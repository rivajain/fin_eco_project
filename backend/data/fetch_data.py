"""Build the project dataset (WTI + gold + OLS regressors). Run from backend/:

    python data/fetch_data.py --offline      # use the CSVs in data/raw/
    python data/fetch_data.py --no-gold      # WTI only
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
START, END = "2021-10-01", "2026-09-30"

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_SERIES = {
    "wti": "DCOILWTICO",
    "usd_broad": "DTWEXBGS",
    "real_yield_10y": "DFII10",
    "vix": "VIXCLS",
    "brent": "DCOILBRENTEU",
}
GOLD_FILE = RAW_DIR / "GC_F_yahoo.csv"


def load_fred(series_id, offline):
    path = RAW_DIR / f"{series_id}.csv"
    if not offline:
        RAW_DIR.mkdir(exist_ok=True)
        pd.read_csv(FRED_URL.format(series_id)).to_csv(path, index=False)
    df = pd.read_csv(path)
    s = pd.to_numeric(df.iloc[:, 1], errors="coerce")  # holidays are blank or "."
    s.index = pd.to_datetime(df.iloc[:, 0])
    return s.dropna().groupby(level=0).last()  # one value per date


def load_gold(offline):
    if not (offline and GOLD_FILE.exists()):
        import yfinance as yf
        df = yf.download("GC=F", start=START, end="2026-10-01", auto_adjust=False, progress=False)
        if df.empty:
            raise SystemExit("Gold download from Yahoo failed. Try again later, or run with --no-gold.")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        RAW_DIR.mkdir(exist_ok=True)
        df.to_csv(GOLD_FILE)
    df = pd.read_csv(GOLD_FILE, index_col=0)
    s = pd.to_numeric(df["Close"], errors="coerce")
    s.index = pd.to_datetime(df.index, errors="coerce")
    return s[s.index.notna()].dropna().groupby(level=0).last()  # one value per date


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    p.add_argument("--no-gold", action="store_true")
    a = p.parse_args()

    series = {name: load_fred(sid, a.offline) for name, sid in FRED_SERIES.items()}
    targets = ["wti"]
    if not a.no_gold:
        series["gold"] = load_gold(a.offline)
        targets.append("gold")

    data = pd.concat(series, axis=1, sort=True).loc[START:END]

    # Returns per asset, each on its own trading days, so adding gold never changes
    # the WTI sample. No forward fill: a filled price would create a fake 0% return.
    returns = {}
    for t in targets:
        p = data[t].dropna()
        p = p[p > 0]
        returns[f"{t}_ret"] = (100 * np.log(p / p.shift(1))).dropna()
    returns = pd.concat(returns, axis=1, sort=True)  # blank where an asset did not trade

    # prices.csv is on WTI trading days (the OLS target). Regressors: gaps filled
    # for at most 3 days, not lagged here, so the OLS model must use the value at t-1.
    wti_days = data["wti"].dropna().index
    panel = data.reindex(wti_days)
    panel[panel.columns.drop(targets)] = panel[panel.columns.drop(targets)].ffill(limit=3)
    panel["brent_wti_spread"] = panel["brent"] - panel["wti"]

    panel.rename_axis("date").to_csv(DATA_DIR / "prices.csv")
    returns.rename_axis("date").to_csv(DATA_DIR / "returns.csv")

    meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": [START, END],
        "sources": {**{k: f"FRED {v}" for k, v in FRED_SERIES.items()},
                    **({} if a.no_gold else {"gold": "Yahoo Finance GC=F, close"})},
        "returns": "100 * ln(P_t / P_t-1), percent",
        "n_returns": {c: int(returns[c].count()) for c in returns},
    }
    (DATA_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    for c in returns:
        r = returns[c].dropna()
        print(f"{c}: {len(r)} daily returns, {r.index[0].date()} to {r.index[-1].date()}")


if __name__ == "__main__":
    main()
