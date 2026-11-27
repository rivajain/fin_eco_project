"""
ols.py - OLS model for the Forecasting Horserace (FIN41660).
Target: daily WTI log returns, Oct 2021 - Sep 2026.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

SERIES = {
    "brent": ("DCOILBRENTEU.csv", "DCOILBRENTEU"),
    "wti":   ("DCOILWTICO.csv",   "DCOILWTICO"),
    "gold":  ("GC_F_yahoo.csv",   "Adj Close"),
    "usd":   ("DTWEXBGS.csv",     "DTWEXBGS"),
    "vix":   ("VIXCLS.csv",       "VIXCLS"),
    "ry10":  ("DFII10.csv",       "DFII10"),
}
START, END = "2021-10-01", "2026-09-30"
REGRESSORS = ["y", "usd_ret", "vix_chg", "ry10_chg", "spread", "gold_ret"]


def load_data(data_dir=DATA_DIR, start=START, end=END):
    """Load the CSVs, clean them, and return WTI returns + regressors (all on day t)."""
    # 1. load all files into one table of levels
    columns = {}
    for name, (file, col) in SERIES.items():
        df = pd.read_csv(Path(data_dir) / file)
        values = pd.to_numeric(df[col], errors="coerce")
        columns[name] = pd.Series(values.values, index=pd.to_datetime(df[df.columns[0]]))
    raw = pd.concat(columns, axis=1).sort_index().loc[start:end]

    # 2. clean: keep WTI trading days, forward-fill regressors max 3 days
    others = ["brent", "gold", "usd", "vix", "ry10"]
    clean = raw.copy()
    clean[others] = clean[others].ffill(limit=3)
    clean = clean[clean["wti"].notna()].dropna()
    if (clean["wti"] <= 0).any():
        raise ValueError("WTI has non-positive prices: log returns impossible")

    # 3. returns and regressors
    data = pd.DataFrame(index=clean.index)
    data["y"]        = 100 * np.log(clean["wti"]).diff()      # WTI log return, %
    data["usd_ret"]  = 100 * np.log(clean["usd"]).diff()      # dollar % change
    data["vix_chg"]  = clean["vix"].diff()                    # VIX change, points
    data["ry10_chg"] = 100 * clean["ry10"].diff()             # real yield change, bp
    data["spread"]   = 100 * (np.log(clean["brent"]) - np.log(clean["wti"]))  # Brent premium, %
    data["gold_ret"] = 100 * np.log(clean["gold"]).diff()     # gold log return, %
    return data.dropna()


def make_model_df(data, h=1):
    """Regressors known on day t + target = WTI return on day t+h."""
    model_df = data[REGRESSORS].copy()
    model_df.columns = [c + "_t" for c in REGRESSORS]
    model_df["target"] = data["y"].shift(-h)
    model_df = model_df.dropna()
    assert model_df["target"].iloc[0] == model_df["y_t"].iloc[h], "target is not h days ahead"
    return model_df


def forecast_ols(data, h=1, eval_frac=0.25):
    """Out-of-sample OLS forecasts (expanding window) vs the naive zero forecast."""
    if h < 1:
        raise ValueError("h must be 1 or more")
    if not 0 < eval_frac < 1:
        raise ValueError("eval_frac must be between 0 and 1")

    model_df = make_model_df(data, h)
    n = len(model_df)
    split = int(round(n * (1 - eval_frac)))
    if n - split < 250:
        raise ValueError(f"only {n - split} forecasts; the brief needs at least 250")

    X_all = np.column_stack([np.ones(n), model_df.drop(columns="target").to_numpy()])
    y_all = model_df["target"].to_numpy()

    rows = []
    for j in range(split, n):
        train_end = j - h + 1              # only rows whose target is already known
        beta_j, *_ = np.linalg.lstsq(X_all[:train_end], y_all[:train_end], rcond=None)
        origin = model_df.index[j]
        rows.append({
            "target_date": data.index[data.index.get_loc(origin) + h],
            "origin": origin,
            "actual": y_all[j],
            "ols": X_all[j] @ beta_j,
            "naive": 0.0,
        })
    return pd.DataFrame(rows).set_index("target_date")


def loss_ratios(fc):
    """RMSE, MAE and OLS / naive loss ratios."""
    rmse = lambda c: np.sqrt(((fc["actual"] - fc[c]) ** 2).mean())
    mae = lambda c: (fc["actual"] - fc[c]).abs().mean()
    return {
        "rmse_ols": rmse("ols"), "rmse_naive": rmse("naive"),
        "mae_ols": mae("ols"), "mae_naive": mae("naive"),
        "rmse_ratio": rmse("ols") / rmse("naive"),
        "mae_ratio": mae("ols") / mae("naive"),
    }


if __name__ == "__main__":
    data = load_data()
    print("Days:", len(data))
    for h in (1, 5):
        fc = forecast_ols(data, h=h, eval_frac=0.25)
        r = loss_ratios(fc)
        print(f"h={h}: {len(fc)} forecasts | RMSE ratio {r['rmse_ratio']:.3f} | MAE ratio {r['mae_ratio']:.3f}")
        fc.to_csv(Path(__file__).resolve().parent / f"ols_forecasts_h{h}.csv")
        



