"""Bloomberg CSV ingestion. Expected long or one-ticker wide format.

Required fields: date, close (or PX_LAST). Optional feature columns can be
included as exog_* columns. Align/lag predictors before calling backtest.
"""
from pathlib import Path
import pandas as pd
import numpy as np

PRICE_CANDIDATES=("close","px_last","PX_LAST","Close","price")
DATE_CANDIDATES=("date","Date","DATE")

def load_bloomberg_csv(path, ticker=None):
    df=pd.read_csv(Path(path))
    date_col=next((c for c in DATE_CANDIDATES if c in df.columns),None)
    price_col=next((c for c in PRICE_CANDIDATES if c in df.columns),None)
    if date_col is None or price_col is None:
        raise ValueError("CSV requires date and close/PX_LAST columns.")
    if ticker and "ticker" in df.columns:
        df=df[df["ticker"].astype(str).str.upper()==ticker.upper()]
    df[date_col]=pd.to_datetime(df[date_col],errors="coerce")
    df[price_col]=pd.to_numeric(df[price_col],errors="coerce")
    df=df.dropna(subset=[date_col,price_col]).sort_values(date_col)
    df=df.drop_duplicates(subset=[date_col],keep="last")
    if len(df)<2: raise ValueError("Not enough valid observations.")
    df["returns"]=100*np.log(df[price_col]).diff()
    # For OLS, require >=2 factors. No synthetic factor variables are silently
    # generated; user should supply aligned/lagged market or macro series.
    exog_cols=[c for c in df.columns if c.startswith("exog_")]
    if len(exog_cols)<2:
        raise ValueError("Provide at least two aligned factor columns named exog_1, exog_2, ...")
    # Assumption: factors in the row have already been lagged and were available
    # at the forecast origin. Document timing/availability in your report.
    clean=df.dropna(subset=["returns"]+exog_cols).copy()
    return clean, exog_cols
