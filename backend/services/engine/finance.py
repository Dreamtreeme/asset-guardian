import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from services.collector import TickerData

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

def analyze_long_term(td: TickerData) -> Dict[str, Any]:
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
        "200일선_기울기": linreg_slope(ma200.dropna().iloc[-250:]) if ma200.dropna().shape[0] >= 20 else None,
        "300일선_기울기": linreg_slope(ma300.dropna().iloc[-250:]) if ma300.dropna().shape[0] >= 20 else None,
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
            "최근개선비율": improve_ratio,
            "분기수": int(s.shape[0]),
        }

    fund = {
        "매출": trend_pack(rev),
        "영업이익률": trend_pack(op_margin),
        "순이익률": trend_pack(net_margin),
        "FCF": trend_pack(fcf),
        "부채_자본": trend_pack(de_ratio),
    }

    improve_count, worsen_count = 0, 0
    for name, item in fund.items():
        if not item.get("사용가능"):
            continue
        slope = item.get("기울기")
        if slope is None or np.isnan(slope):
            continue
        if name == "부채_자본":
            if slope < 0: improve_count += 1
            elif slope > 0: worsen_count += 1
        else:
            if slope > 0: improve_count += 1
            elif slope < 0: worsen_count += 1

    fund_verdict = "✅ 개선" if improve_count >= 3 else ("❌ 악화" if worsen_count >= 3 else "⚠️ 혼합")

    # ---- 현재 밸류에이션
    info = td.info or {}
    def safe_first(d, *keys, default=None):
        for k in keys:
            if k in d and d[k] is not None: return d[k]
        return default

    valuation_now = {
        "trailingPE": safe_first(info, "trailingPE"),
        "forwardPE": safe_first(info, "forwardPE"),
        "priceToBook": safe_first(info, "priceToBook"),
        "trailingPEG": safe_first(info, "trailingPegRatio", "trailingPEG"),
        "marketCap": safe_first(info, "marketCap"),
    }

    price_ok = (
        price_block.get("200일선") is not None and
        price_block.get("현재가") > price_block.get("200일선") and
        (price_block.get("200일선_기울기") is None or price_block.get("200일선_기울기") >= 0)
    )
    outlook = "장기 우호" if "✅" in fund_verdict and price_ok else ("장기 비우호" if "❌" in fund_verdict and not price_ok else "장기 중립")

    return {
        "evidence": {
            "재무추세": fund,
            "장기추세": price_block,
            "밸류에이션": valuation_now,
            "판정": fund_verdict
        },
        "outlook": outlook,
    }
