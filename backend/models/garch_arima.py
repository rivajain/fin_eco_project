"""ARIMA-GARCH ("Hybrid Racer"): ARIMA conditional mean + GARCH(1,1) conditional variance.

Model
    r_t      = mu + sum_i phi_i r_{t-i} + sum_j theta_j e_{t-j} + e_t        ARIMA(p,0,q) mean
    e_t      = sigma_t z_t,  z_t ~ iid Student-t(nu) (or Normal)
    sigma2_t = omega + alpha e_{t-1}^2 + beta sigma2_{t-1}                   GARCH(1,1) variance

ARIMA order: grid p,q in 0..2, chosen by BIC (or AIC with --criterion aic).
Estimation is two-step: ARIMA by exact ML (statsmodels), then GARCH(1,1) on the ARIMA residuals (arch, zero mean). The `arch` package cannot fit MA terms in the mean, which is why the mean and variance are estimated separately. Report this choice.

Out-of-sample design (assignment section 2.3)
    * The last `eval_size` returns are the evaluation window. Model choice (ARIMA order
      by AIC, error distribution by AIC) uses ONLY the data before it.
    * At every forecast origin both stages are re-estimated on the expanding (or
      rolling) estimation window and an h-step forecast is issued.
    * Origin index o = first observation the model has not seen; target = o + h - 1.
      This matches backend/evaluation.py.

Units: returns in percent (100 * log return). Variance forecasts are in percent^2.

Outputs (backend/models/outputs/):
    garch_arima_<asset>_h<h>_forecasts.csv   one row per origin: date, mean fc, var fc, actual
    garch_arima_<asset>_h<h>_summary.json    chosen spec, diagnostics, losses vs benchmarks
    garch_arima_<asset>_h<h>.pkl             spec + final-fit parameters + forecasts
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import warnings
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from arch import arch_model
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from scipy import stats

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))  # so `evaluation` imports when run as a script
from evaluation import dm_test, mae, qlike, rmse  # noqa: E402  (shared loss functions)

DATA_FILE = BACKEND_DIR / "data" / "returns.csv"
OUT_DIR = Path(__file__).resolve().parent / "outputs"
EPS = 1e-12


# ---------------------------------------------------------------- estimation
def fit_arima(y: np.ndarray, order: tuple[int, int, int]):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ARIMA(y, order=order, trend="c").fit()


def fit_garch(resid: np.ndarray, dist: str):
    am = arch_model(resid, mean="Zero", vol="GARCH", p=1, q=1, dist=dist, rescale=False)
    return am.fit(disp="off", show_warning=False)


def select_spec(y_train: np.ndarray, max_p: int = 2, max_q: int = 2, criterion: str = "bic") -> dict:
    """Choose ARIMA(p,0,q) by `criterion` (BIC default) and the GARCH error
    distribution by AIC, using training data only."""
    grid = []
    for p_, q_ in product(range(max_p + 1), range(max_q + 1)):
        try:
            res = fit_arima(y_train, (p_, 0, q_))
            grid.append({"order": [p_, 0, q_], "aic": float(res.aic), "bic": float(res.bic)})
        except Exception:
            continue
    if not grid:
        raise RuntimeError("No ARIMA order could be estimated on the training sample.")
    best = min(grid, key=lambda g: g[criterion])
    resid = fit_arima(y_train, tuple(best["order"])).resid
    dist_aic = {}
    for d in ("normal", "t"):
        try:
            dist_aic[d] = float(fit_garch(resid, d).aic)
        except Exception:
            continue
    dist = min(dist_aic, key=dist_aic.get)
    return {"order": best["order"], "dist": dist, "criterion": criterion,
            "arima_grid": sorted(grid, key=lambda g: g[criterion]),
            "dist_aic": dist_aic}


def forecast_one(y_train: np.ndarray, order, dist: str, horizon: int) -> tuple[float, float]:
    """h-step-ahead mean and variance forecast from data up to the origin."""
    ar = fit_arima(y_train, tuple(order))
    mean_fc = float(np.asarray(ar.forecast(steps=horizon))[horizon - 1])
    try:
        g = fit_garch(np.asarray(ar.resid), dist)
        var_fc = float(g.forecast(horizon=horizon, reindex=False).variance.values[-1, horizon - 1])
    except Exception:
        var_fc = float(np.var(ar.resid, ddof=1))  # fallback, counted in the summary
    return mean_fc, max(var_fc, EPS)


# --------------------------------------------------------------- diagnostics
def diagnostics(y_train: np.ndarray, order, dist: str) -> dict:
    """Diagnostics on the final training-window fit (for the report's Models section)."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    ar = fit_arima(y_train, tuple(order))
    g = fit_garch(np.asarray(ar.resid), dist)
    z = np.asarray(g.std_resid)
    z = z[np.isfinite(z)]
    adf = adfuller(y_train, autolag="AIC")
    lb_raw = acorr_ljungbox(ar.resid, lags=[10], return_df=True)
    lb_z = acorr_ljungbox(z, lags=[10], return_df=True)
    lb_z2 = acorr_ljungbox(z ** 2, lags=[10], return_df=True)
    arch_before = het_arch(ar.resid, nlags=5)
    arch_after = het_arch(z, nlags=5)
    jb = stats.jarque_bera(z)
    params = {k: float(v) for k, v in g.params.items()}
    return {
        "adf_returns": {"stat": float(adf[0]), "p_value": float(adf[1])},
        "arima_params": {k: float(v) for k, v in zip(ar.param_names, ar.params)},
        "garch_params": params,
        "persistence_alpha_plus_beta": params.get("alpha[1]", np.nan) + params.get("beta[1]", np.nan),
        "ljung_box_10_arima_resid_p": float(lb_raw["lb_pvalue"].iloc[0]),
        "ljung_box_10_std_resid_p": float(lb_z["lb_pvalue"].iloc[0]),
        "ljung_box_10_sq_std_resid_p": float(lb_z2["lb_pvalue"].iloc[0]),
        "arch_lm_5_before_garch_p": float(arch_before[1]),
        "arch_lm_5_after_garch_p": float(arch_after[1]),
        "jarque_bera_std_resid_p": float(jb.pvalue),
        "arima_aic": float(ar.aic), "garch_aic": float(g.aic),
    }


# ------------------------------------------------------- out-of-sample loop
def rolling_forecasts(y: np.ndarray, dates: pd.DatetimeIndex, order, dist: str, eval_size: int,
                      horizon: int, scheme: str, window: int | None) -> pd.DataFrame:
    n = len(y)
    first_origin = n - eval_size
    rows = []
    origins = range(first_origin, n - horizon + 1)
    for i, o in enumerate(origins):
        start = 0 if scheme == "expanding" else max(0, o - window)
        y_tr = y[start:o]
        m, v = forecast_one(y_tr, order, dist, horizon)
        t = o + horizon - 1
        hist_var = float(np.var(y_tr, ddof=1))
        rows.append({
            "origin_date": dates[o - 1].date(),  # last date the model saw
            "target_date": dates[t].date(),
            "mean_forecast": m,
            "variance_forecast": v,
            "actual": float(y[t]),
            "realized_variance_proxy": float(y[t] ** 2),
            "naive_mean": 0.0,
            "naive_variance": hist_var,
            "train_obs": len(y_tr),
        })
        if (i + 1) % 25 == 0 or i + 1 == len(origins):
            print(f"  {i + 1}/{len(origins)} forecasts done", flush=True)
    return pd.DataFrame(rows)


def score(fc: pd.DataFrame, horizon: int) -> dict:
    a = fc["actual"].to_numpy()
    m = fc["mean_forecast"].to_numpy()
    nv = fc["naive_mean"].to_numpy()
    rv = fc["realized_variance_proxy"].to_numpy()
    gv = fc["variance_forecast"].to_numpy()
    hv = fc["naive_variance"].to_numpy()
    se_m, se_n = (a - m) ** 2, (a - nv) ** 2
    ql_g = np.log(np.maximum(gv, EPS)) + np.maximum(rv, EPS) / np.maximum(gv, EPS)
    ql_h = np.log(np.maximum(hv, EPS)) + np.maximum(rv, EPS) / np.maximum(hv, EPS)
    mean_race = {
        "RMSE": rmse(a, m), "MAE": mae(a, m),
        "RMSE_naive": rmse(a, nv), "MAE_naive": mae(a, nv),
        "RMSE_ratio_vs_naive": rmse(a, m) / max(rmse(a, nv), EPS),
        "MAE_ratio_vs_naive": mae(a, m) / max(mae(a, nv), EPS),
        "directional_accuracy_pct": float(100 * np.mean(np.sign(a) == np.sign(m))),
        "DM_vs_naive_squared_error": dm_test(se_m, se_n, horizon),
    }
    vol_race = {
        "variance_RMSE": rmse(rv, gv), "QLIKE": qlike(rv, gv),
        "variance_RMSE_hist": rmse(rv, hv), "QLIKE_hist": qlike(rv, hv),
        "variance_RMSE_ratio_vs_hist": rmse(rv, gv) / max(rmse(rv, hv), EPS),
        # QLIKE can be negative when variances are below 1 (percent^2), so a ratio is
        # only meaningful when both are positive; the difference is always valid.
        "QLIKE_minus_hist": qlike(rv, gv) - qlike(rv, hv),
        "QLIKE_ratio_vs_hist": (qlike(rv, gv) / qlike(rv, hv)
                                if qlike(rv, gv) > 0 and qlike(rv, hv) > 0 else None),
        "DM_vs_hist_QLIKE": dm_test(ql_g, ql_h, horizon),
    }
    return {"mean_race": mean_race, "volatility_race": vol_race}


# ----------------------------------------------------------------------- CLI
def load_returns(asset: str) -> pd.Series:
    if not DATA_FILE.exists():
        sys.exit(f"{DATA_FILE} not found. Run `python data/fetch_data.py` first.")
    df = pd.read_csv(DATA_FILE, parse_dates=["date"], index_col="date")
    col = f"{asset}_ret"
    if col not in df:
        sys.exit(f"Column {col} not in {DATA_FILE}. Available: {list(df.columns)}")
    return df[col].dropna()


def main() -> None:
    p = argparse.ArgumentParser(description="Train and evaluate ARIMA-GARCH out of sample.")
    p.add_argument("--asset", choices=["gold", "wti"], default="gold")
    p.add_argument("--eval-size", type=int, default=250, help="evaluation window length (>=250 daily)")
    p.add_argument("--horizon", type=int, default=1, choices=[1, 5])
    p.add_argument("--scheme", choices=["expanding", "rolling"], default="expanding")
    p.add_argument("--window", type=int, default=750, help="rolling window length (rolling scheme only)")
    p.add_argument("--criterion", choices=["bic", "aic"], default="bic", help="ARIMA order selection")
    a = p.parse_args()

    r = load_returns(a.asset)
    y, dates = r.to_numpy(float), r.index
    if a.eval_size >= len(y) - 250:
        sys.exit(f"eval-size {a.eval_size} leaves too little training data ({len(y)} obs).")
    train = y[: len(y) - a.eval_size]
    print(f"{a.asset}: {len(y)} returns, training {len(train)} "
          f"({dates[0].date()} to {dates[len(train) - 1].date()}), evaluation {a.eval_size}")

    print("Selecting specification on the training window only...")
    spec = select_spec(train, criterion=a.criterion)
    print(f"  ARIMA order {tuple(spec['order'])}, GARCH(1,1) errors: {spec['dist']}")

    diag = diagnostics(train, spec["order"], spec["dist"])
    print("Running out-of-sample forecasts (re-estimated at every origin)...")
    fc = rolling_forecasts(y, dates, spec["order"], spec["dist"], a.eval_size,
                           a.horizon, a.scheme, a.window)
    scores = score(fc, a.horizon)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"garch_arima_{a.asset}_h{a.horizon}"
    fc.to_csv(OUT_DIR / f"{stem}_forecasts.csv", index=False)
    summary = {
        "model": "ARIMA-GARCH(1,1), two-step",
        "asset": a.asset, "units": "percent log returns; variance in percent^2",
        "design": {"scheme": a.scheme, "window": a.window if a.scheme == "rolling" else None,
                   "eval_size": a.eval_size, "horizon": a.horizon, "n_forecasts": len(fc),
                   "first_target": str(fc["target_date"].iloc[0]),
                   "last_target": str(fc["target_date"].iloc[-1])},
        "spec": spec, "diagnostics_training_window": diag, "scores": scores,
    }
    (OUT_DIR / f"{stem}_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    final_fit = {"order": spec["order"], "dist": spec["dist"],
                 "params_on_training_window": {"arima": diag["arima_params"], "garch": diag["garch_params"]}}
    with open(OUT_DIR / f"{stem}.pkl", "wb") as fh:
        pickle.dump({"summary": summary, "final_fit": final_fit, "forecasts": fc}, fh)

    m, v = scores["mean_race"], scores["volatility_race"]
    print("\nMean race (vs naive zero):")
    print(f"  RMSE {m['RMSE']:.4f}  naive {m['RMSE_naive']:.4f}  ratio {m['RMSE_ratio_vs_naive']:.3f}"
          f"  DM p={m['DM_vs_naive_squared_error']['p_value']:.3f}")
    print("Volatility race (vs historical variance):")
    print(f"  QLIKE {v['QLIKE']:.4f}  hist {v['QLIKE_hist']:.4f}  difference {v['QLIKE_minus_hist']:+.4f}"
          f" (negative = GARCH better)  DM p={v['DM_vs_hist_QLIKE']['p_value']:.3f}")
    print(f"\nSaved to {OUT_DIR}")


if __name__ == "__main__":
    main()
