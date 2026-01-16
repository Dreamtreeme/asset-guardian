# -*- coding: utf-8 -*-
import re
import json
import datetime as dt
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME"
engine = create_engine(DB_URL, pool_pre_ping=True)

# -------------------------
# 1) 유니버스 텍스트 -> (rank, name_ko, raw_row) 파싱
# -------------------------
def parse_names_only(raw: str) -> List[Dict[str, Any]]:
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"\t+", line)
        if len(parts) < 2:
            continue
        try:
            rank = int(parts[0])
        except:
            continue
        name_ko = parts[1].strip()
        rows.append({"rank": rank, "name_ko": name_ko, "raw_row": line})
    return rows


# -------------------------
# 2) assets upsert (name only)
# -------------------------
def ensure_assets(names: List[str]) -> Dict[str, int]:
    """
    name_ko 리스트를 assets에 넣고 asset_id 매핑 반환
    """
    sql_ins = """
    INSERT INTO market.assets (name_ko, exchange, currency)
    VALUES (:name_ko, 'KRX', 'KRW')
    ON CONFLICT (name_ko) DO UPDATE SET
      updated_at = now()
    RETURNING asset_id, name_ko;
    """

    name_to_id: Dict[str, int] = {}

    with engine.begin() as conn:
        for nm in names:
            r = conn.execute(text(sql_ins), {"name_ko": nm}).fetchone()
            if r:
                name_to_id[r[1]] = int(r[0])

        # 이미 존재했던 애들도 RETURNING이 나와서 보통 충분하지만,
        # 혹시 누락될 수 있으니 한번 더 조회로 완성
        rows = conn.execute(
            text("SELECT asset_id, name_ko FROM market.assets WHERE name_ko = ANY(:names)"),
            {"names": names},
        ).fetchall()
        for aid, nm in rows:
            name_to_id[nm] = int(aid)

    return name_to_id


# -------------------------
# 3) universe snapshot 저장
# -------------------------
def upsert_universe_snapshot(rows: List[Dict[str, Any]], as_of_date: dt.date, name_to_id: Dict[str, int]):
    sql = """
    INSERT INTO market.universe_snapshot_kr_top50
      (as_of_date, rank, name_ko, asset_id, raw_row)
    VALUES
      (:as_of_date, :rank, :name_ko, :asset_id, :raw_row)
    ON CONFLICT (as_of_date, rank) DO UPDATE SET
      name_ko = EXCLUDED.name_ko,
      asset_id = EXCLUDED.asset_id,
      raw_row = EXCLUDED.raw_row;
    """
    params = []
    for r in rows:
        params.append({
            "as_of_date": as_of_date,
            "rank": r["rank"],
            "name_ko": r["name_ko"],
            "asset_id": name_to_id.get(r["name_ko"]),
            "raw_row": r["raw_row"],
        })
    with engine.begin() as conn:
        conn.execute(text(sql), params)


# -------------------------
# 4) yfinance 이름 검색 -> ticker 추정
# -------------------------
def try_resolve_ticker(name_ko: str) -> Optional[Dict[str, Any]]:
    """
    yfinance Search 기능을 써서 ticker 후보를 찾는다.
    - yfinance 버전에 따라 Search가 없을 수 있어 예외 처리
    - 성공해도 'KRX/KOSPI 티커(.KS/.KQ)' 우선
    """
    queries = [
        name_ko,
        f"{name_ko} KOSPI",
        f"{name_ko} KRX",
        f"{name_ko} 주가",
    ]

    for q in queries:
        try:
            s = yf.Search(q, max_results=10)
            # yfinance Search 결과는 버전에 따라 속성이 다를 수 있어 방어적으로 처리
            quotes = getattr(s, "quotes", None)
            if quotes is None:
                data = getattr(s, "to_dict", lambda: None)()
                quotes = data.get("quotes") if isinstance(data, dict) else None
            if not quotes:
                _log_resolution(name_ko, q, None, status="failed", raw={"notes": "no quotes"})
                continue

            # 후보 스코어링: KRX/KS/KQ 우선 + 이름 유사도(단순 포함)
            best = None
            best_score = -1

            for it in quotes:
                sym = it.get("symbol") or it.get("ticker")
                longname = it.get("longname") or it.get("longName") or it.get("shortname") or it.get("shortName")
                exch = it.get("exchange") or it.get("exchDisp") or it.get("exchangeDisp")

                if not sym:
                    continue

                score = 0
                if sym.endswith(".KS") or sym.endswith(".KQ"):
                    score += 5
                if exch and ("Korea" in str(exch) or "KRX" in str(exch) or "KSE" in str(exch)):
                    score += 3
                if longname and (name_ko.replace(" ", "") in str(longname).replace(" ", "")):
                    score += 2

                if score > best_score:
                    best_score = score
                    best = {"ticker": sym, "name": longname, "exchange": exch, "score": float(score), "raw": it}

            if best and best_score >= 5:
                _log_resolution(name_ko, q, best["ticker"], best["name"], best["exchange"], best["score"], "matched", best["raw"])
                return best

            # 점수 낮으면 실패 기록하고 다음 쿼리로
            _log_resolution(name_ko, q, None, status="failed", raw={"best_score": best_score, "best": best})
        except Exception as e:
            _log_resolution(name_ko, q, None, status="failed", raw={"error": str(e)})

    return None


def _log_resolution(name_ko, query, result_ticker=None, result_name=None, result_exchange=None, score=None, status="failed", raw=None):
    sql = """
    INSERT INTO market.ticker_resolution_log
      (name_ko, query, result_ticker, result_name, result_exchange, score, status, raw)
    VALUES
      (:name_ko, :query, :result_ticker, :result_name, :result_exchange, :score, :status, :raw::jsonb)
    """
    payload = {
        "name_ko": name_ko,
        "query": query,
        "result_ticker": result_ticker,
        "result_name": result_name,
        "result_exchange": result_exchange,
        "score": score,
        "status": status,
        "raw": json.dumps(raw or {}, ensure_ascii=False),
    }
    with engine.begin() as conn:
        conn.execute(text(sql), payload)


# -------------------------
# 5) assets에 ticker 업데이트
# -------------------------
def update_asset_ticker(asset_id: int, ticker: str, exchange: Optional[str] = None, industry: Optional[str] = None):
    sql = """
    UPDATE market.assets
    SET ticker = :ticker,
        exchange = COALESCE(:exchange, exchange),
        industry = COALESCE(:industry, industry),
        updated_at = now()
    WHERE asset_id = :asset_id
    """
    with engine.begin() as conn:
        conn.execute(text(sql), {"asset_id": asset_id, "ticker": ticker, "exchange": exchange, "industry": industry})


# -------------------------
# 6) 가격/매크로/재무 적재
# -------------------------
def upsert_prices_daily(asset_id: int, df: pd.DataFrame, source: str = "yfinance"):
    if df is None or df.empty:
        return 0
    d = df.copy()
    d.index = pd.to_datetime(d.index).date
    d = d.reset_index().rename(columns={"index": "date"})
    d = d.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Adj Close":"adj_close","Volume":"volume"})
    d["asset_id"] = asset_id
    d["source"] = source

    sql = """
    INSERT INTO market.prices_daily
      (asset_id, date, open, high, low, close, adj_close, volume, source)
    VALUES
      (:asset_id, :date, :open, :high, :low, :close, :adj_close, :volume, :source)
    ON CONFLICT (asset_id, date) DO UPDATE SET
      open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
      adj_close=EXCLUDED.adj_close, volume=EXCLUDED.volume, source=EXCLUDED.source,
      updated_at=now();
    """
    params = d[["asset_id","date","open","high","low","close","adj_close","volume","source"]].to_dict("records")
    with engine.begin() as conn:
        conn.execute(text(sql), params)
    return len(d)


def upsert_series_daily(series_id: str, df: pd.DataFrame, source: str = "yfinance"):
    if df is None or df.empty:
        return 0
    d = df.copy()
    d.index = pd.to_datetime(d.index).date
    d = d.reset_index().rename(columns={"index":"date"})
    d = d.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Adj Close":"adj_close","Volume":"volume"})
    d["series_id"] = series_id
    d["source"] = source

    sql = """
    INSERT INTO market.series_daily
      (series_id, date, open, high, low, close, adj_close, volume, source)
    VALUES
      (:series_id, :date, :open, :high, :low, :close, :adj_close, :volume, :source)
    ON CONFLICT (series_id, date) DO UPDATE SET
      open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
      adj_close=EXCLUDED.adj_close, volume=EXCLUDED.volume, source=EXCLUDED.source,
      updated_at=now();
    """
    params = d[["series_id","date","open","high","low","close","adj_close","volume","source"]].to_dict("records")
    with engine.begin() as conn:
        conn.execute(text(sql), params)
    return len(d)


def load_prices(ticker: str, years: int = 10) -> pd.DataFrame:
    tk = yf.Ticker(ticker)
    df = tk.history(period=f"{years}y", auto_adjust=False)
    if df is None or df.empty:
        df = tk.history(period="2y", auto_adjust=False)
    return df


def upsert_financials_quarterly(asset_id: int, ticker: str):
    tk = yf.Ticker(ticker)
    q_fin = getattr(tk, "quarterly_financials", None)
    q_cf  = getattr(tk, "quarterly_cashflow", None)
    q_bs  = getattr(tk, "quarterly_balance_sheet", None)

    def pick_row(df, candidates):
        if df is None or getattr(df, "empty", True):
            return None
        for r in candidates:
            if r in df.index:
                s = df.loc[r].sort_index()
                s.index = pd.to_datetime(s.index).date
                return s
        return None

    # IS
    rev = pick_row(q_fin, ["Total Revenue","TotalRevenue","Revenue"])
    op  = pick_row(q_fin, ["Operating Income","OperatingIncome"])
    net = pick_row(q_fin, ["Net Income","NetIncome"])
    if any(x is not None for x in [rev, op, net]):
        periods = sorted(set((rev.index if rev is not None else [])).union(op.index if op is not None else []).union(net.index if net is not None else []))
        rows = []
        for pe in periods:
            rows.append({
                "asset_id": asset_id, "period_end": pe,
                "revenue": float(rev.get(pe)) if rev is not None and pd.notna(rev.get(pe)) else None,
                "operating_income": float(op.get(pe)) if op is not None and pd.notna(op.get(pe)) else None,
                "net_income": float(net.get(pe)) if net is not None and pd.notna(net.get(pe)) else None,
                "currency":"KRW","source":"yfinance",
            })
        sql = """
        INSERT INTO market.financials_q_is (asset_id, period_end, revenue, operating_income, net_income, currency, source)
        VALUES (:asset_id,:period_end,:revenue,:operating_income,:net_income,:currency,:source)
        ON CONFLICT (asset_id, period_end) DO UPDATE SET
          revenue=EXCLUDED.revenue, operating_income=EXCLUDED.operating_income, net_income=EXCLUDED.net_income,
          currency=EXCLUDED.currency, source=EXCLUDED.source, updated_at=now();
        """
        with engine.begin() as conn:
            conn.execute(text(sql), rows)

    # CF
    ocf = pick_row(q_cf, ["Total Cash From Operating Activities","Operating Cash Flow","OperatingCashFlow"])
    capex = pick_row(q_cf, ["Capital Expenditures","CapitalExpenditures"])
    if any(x is not None for x in [ocf, capex]):
        periods = sorted(set((ocf.index if ocf is not None else [])).union(capex.index if capex is not None else []))
        rows = []
        for pe in periods:
            rows.append({
                "asset_id": asset_id, "period_end": pe,
                "operating_cf": float(ocf.get(pe)) if ocf is not None and pd.notna(ocf.get(pe)) else None,
                "capex": float(capex.get(pe)) if capex is not None and pd.notna(capex.get(pe)) else None,
                "currency":"KRW","source":"yfinance",
            })
        sql = """
        INSERT INTO market.financials_q_cf (asset_id, period_end, operating_cf, capex, currency, source)
        VALUES (:asset_id,:period_end,:operating_cf,:capex,:currency,:source)
        ON CONFLICT (asset_id, period_end) DO UPDATE SET
          operating_cf=EXCLUDED.operating_cf, capex=EXCLUDED.capex,
          currency=EXCLUDED.currency, source=EXCLUDED.source, updated_at=now();
        """
        with engine.begin() as conn:
            conn.execute(text(sql), rows)

    # BS
    debt = pick_row(q_bs, ["Total Debt","TotalDebt","Long Term Debt","LongTermDebt"])
    eq   = pick_row(q_bs, ["Total Stockholder Equity","TotalStockholderEquity","StockholdersEquity"])
    if any(x is not None for x in [debt, eq]):
        periods = sorted(set((debt.index if debt is not None else [])).union(eq.index if eq is not None else []))
        rows = []
        for pe in periods:
            rows.append({
                "asset_id": asset_id, "period_end": pe,
                "total_debt": float(debt.get(pe)) if debt is not None and pd.notna(debt.get(pe)) else None,
                "total_equity": float(eq.get(pe)) if eq is not None and pd.notna(eq.get(pe)) else None,
                "currency":"KRW","source":"yfinance",
            })
        sql = """
        INSERT INTO market.financials_q_bs (asset_id, period_end, total_debt, total_equity, currency, source)
        VALUES (:asset_id,:period_end,:total_debt,:total_equity,:currency,:source)
        ON CONFLICT (asset_id, period_end) DO UPDATE SET
          total_debt=EXCLUDED.total_debt, total_equity=EXCLUDED.total_equity,
          currency=EXCLUDED.currency, source=EXCLUDED.source, updated_at=now();
        """
        with engine.begin() as conn:
            conn.execute(text(sql), rows)


# -------------------------
# 7) 매크로 시리즈 적재
# -------------------------
SERIES_MAP = {
    "KOSPI": "^KS11",
    "VIX": "^VIX",
    "DXY": "DX-Y.NYB",
    "KRWUSD": "KRW=X",
}


# -------------------------
# 8) 실행
# -------------------------
def main():
    as_of = dt.date.today()

    RAW_TOP50 = """여기에 너가 붙여준 상위50 텍스트 그대로 붙여넣기"""
    uni_rows = parse_names_only(RAW_TOP50)

    names = [r["name_ko"] for r in uni_rows]
    name_to_id = ensure_assets(names)

    upsert_universe_snapshot(uni_rows, as_of, name_to_id)
    print(f"[OK] assets upserted={len(name_to_id)} / universe rows={len(uni_rows)}")

    # 매크로 적재(무조건 가능)
    for sid, sym in SERIES_MAP.items():
        df = yf.Ticker(sym).history(period="10y", auto_adjust=False)
        if df is None or df.empty:
            df = yf.Ticker(sym).history(period="2y", auto_adjust=False)
        n = upsert_series_daily(sid, df)
        print(f"[OK] series {sid} rows={n}")

    # 종목별: ticker 자동추정 -> 성공한 경우만 가격/재무 적재
    matched = 0
    failed = 0

    for nm in names:
        aid = name_to_id[nm]

        # 이미 ticker가 있으면 재사용
        with engine.begin() as conn:
            row = conn.execute(text("SELECT ticker FROM market.assets WHERE asset_id=:aid"), {"aid": aid}).fetchone()
        current_ticker = row[0] if row else None

        if not current_ticker:
            res = try_resolve_ticker(nm)
            if not res:
                failed += 1
                print(f"[WARN] ticker not resolved: {nm}")
                continue
            current_ticker = res["ticker"]
            update_asset_ticker(aid, current_ticker, exchange=res.get("exchange"))

        # 가격 적재
        px = load_prices(current_ticker, years=10)
        n = upsert_prices_daily(aid, px)
        print(f"[OK] prices {nm} ({current_ticker}) rows={n}")

        # 재무 적재(될 때만)
        try:
            upsert_financials_quarterly(aid, current_ticker)
            print(f"[OK] financials {nm} ({current_ticker})")
        except Exception as e:
            print(f"[WARN] financials failed: {nm} ({current_ticker}) err={e}")

        matched += 1

    print(f"DONE. matched={matched}, failed={failed}")
    print("미매핑 종목은 market.ticker_resolution_log에서 검색 실패 기록을 확인 가능.")


if __name__ == "__main__":
    main()
