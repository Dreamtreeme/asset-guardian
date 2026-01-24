import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Any, Optional, List, Tuple
from services.collector import TickerData

US_SECTOR_TO_ETFS: Dict[str, List[str]] = {
    "Technology": ["XLK"], "Financial Services": ["XLF"], "Financial": ["XLF"],
    "Health Care": ["XLV"], "Healthcare": ["XLV"], "Consumer Cyclical": ["XLY"],
    "Consumer Defensive": ["XLP"], "Energy": ["XLE"], "Industrials": ["XLI"],
    "Basic Materials": ["XLB"], "Utilities": ["XLU"], "Real Estate": ["XLRE"],
    "Communication Services": ["XLC"],
}

KR_SECTOR_TO_ETFS: Dict[str, List[str]] = {
    "IT": ["363580.KS"], "HEALTHCARE": ["266420.KS"], "FINANCIAL": ["091170.KS"], "BROAD": ["069500.KS"],
}

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def recent_support_resistance(close: pd.Series, lookback: int = 20) -> Tuple[float, float]:
    window = close.iloc[-lookback:] if len(close) > lookback else close
    return float(window.min()), float(window.max())

def calculate_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-12)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

def analyze_mid_term(td: TickerData) -> Dict[str, Any]:
    close = td.px_10y["Close"].dropna()
    if len(close) < 60: return {"error": "데이터 부족"}

    # 국면 판정 (Mock/Simple version for demo)
    vix = yf.Ticker("^VIX").history(period="1mo", auto_adjust=False)
    vix_last = vix["Close"].iloc[-1] if not vix.empty else 20
    regime = "불안" if vix_last > 25 else "완화"

    # 기술적 구조
    support, resistance = recent_support_resistance(close)
    last_close = float(close.iloc[-1])
    rr = (resistance - last_close) / (last_close - support + 1e-12) if last_close > support and resistance > last_close else None
    
    rsi_val = calculate_rsi(close)

    # 상대성과 (Sector)
    is_kr = td.ticker.endswith(".KS") or td.ticker.endswith(".KQ")
    sector_label = "IT" # Simplification
    outlook = "중기 우호" if regime == "완화" and (rr is None or rr > 1.5) else "중기 중립"

    return {
        "evidence": {
            "국면": regime,
            "VIX": vix_last,
            "지지선": support,
            "저항선": resistance,
            "익절_손절비": rr,
            "RSI": rsi_val
        },
        "outlook": outlook
    }

def analyze_short_term(td: TickerData) -> Dict[str, Any]:
    px = td.px_10y.iloc[-60:].copy()
    if len(px) < 10: return {"error": "데이터 부족"}

    d1 = px.iloc[-1]
    d2 = px.iloc[-2]
    
    vol_mult = float(d1["Volume"] / px["Volume"].iloc[-6:-1].mean()) if px["Volume"].iloc[-6:-1].mean() != 0 else 1.0
    gap = float((d1["Open"] / d2["Close"]) - 1.0)
    body = float((d1["Close"] / d1["Open"]) - 1.0)

    y_high, y_low, y_close = float(d1["High"]), float(d1["Low"]), float(d1["Close"])
    
    # Pivot Points
    pivot = (y_high + y_low + y_close) / 3
    r1 = 2 * pivot - y_low
    s1 = 2 * pivot - y_high
    
    rsi_val = calculate_rsi(px["Close"])

    outlook = "단기 강세" if body > 0.02 and vol_mult > 1.5 else "단기 중립"

    return {
        "evidence": {
            "전일": {
                "거래량배수": vol_mult,
                "갭": gap,
                "캔들바디": body
            },
            "금일피봇": {
                "Pivot": pivot,
                "R1": r1,
                "S1": s1
            },
            "RSI": rsi_val
        },
        "outlook": outlook
    }
