"""FastAPI service for the Forecasting Horserace React frontend."""
from typing import Literal
import os
from datetime import datetime, timezone
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from evaluation import rolling_evaluation, fit_next_forecast

app = FastAPI(title="Forecasting Horserace API", version="1.2")
cors_origins = [origin.strip() for origin in os.getenv(
    "BACKEND_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ForecastRequest(BaseModel):
    returns: list[float] = Field(min_length=60)
    exog: list[list[float]] = Field(min_length=60, description="Aligned features with at least two columns.")
    window: int = Field(default=250, ge=60)
    horizon: int = Field(default=1, ge=1, le=5)
    arima_order: tuple[int, int, int] = (1, 0, 1)
    ols_weights: tuple[float, float, float] | None = None

    @model_validator(mode="after")
    def check_alignment(self):
        if len(self.returns) != len(self.exog):
            raise ValueError("returns and exog must have the same number of observations.")
        if any(len(row) < 2 for row in self.exog):
            raise ValueError("Each exog row must contain at least two features.")
        return self


class EvaluationRequest(BaseModel):
    returns: list[float] = Field(min_length=100)
    exog: list[list[float]] = Field(min_length=100, description="Date-aligned explanatory variables; at least two columns.")
    window: int = Field(default=250, ge=60)
    evaluation_size: int = Field(default=250, ge=20)
    horizon: int = Field(default=1, ge=1, le=5)
    scheme: Literal["rolling", "expanding"] = "rolling"
    arima_order: tuple[int, int, int] = (1, 0, 1)

    @model_validator(mode="after")
    def check_alignment(self):
        if len(self.returns) != len(self.exog):
            raise ValueError("returns and exog must have the same number of observations.")
        if any(len(row) < 2 for row in self.exog):
            raise ValueError("Each exog row must contain at least two columns.")
        return self


@app.get("/health")
def health():
    return {"status": "ok", "mean_race": ["OLS", "ARIMA", "Naive"], "volatility_race": ["GARCH"]}



@app.get("/market-stats")
def market_stats():
    """Fetch a daily close snapshot for a small multi-asset watchlist."""
    try:
        import yfinance as yf
        symbols = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "Apple": "AAPL",
            "Microsoft": "MSFT",
            "Adobe": "ADBE",
            "NVIDIA": "NVDA",
        }
        raw = yf.download(list(symbols.values()), period="5d", interval="1d",
                          auto_adjust=False, progress=False, group_by="ticker",
                          threads=True)
        items = []
        for label, ticker in symbols.items():
            try:
                closes = raw[ticker]["Close"].dropna()
                if len(closes) < 2:
                    continue
                latest, previous = float(closes.iloc[-1]), float(closes.iloc[-2])
                items.append({
                    "asset": label,
                    "ticker": ticker,
                    "last_close": latest,
                    "daily_change_pct": (latest / previous - 1) * 100 if previous else None,
                    "as_of": closes.index[-1].isoformat(),
                })
            except (KeyError, TypeError, ValueError):
                continue
        if not items:
            raise ValueError("The market data provider returned no daily close values.")
        return {
            "provider": "Yahoo Finance via yfinance",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
            "note": "Daily close snapshot; not intraday quotes.",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {exc}") from exc

@app.post("/forecast")
def forecast(req: ForecastRequest):
    try:
        return fit_next_forecast(req.returns, req.exog, window=req.window,
                                 horizon=req.horizon, arima_order=req.arima_order,
                                 ols_weights=req.ols_weights)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/evaluate")
def evaluate(req: EvaluationRequest):
    try:
        return rolling_evaluation(req.returns, req.exog, window=req.window,
                                  evaluation_size=req.evaluation_size, horizon=req.horizon,
                                  scheme=req.scheme, arima_order=req.arima_order)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/market-history/{ticker}")
def market_history(ticker: str, period: str = "2y", interval: str = "1d"):
    """Return actual OHLC history and aligned close-to-close log returns."""
    allowed_periods = {"6mo", "1y", "2y", "5y"}
    allowed_intervals = {"1d"}
    if period not in allowed_periods or interval not in allowed_intervals:
        raise HTTPException(status_code=400, detail="Use period 6mo/1y/2y/5y and interval 1d.")
    if not ticker or len(ticker) > 16 or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789^.-=" for c in ticker.upper()):
        raise HTTPException(status_code=400, detail="Invalid ticker.")
    try:
        import yfinance as yf
        df = yf.download(ticker.upper(), period=period, interval=interval,
                         auto_adjust=True, progress=False, threads=False)
        if df.empty:
            raise ValueError("No OHLC observations returned.")
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        closes = df["Close"].astype(float)
        log_returns = np.log(closes / closes.shift(1)).dropna()
        candles = []
        for dt, row in df.iterrows():
            candles.append({
                "date": dt.strftime("%Y-%m-%d"),
                "open": float(row["Open"]), "high": float(row["High"]),
                "low": float(row["Low"]), "close": float(row["Close"]),
            })
        return {
            "ticker": ticker.upper(), "period": period, "interval": interval,
            "provider": "Yahoo Finance via yfinance", "adjusted": True,
            "candles": candles,
            "log_returns": [{"date": dt.strftime("%Y-%m-%d"), "value": float(v)}
                            for dt, v in log_returns.items()],
            "note": "Adjusted daily OHLC; log return is 100 × ln(Close_t / Close_t-1), in percentage points.",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to retrieve history: {exc}") from exc
