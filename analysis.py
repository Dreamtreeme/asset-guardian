# -*- coding: utf-8 -*-
"""
한 종목 입력 -> 장기/중기/단기(전일+금일 시나리오) Evidence 계산 + 전망(요약) 출력
- 데이터 소스: yfinance
- 입력: 종목코드 (예: 005930, 035420.KS, AAPL)
- 출력: 장기/중기/단기 각각의 evidence + 간단 전망(조건부)

설명:
- 장기: (재무 추세) + (장기 추세선/이평)
- 중기: (국면) + (유사국면 이벤트 스터디) + (섹터 ETF 대비 상대성과) + (기술적 R/R)
- 단기: 전일(변동성/거래량/갭) + 금일(상/하/중립 조건 시나리오)

주의:
- yfinance의 분기 재무/섹터 정보는 종목/시장에 따라 비어 있을 수 있음.
- 국내 섹터 분류는 yfinance가 빈 경우가 많아 휴리스틱(키워드)로 추정.
- "섹터 ETF"는 후보군 중 최근 3개월 평균 거래량이 가장 큰 것을 선택.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import pandas as pd
import yfinance as yf


# =========================================================
# 0) 설정: 섹터 ETF 후보군
# =========================================================

# 해외(주로 미국) 섹터 -> 대표 ETF 후보(확장 가능)
US_SECTOR_TO_ETFS: Dict[str, List[str]] = {
    "Technology": ["XLK"],
    "Financial Services": ["XLF"],
    "Financial": ["XLF"],
    "Health Care": ["XLV"],
    "Healthcare": ["XLV"],
    "Consumer Cyclical": ["XLY"],
    "Consumer Defensive": ["XLP"],
    "Energy": ["XLE"],
    "Industrials": ["XLI"],
    "Basic Materials": ["XLB"],
    "Utilities": ["XLU"],
    "Real Estate": ["XLRE"],
    "Communication Services": ["XLC"],
}

# 국내 섹터 -> ETF 후보 (원하면 여기 후보를 더 채우면 정확도/범용성↑)
# - IT: KODEX 200IT TR (363580)
# - 헬스케어: KODEX 헬스케어 (266420)
# - 금융: KODEX 은행 (091170) (금융 프록시)
# - fallback: KODEX 200 (069500)
KR_SECTOR_TO_ETFS: Dict[str, List[str]] = {
    "IT": ["363580.KS"],
    "HEALTHCARE": ["266420.KS"],
    "FINANCIAL": ["091170.KS"],
    "BROAD": ["069500.KS"],
}


# =========================================================
# 1) 유틸
# =========================================================

def normalize_ticker(code: str) -> str:
    """
    - 6자리 숫자면 한국 종목(.KS)로 가정 (KOSDAQ이면 사용자가 .KQ로 직접 입력)
    - 이미 접미사(.KS/.KQ 등) 있으면 그대로 사용
    """
    code = code.strip()
    if "." in code:
        return code
    if code.isdigit() and len(code) == 6:
        return f"{code}.KS"
    return code


def safe_first(d: Dict[str, Any], *keys: str, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def linreg_slope(y: pd.Series) -> float:
    y = y.dropna()
    if len(y) < 3:
        return np.nan
    x = np.arange(len(y), dtype=float)
    yy = y.values.astype(float)
    return float(np.cov(x, yy, bias=True)[0, 1] / (np.var(x) + 1e-12))


def max_drawdown(close: pd.Series, window: int = 252) -> float:
    c = close.dropna()
    if len(c) < 2:
        return np.nan
    c = c.iloc[-window:] if len(c) > window else c
    running_max = c.cummax()
    dd = (c / running_max) - 1.0
    return float(dd.min())


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def recent_support_resistance(close: pd.Series, lookback: int = 20) -> Tuple[float, float]:
    c = close.dropna()
    if len(c) < lookback:
        lookback = max(5, len(c))
    window = c.iloc[-lookback:]
    support = float(window.min())
    resistance = float(window.max())
    return support, resistance


def pick_market_index(ticker: str) -> str:
    # 한국: 코스피(^KS11), 해외: S&P500(^GSPC)
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return "^KS11"
    return "^GSPC"


# =========================================================
# 2) 섹터 ETF 자동 선택 (거래량 1등)
# =========================================================

def _avg_volume_3m(etf_ticker: str) -> float:
    df = yf.Ticker(etf_ticker).history(period="3mo", auto_adjust=False)
    if df is None or df.empty or "Volume" not in df:
        return 0.0
    v = df["Volume"].dropna()
    return float(v.mean()) if len(v) else 0.0


def pick_most_liquid_etf(candidates: List[str]) -> Optional[str]:
    if not candidates:
        return None
    vols = [(t, _avg_volume_3m(t)) for t in candidates]
    vols.sort(key=lambda x: x[1], reverse=True)
    # 거래량 데이터가 0으로 나오는 경우도 있어, 그땐 첫 후보를 반환
    return vols[0][0] if vols[0][1] > 0 else candidates[0]


def infer_kr_sector_from_info(info: Dict[str, Any]) -> str:
    """
    국내는 yfinance sector가 비는 경우가 많아서 industry/이름으로 휴리스틱 추정.
    실패하면 BROAD(코스피200)로.
    """
    text = " ".join([
        str(info.get("industry", "")),
        str(info.get("sector", "")),
        str(info.get("shortName", "")),
        str(info.get("longName", "")),
    ]).lower()

    if any(k in text for k in ["semiconductor", "software", "it", "electronic", "internet", "hardware", "display"]):
        return "IT"
    if any(k in text for k in ["bank", "insurance", "financial", "broker", "capital markets"]):
        return "FINANCIAL"
    if any(k in text for k in ["biotech", "pharmaceutical", "drug", "health", "medical"]):
        return "HEALTHCARE"
    return "BROAD"


def get_sector_etf_for_ticker(stock_ticker: str, info: Dict[str, Any]) -> Dict[str, Any]:
    """
    반환:
    {
      sector_label: str,
      sector_etf: str,
      candidates: [..],
      avg_volume_3m: float
    }
    """
    is_kr = stock_ticker.endswith(".KS") or stock_ticker.endswith(".KQ")

    if not is_kr:
        sector = info.get("sector") or info.get("sectorKey") or ""
        candidates = US_SECTOR_TO_ETFS.get(str(sector), ["SPY"])  # fallback
        chosen = pick_most_liquid_etf(candidates)
        return {
            "sector_label": sector if sector else "UNKNOWN",
            "sector_etf": chosen,
            "candidates": candidates,
            "avg_volume_3m": _avg_volume_3m(chosen) if chosen else 0.0,
        }

    kr_sector = infer_kr_sector_from_info(info or {})
    candidates = KR_SECTOR_TO_ETFS.get(kr_sector, KR_SECTOR_TO_ETFS["BROAD"])
    chosen = pick_most_liquid_etf(candidates)

    return {
        "sector_label": kr_sector,
        "sector_etf": chosen,
        "candidates": candidates,
        "avg_volume_3m": _avg_volume_3m(chosen) if chosen else 0.0,
    }


def compute_relative_performance(stock_close: pd.Series, etf_ticker: str) -> Dict[str, Any]:
    """
    종목 vs 섹터ETF 상대성과:
    - 6m/12m/24m 종목/섹터 수익률 + 초과수익
    """
    etf = yf.Ticker(etf_ticker).history(period="2y", auto_adjust=False)
    if etf is None or etf.empty:
        return {"available": False, "reason": "섹터 ETF 가격 데이터 없음"}

    etf_close = etf["Close"].dropna()
    s = stock_close.dropna()
    if len(s) < 60 or len(etf_close) < 60:
        return {"available": False, "reason": "데이터 길이 부족"}

    df = pd.DataFrame({"stock": s, "sector": etf_close}).dropna()
    if df.shape[0] < 60:
        return {"available": False, "reason": "날짜 정렬 후 데이터 부족"}

    def ret_over(n: int):
        if df.shape[0] <= n:
            return {"stock": None, "sector": None, "excess": None}
        sr = float(df["stock"].iloc[-1] / df["stock"].iloc[-1 - n] - 1.0)
        er = float(df["sector"].iloc[-1] / df["sector"].iloc[-1 - n] - 1.0)
        return {"stock": sr, "sector": er, "excess": sr - er}

    return {
        "available": True,
        "etf": etf_ticker,
        "returns": {
            "6m": ret_over(126),
            "12m": ret_over(252),
            "24m": ret_over(504),
        }
    }


# =========================================================
# 3) 데이터 로딩(분기 재무 포함)
# =========================================================

@dataclass
class TickerData:
    ticker: str
    px_10y: pd.DataFrame
    info: Dict[str, Any]
    q_fin: Optional[pd.DataFrame]
    q_cf: Optional[pd.DataFrame]
    q_bs: Optional[pd.DataFrame]


def fetch_ticker_data(ticker_code: str) -> TickerData:
    tkr = normalize_ticker(ticker_code)
    tk = yf.Ticker(tkr)

    px_10y = tk.history(period="10y", auto_adjust=False)
    if px_10y is None or px_10y.empty:
        px_10y = tk.history(period="2y", auto_adjust=False)

    try:
        info = tk.info or {}
    except Exception:
        info = {}

    def _safe_df(getter):
        try:
            df = getter()
            if df is not None and hasattr(df, "empty") and df.empty:
                return None
            return df
        except Exception:
            return None

    q_fin = _safe_df(lambda: tk.quarterly_financials)
    q_cf = _safe_df(lambda: tk.quarterly_cashflow)
    q_bs = _safe_df(lambda: tk.quarterly_balance_sheet)

    return TickerData(ticker=tkr, px_10y=px_10y, info=info, q_fin=q_fin, q_cf=q_cf, q_bs=q_bs)


# =========================================================
# 4) Evidence: 장기
# =========================================================

def evidence_long_term(td: TickerData) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ticker": td.ticker}

    px = td.px_10y.copy()
    close = px["Close"].dropna()
    if close.empty:
        return {"error": "가격 데이터가 없습니다."}

    # ---- 장기 추세(이평)
    ma200 = close.rolling(200).mean()
    ma300 = close.rolling(300).mean()
    price_block = {
        "현재가": float(close.iloc[-1]),
        "200일선": float(ma200.iloc[-1]) if not np.isnan(ma200.iloc[-1]) else None,
        "300일선": float(ma300.iloc[-1]) if not np.isnan(ma300.iloc[-1]) else None,
        "200일선_기울기(최근250일)": linreg_slope(ma200.dropna().iloc[-250:]) if ma200.dropna().shape[0] >= 20 else None,
        "300일선_기울기(최근250일)": linreg_slope(ma300.dropna().iloc[-250:]) if ma300.dropna().shape[0] >= 20 else None,
        "최근5년_MDD": max_drawdown(close, window=252*5),
    }

    # ---- 분기 재무(추세)
    q_fin, q_cf, q_bs = td.q_fin, td.q_cf, td.q_bs

    def get_row(df: Optional[pd.DataFrame], candidates: List[str]) -> Optional[pd.Series]:
        if df is None:
            return None
        for r in candidates:
            if r in df.index:
                s = df.loc[r].sort_index()
                s.index = pd.to_datetime(s.index)
                return s
        return None

    rev = get_row(q_fin, ["Total Revenue", "TotalRevenue", "Revenue"])
    op_inc = get_row(q_fin, ["Operating Income", "OperatingIncome"])
    net_inc = get_row(q_fin, ["Net Income", "NetIncome"])
    ocf = get_row(q_cf, ["Total Cash From Operating Activities", "Operating Cash Flow", "OperatingCashFlow"])
    capex = get_row(q_cf, ["Capital Expenditures", "CapitalExpenditures"])
    total_debt = get_row(q_bs, ["Total Debt", "TotalDebt", "Long Term Debt", "LongTermDebt"])
    equity = get_row(q_bs, ["Total Stockholder Equity", "TotalStockholderEquity", "StockholdersEquity"])

    op_margin = (op_inc / rev).replace([np.inf, -np.inf], np.nan) if (rev is not None and op_inc is not None) else None
    net_margin = (net_inc / rev).replace([np.inf, -np.inf], np.nan) if (rev is not None and net_inc is not None) else None
    fcf = (ocf + capex).replace([np.inf, -np.inf], np.nan) if (ocf is not None and capex is not None) else (ocf.copy() if ocf is not None else None)
    de_ratio = (total_debt / equity).replace([np.inf, -np.inf], np.nan) if (total_debt is not None and equity is not None) else None

    def trend_pack(s: Optional[pd.Series]) -> Dict[str, Any]:
        if s is None or s.dropna().shape[0] < 3:
            return {"사용가능": False}
        s = s.dropna().sort_index()
        diff = s.diff()
        recent = diff.iloc[-8:] if diff.shape[0] >= 8 else diff
        improve_ratio = float((recent > 0).mean()) if len(recent) else None
        return {
            "사용가능": True,
            "최신값": float(s.iloc[-1]),
            "기울기": linreg_slope(s),
            "최근개선비율(최대8분기)": improve_ratio,
            "분기수": int(s.shape[0]),
        }

    fund = {
        "매출": trend_pack(rev),
        "영업이익률": trend_pack(op_margin),
        "순이익률": trend_pack(net_margin),
        "FCF": trend_pack(fcf),
        "부채/자본": trend_pack(de_ratio),
    }

    improve_count, worsen_count = 0, 0
    for name, item in fund.items():
        if not item.get("사용가능"):
            continue
        slope = item.get("기울기")
        if slope is None or np.isnan(slope):
            continue
        # 부채/자본은 낮을수록 좋음 → slope<0이면 개선
        if name == "부채/자본":
            if slope < 0:
                improve_count += 1
            elif slope > 0:
                worsen_count += 1
        else:
            if slope > 0:
                improve_count += 1
            elif slope < 0:
                worsen_count += 1

    if improve_count >= 3:
        fund_verdict = "✅ 개선"
    elif worsen_count >= 3:
        fund_verdict = "❌ 악화"
    else:
        fund_verdict = "⚠️ 혼합"

    # ---- 현재 밸류에이션(가능하면)
    info = td.info or {}
    valuation_now = {
        "trailingPE": safe_first(info, "trailingPE"),
        "forwardPE": safe_first(info, "forwardPE"),
        "priceToBook": safe_first(info, "priceToBook"),
        "enterpriseToEbitda": safe_first(info, "enterpriseToEbitda"),
        "marketCap": safe_first(info, "marketCap"),
    }

    # ---- 장기 전망(요약)
    price_ok = (
        price_block.get("200일선") is not None and
        price_block.get("현재가") > price_block.get("200일선") and
        (price_block.get("200일선_기울기(최근250일)") is None or price_block.get("200일선_기울기(최근250일)") >= 0)
    )
    if "✅" in fund_verdict and price_ok:
        outlook = "장기 우호(펀더멘털+추세가 비교적 긍정)."
    elif "❌" in fund_verdict and not price_ok:
        outlook = "장기 비우호(펀더멘털/추세가 약한 편)."
    else:
        outlook = "장기 중립/혼합(좋은 요소와 약한 요소가 공존)."

    return {
        "evidence": {
            "재무추세": {
                "지표": fund,
                "개선지표수": improve_count,
                "악화지표수": worsen_count,
                "판정": fund_verdict,
                "메모": "분기 재무가 없으면 일부 지표가 사용불가로 나올 수 있어요.",
            },
            "장기추세": price_block,
            "밸류에이션(현재)": valuation_now,
        },
        "전망": outlook,
    }


# =========================================================
# 5) Evidence: 중기
# =========================================================

def evidence_mid_term(td: TickerData) -> Dict[str, Any]:
    tkr = td.ticker
    out: Dict[str, Any] = {}

    px = yf.Ticker(tkr).history(period="2y", auto_adjust=False)
    if px is None or px.empty:
        return {"error": "2년 가격 데이터가 없습니다."}

    close = px["Close"].dropna()
    if close.empty:
        return {"error": "종가 데이터가 없습니다."}

    # ---- (1) 국면 점수: VIX, DXY, (KRW=X), 시장 드로우다운
    market_index = pick_market_index(tkr)
    mkt = yf.Ticker(market_index).history(period="2y", auto_adjust=False)
    vix = yf.Ticker("^VIX").history(period="2y", auto_adjust=False)
    dxy = yf.Ticker("DX-Y.NYB").history(period="2y", auto_adjust=False)
    fx_symbol = "KRW=X" if (tkr.endswith(".KS") or tkr.endswith(".KQ")) else None
    fx = yf.Ticker(fx_symbol).history(period="2y", auto_adjust=False) if fx_symbol else None

    def last(df: Optional[pd.DataFrame]) -> Optional[float]:
        if df is None or df.empty:
            return None
        s = df["Close"].dropna()
        return float(s.iloc[-1]) if not s.empty else None

    def pct_3m(df: Optional[pd.DataFrame]) -> Optional[float]:
        if df is None or df.empty:
            return None
        s = df["Close"].dropna()
        if len(s) < 63:
            return None
        return float((s.iloc[-1] / s.iloc[-63]) - 1.0)

    def drawdown_1m(df: Optional[pd.DataFrame]) -> Optional[float]:
        if df is None or df.empty:
            return None
        s = df["Close"].dropna()
        if len(s) < 21:
            return None
        return float((s.iloc[-1] / s.iloc[-21:].max()) - 1.0)

    vix_last = last(vix)
    dxy_3m = pct_3m(dxy)
    fx_3m = pct_3m(fx) if fx is not None else None
    mkt_dd = drawdown_1m(mkt)

    signals = []
    if vix_last is not None and vix_last > 25:
        signals.append("VIX>25")
    if dxy_3m is not None and dxy_3m > 0.05:
        signals.append("DXY 3개월 +5%")
    if fx_3m is not None and fx_3m > 0.05:
        signals.append("KRW=X 3개월 +5%")
    if mkt_dd is not None and mkt_dd <= -0.10:
        signals.append("시장 1개월 -10% 이하")

    score = len(signals)
    regime = "불안" if score >= 3 else ("중립" if score >= 1 else "완화")

    regime_block = {
        "시장지수": market_index,
        "지표": {
            "VIX(현재)": vix_last,
            "DXY(3개월변화)": dxy_3m,
            "환율KRW=X(3개월변화)": fx_3m,
            "시장(1개월드로우다운)": mkt_dd,
        },
        "신호": signals,
        "점수": score,
        "국면": regime,
    }

    # ---- (2) 유사 국면 이벤트 스터디: VIX 25 상향 돌파 → 1개월 후 초과수익(종목-시장)
    events = []
    vix_close = vix["Close"].dropna() if vix is not None and not vix.empty else pd.Series(dtype=float)
    mkt_close = mkt["Close"].dropna() if mkt is not None and not mkt.empty else None
    stock_close = close.copy()

    if len(vix_close) >= 2 and mkt_close is not None and not mkt_close.empty:
        cross = (vix_close > 25) & (vix_close.shift(1) <= 25)
        event_dates = vix_close.index[cross].tolist()

        def fwd_return(s: pd.Series, dt, fwd: int = 21) -> Optional[float]:
            if len(s) < fwd + 2:
                return None
            if dt not in s.index:
                idx = s.index.searchsorted(dt) - 1
            else:
                idx = s.index.get_loc(dt)
            if idx < 0 or idx + fwd >= len(s):
                return None
            return float((s.iloc[idx + fwd] / s.iloc[idx]) - 1.0)

        for dt in event_dates:
            r_stock = fwd_return(stock_close, dt, 21)
            r_mkt = fwd_return(mkt_close, dt, 21)
            if r_stock is None or r_mkt is None:
                continue
            events.append({
                "날짜": str(pd.to_datetime(dt).date()),
                "종목1개월수익률": r_stock,
                "시장1개월수익률": r_mkt,
                "초과수익(종목-시장)": r_stock - r_mkt,
            })

    if events:
        ex = np.array([e["초과수익(종목-시장)"] for e in events], dtype=float)
        win_rate = float((ex > 0).mean())
        avg_ex = float(ex.mean())
        event_verdict = "✅ 강함" if win_rate >= 0.60 else ("⚠️ 혼합" if win_rate >= 0.40 else "❌ 약함")
    else:
        win_rate, avg_ex, event_verdict = None, None, "정보부족"

    event_block = {
        "방법": "VIX가 25를 상향 돌파한 이벤트에서 1개월 후 초과수익(종목-시장)",
        "이벤트수": len(events),
        "초과수익_승률": win_rate,
        "초과수익_평균": avg_ex,
        "판정": event_verdict,
        "이벤트샘플(최대30개)": events[:30],
    }

    # ---- (3) 섹터 ETF 대비 상대성과 (거래량 1등 ETF 자동 선택)
    sector_pick = get_sector_etf_for_ticker(tkr, td.info or {})
    sector_etf = sector_pick.get("sector_etf")
    sector_rel = compute_relative_performance(close, sector_etf) if sector_etf else {"available": False}

    sector_block = {
        "추정섹터": sector_pick.get("sector_label"),
        "선택된섹터ETF": sector_etf,
        "후보ETF": sector_pick.get("candidates"),
        "선택ETF_3개월평균거래량": sector_pick.get("avg_volume_3m"),
        "상대성과(종목-섹터)": sector_rel,
        "메모": "국내 섹터는 yfinance 정보가 빈 경우가 많아 키워드 기반 휴리스틱으로 추정합니다.",
    }

    # ---- (4) 기술적 구조: 20일 지지/저항 + R/R + ATR
    support, resistance = recent_support_resistance(close, lookback=20)
    last_close = float(close.iloc[-1])
    rr = None
    if last_close > support and resistance > last_close:
        rr = (resistance - last_close) / (last_close - support + 1e-12)

    atr14 = atr(px, 14)
    atr_last = float(atr14.iloc[-1]) if not atr14.dropna().empty else None

    if rr is None:
        tech_verdict = "정보부족"
    elif rr >= 2:
        tech_verdict = "✅ 상승우위"
    elif rr >= 1:
        tech_verdict = "⚠️ 중립"
    else:
        tech_verdict = "❌ 하방리스크"

    tech_block = {
        "현재가": last_close,
        "20일지지선": support,
        "20일저항선": resistance,
        "RiskReward": rr,
        "ATR14": atr_last,
        "판정": tech_verdict,
    }

    # ---- 중기 전망(요약)
    # 룰: 국면(불안이면 보수), 이벤트(강함이면 가점), 섹터 상대성과(최근 6m excess), 기술구조(R/R)
    ex6 = None
    if sector_rel.get("available"):
        ex6 = sector_rel["returns"]["6m"]["excess"]

    score_mid = 0
    if regime == "완화":
        score_mid += 1
    elif regime == "불안":
        score_mid -= 1

    if "✅" in event_verdict:
        score_mid += 1
    elif "❌" in event_verdict:
        score_mid -= 1

    if ex6 is not None:
        if ex6 > 0:
            score_mid += 1
        elif ex6 < 0:
            score_mid -= 1

    if "✅" in tech_verdict:
        score_mid += 1
    elif "❌" in tech_verdict:
        score_mid -= 1

    if score_mid >= 2:
        outlook = "중기 우호(국면/유사국면/섹터대비/기술구조 중 다수가 긍정)."
    elif score_mid <= -2:
        outlook = "중기 비우호(불안 신호/상대부진/기술적 리스크가 우세)."
    else:
        outlook = "중기 혼합/중립(근거가 엇갈림. 조건 확인 필요)."

    out["evidence"] = {
        "국면판정": regime_block,
        "유사국면성과": event_block,
        "섹터비교": sector_block,
        "기술적구조": tech_block,
    }
    out["전망"] = outlook
    return out


# =========================================================
# 6) Evidence: 단기 (전일 + 금일 시나리오)
# =========================================================

def evidence_short_term(td: TickerData) -> Dict[str, Any]:
    tkr = td.ticker
    out: Dict[str, Any] = {}

    px = yf.Ticker(tkr).history(period="2mo", auto_adjust=False)
    if px is None or px.empty or len(px) < 10:
        return {"error": "최근(2개월) 데이터가 부족합니다."}

    px = px.dropna(subset=["Close"])
    if len(px) < 10:
        return {"error": "최근 데이터가 부족합니다."}

    # ---- 전일 분석(가장 최근 완결 일봉 기준)
    # 최신 row가 오늘 종가일 수 있으니, "전일"은 px[-2], "전전일"은 px[-3]로 본다.
    d0 = px.iloc[-1]   # 최신(가장 최근 거래일 종가)
    d1 = px.iloc[-2]   # 전일
    d2 = px.iloc[-3]   # 전전일
    last5 = px.iloc[-7:-2]  # 전일 기준으로 직전 5일

    # 변동성(ATR): 전일 시점의 ATR vs 전일 기준 최근5일 평균
    atr14 = atr(px, 14).dropna()
    atr_d1 = float(atr14.iloc[-2]) if len(atr14) >= 2 else None
    atr5_avg = float(atr14.iloc[-7:-2].mean()) if len(atr14) >= 7 else None
    delta = None
    if atr_d1 is not None and atr5_avg is not None and atr5_avg != 0:
        delta = (atr_d1 - atr5_avg) / atr5_avg

    if delta is None:
        vol_state = "정보부족"
    elif delta > 0.20:
        vol_state = "확대"
    elif delta < -0.20:
        vol_state = "축소"
    else:
        vol_state = "중립"

    # 거래량 배수: 전일 거래량 / 전일 기준 최근5일 평균
    vol_d1 = float(d1["Volume"]) if "Volume" in d1 and not pd.isna(d1["Volume"]) else None
    vol5 = float(last5["Volume"].mean()) if "Volume" in last5 else None
    vol_mult = (vol_d1 / vol5) if (vol_d1 is not None and vol5 and vol5 != 0) else None

    if vol_mult is None:
        flow_state = "정보부족"
    elif vol_mult >= 1.5:
        flow_state = "유입"
    elif vol_mult <= 0.7:
        flow_state = "이탈"
    else:
        flow_state = "보통"

    gap = float((d1["Open"] / d2["Close"]) - 1.0) if d2["Close"] != 0 else None
    body = float((d1["Close"] / d1["Open"]) - 1.0) if d1["Open"] != 0 else None
    rng = float((d1["High"] / d1["Low"]) - 1.0) if d1["Low"] != 0 else None

    prev_day_block = {
        "변동성": {"ATR14(전일)": atr_d1, "ATR14(최근5일평균)": atr5_avg, "변화율": delta, "판정": vol_state},
        "수급프록시(거래량/캔들)": {
            "거래량(전일)": vol_d1,
            "거래량(최근5일평균)": vol5,
            "거래량배수": vol_mult,
            "갭(전일Open/전전일Close-1)": gap,
            "캔들바디(전일Close/Open-1)": body,
            "일중범위(전일High/Low-1)": rng,
            "판정": flow_state,
        },
        "메모": "뉴스 타임라인은 별도 소스 필요(현재는 가격/거래량 반응만).",
    }

    # ---- 금일(조건부 시나리오): 전일 고/저 기준
    y_high = float(d1["High"])
    y_low = float(d1["Low"])
    y_close = float(d1["Close"])

    scenarios = {
        "상방": {
            "트리거": {"돌파가격": y_high, "거래량배수_최소": 1.5},
            "설명": "현재가가 전일 고가를 돌파 + 거래량이 동반되면 단기 추세 가속 가능(조건부).",
        },
        "하방": {
            "트리거": {"이탈가격": y_low, "거래량배수_최소": 1.2},
            "설명": "현재가가 전일 저가 이탈 + 거래량 동반이면 단기 리스크 확대(조건부).",
        },
        "중립": {
            "트리거": {"박스하단": y_low, "박스상단": y_high, "거래량배수_최대": 0.8},
            "설명": "전일 범위 내 박스권 + 거래량 감소면 관망 우위(조건부).",
        },
    }

    today_block = {
        "기준값(전일)": {
            "전일고가": y_high,
            "전일저가": y_low,
            "전일종가": y_close,
            "전일거래량배수(최근5일평균대비)": vol_mult,
        },
        "시나리오": scenarios,
        "메모": "실시간(분봉/체결) 데이터를 붙이면 자동으로 상/하/중립 판정까지 가능.",
    }

    # ---- 단기 전망(요약)
    # 룰: 변동성 확대+거래량 유입이면 '단기 방향성 가능', 축소+거래량 감소면 '관망'
    if vol_state == "확대" and flow_state == "유입":
        outlook = "단기: 변동성 확대 + 거래량 유입 → 방향성(추세) 형성 가능. (돌파/이탈 트리거 확인)"
    elif vol_state == "축소" and flow_state in ("보통", "이탈"):
        outlook = "단기: 변동성 축소(수렴) → 관망/박스 가능성. (상단/하단 트리거 중심)"
    else:
        outlook = "단기: 혼조. (전일 고가/저가 트리거와 거래량 동반 여부로 시나리오 판단)"

    out["evidence"] = {"전일": prev_day_block, "금일(조건부)": today_block}
    out["전망"] = outlook
    return out


# =========================================================
# 7) 메인: 한 종목 -> 장기/중기/단기 전망 출력
# =========================================================

def analyze_one_ticker(ticker_code: str) -> Dict[str, Any]:
    td = fetch_ticker_data(ticker_code)

    long_res = evidence_long_term(td)
    mid_res = evidence_mid_term(td)
    short_res = evidence_short_term(td)

    return {
        "ticker": td.ticker,
        "장기": long_res,
        "중기": mid_res,
        "단기": short_res,
        "요약": {
            "장기전망": long_res.get("전망") if isinstance(long_res, dict) else None,
            "중기전망": mid_res.get("전망") if isinstance(mid_res, dict) else None,
            "단기전망": short_res.get("전망") if isinstance(short_res, dict) else None,
        }
    }


def pretty_print_all(result: Dict[str, Any]):
    print("\n" + "=" * 80)
    print(f"✅ 분석 종목: {result.get('ticker')}")
    print("=" * 80)

    summary = result.get("요약", {})
    print("\n[전망 요약]")
    print(f"- 장기: {summary.get('장기전망')}")
    print(f"- 중기: {summary.get('중기전망')}")
    print(f"- 단기: {summary.get('단기전망')}")

    # 섹션별 상세
    for horizon in ["장기", "중기", "단기"]:
        sec = result.get(horizon, {})
        print("\n" + "#" * 80)
        print(f"[{horizon} 상세]")
        print("#" * 80)

        if isinstance(sec, dict) and "error" in sec:
            print("❌ 오류:", sec["error"])
            continue

        outlook = sec.get("전망") if isinstance(sec, dict) else None
        if outlook:
            print("\n- 전망:", outlook)

        evidence = sec.get("evidence") if isinstance(sec, dict) else None
        if not isinstance(evidence, dict):
            print("(evidence 없음)")
            continue

        for k, v in evidence.items():
            print("\n" + "-" * 80)
            print(f"[{k}]")
            print("-" * 80)
            _print_nested(v)


def _print_nested(obj, indent: int = 0):
    prefix = " " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                print(f"{prefix}- {k}:")
                _print_nested(v, indent + 2)
            else:
                print(f"{prefix}- {k}: {v}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj[:50]):
            if isinstance(x, (dict, list)):
                print(f"{prefix}- [{i}]")
                _print_nested(x, indent + 2)
            else:
                print(f"{prefix}- [{i}] {x}")
        if len(obj) > 50:
            print(f"{prefix}... (총 {len(obj)}개 중 50개만 표시)")
    else:
        print(f"{prefix}{obj}")


def run_cli():
    print("📈 한 종목 장기/중기/단기 Evidence & 전망 (yfinance)")
    print("-" * 70)
    code = input("종목코드를 입력하세요 (예: 005930 / 035420.KS / AAPL): ").strip()

    print("\n⏳ 분석 중...\n")
    try:
        res = analyze_one_ticker(code)
        pretty_print_all(res)
    except Exception as e:
        print("❌ 실행 중 오류:", e)


if __name__ == "__main__":
    run_cli()
