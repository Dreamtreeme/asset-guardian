import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import numpy as np

@dataclass
class TickerData:
    ticker: str
    px_10y: pd.DataFrame
    info: Dict[str, Any]
    q_fin: Optional[pd.DataFrame]
    q_cf: Optional[pd.DataFrame]
    q_bs: Optional[pd.DataFrame]

class DataCollector:
    def __init__(self):
        pass

    def normalize_ticker(self, code: str) -> str:
        code = code.strip()
        if "." in code:
            return code
        if code.isdigit() and len(code) == 6:
            return f"{code}.KS"
        return code

    async def fetch_ticker_data(self, ticker_code: str) -> TickerData:
        tkr = self.normalize_ticker(ticker_code)
        tk = yf.Ticker(tkr)

        # history() is a blocking call, but yfinance doesn't have a native async version.
        # In a real production app, we might use run_in_executor.
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

        print(f"[DEBUG] FETCHED {tkr}: PX_10Y={len(px_10y)} rows, INFO={'Yes' if info else 'No'}, FIN={'Yes' if q_fin is not None else 'No'}, CF={'Yes' if q_cf is not None else 'No'}, BS={'Yes' if q_bs is not None else 'No'}")

        return TickerData(ticker=tkr, px_10y=px_10y, info=info, q_fin=q_fin, q_cf=q_cf, q_bs=q_bs)

collector = DataCollector()
