# Data

Run from `backend/`:

```bash
python data/fetch_data.py                      # download from FRED, window 2021-10-01 to 2026-09-30
python data/fetch_data.py --offline            # build from CSVs saved by hand in data/raw/
python data/fetch_data.py --no-gold            # crude only
```

Manual download: on each FRED series page click **Download → CSV** and save the file in
`data/raw/` as `<SERIES_ID>.csv` (e.g. `DCOILWTICO.csv`). Write the download date in the report.

| File | Content |
|---|---|
| `raw/*.csv` | untouched downloads, one per series |
| `prices.csv` | date-aligned daily levels: `wti`, `gold`, plus candidate OLS regressors |
| `returns.csv` | `wti_ret`, `gold_ret` = 100 × ln(P_t / P_{t-1}), percent |
| `metadata.json` | sources, download time (UTC), cleaning log |

## Sources

| Column | Source | Notes |
|---|---|---|
| `wti` | FRED `DCOILWTICO` | WTI spot, Cushing OK, USD/bbl (EIA) |
| `gold` | Yahoo Finance `GC=F` (via yfinance, saved to `raw/GC_F_yahoo.csv`) | COMEX gold futures close; FRED removed its daily LBMA gold series in 2022 |
| `usd_broad` | FRED `DTWEXBGS` | Nominal broad U.S. dollar index |
| `real_yield_10y` | FRED `DFII10` | 10-year TIPS yield, % |
| `vix` | FRED `VIXCLS` | CBOE VIX close |
| `brent`, `brent_wti_spread` | FRED `DCOILBRENTEU` | Brent spot, Europe (EIA); spread = Brent − WTI |

The regressors are levels on the same date as the target. They are **not lagged** in
these files: OLS must use the value at t-1 (or a change from t-2 to t-1) to forecast the
return at t, otherwise it is not a real forecast.

## Missing values and non-trading days

- FRED writes `.` on holidays; these become missing.
- Target prices are **not** forward-filled (a filled price creates a fake 0% return).
  Only dates where both WTI and gold have a price are kept, so a return can span a
  day on which one market was closed.
- Non-positive prices are dropped (log return undefined).
- Regressors are forward-filled for at most 3 days on target dates; the count is logged.
