"""Rolling/expanding out-of-sample forecasting toolkit for Forecasting Horserace.

Input arrays are chronological. Returns are in decimal units (e.g. 0.01 = 1%).
OLS exogenous columns must be known at forecast origin and lag-aligned.
"""
from __future__ import annotations
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
try:
    from arch import arch_model
except ImportError:
    arch_model = None

EPS = 1e-12

def rmse(actual, forecast):
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    return float(np.sqrt(np.mean((a-f)**2)))

def mae(actual, forecast):
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    return float(np.mean(np.abs(a-f)))

def qlike(realized_variance, forecast_variance):
    rv=np.maximum(np.asarray(realized_variance,float),EPS)
    fv=np.maximum(np.asarray(forecast_variance,float),EPS)
    # QLIKE convention; constant terms do not affect model rankings.
    return float(np.mean(np.log(fv)+rv/fv))

def dm_test(loss_a, loss_b, horizon=1):
    """Two-sided DM test using Bartlett HAC estimate (lag h-1).

    Returns statistic, approximate normal p-value, and mean loss differential.
    Positive differential means `loss_b` has lower average loss.
    """
    d=np.asarray(loss_a,float)-np.asarray(loss_b,float)
    d=d[np.isfinite(d)]; n=len(d)
    if n<3: return {"statistic":None,"p_value":None,"mean_loss_difference":None,"n":n}
    mean=float(d.mean()); u=d-mean
    lag=min(max(int(horizon)-1,0),n-1)
    longrun=float(np.dot(u,u)/n)
    for k in range(1,lag+1):
        gamma=float(np.dot(u[k:],u[:-k])/n)
        longrun+=2*(1-k/(lag+1))*gamma
    var_mean=max(longrun/n,EPS)
    stat=mean/np.sqrt(var_mean)
    from math import erf,sqrt
    p=2*(1-(.5*(1+erf(abs(stat)/sqrt(2)))))
    return {"statistic":float(stat),"p_value":float(np.clip(p,0,1)),
            "mean_loss_difference":mean,"n":n}

def _ols_fit_predict(y, x, next_x):
    """OLS with intercept, exog as supplied at forecast origin.

    To avoid look-ahead, user should pass columns already lagged such that
    x[t] is available before y[t]'s forecast is issued.
    """
    if x.shape[1]<2: raise ValueError("OLS requires at least two explanatory variables.")
    fit=OLS(y,add_constant(x,has_constant="add")).fit()
    pred=fit.predict(add_constant(np.asarray(next_x,float).reshape(1,-1),has_constant="add"))
    return float(pred[0]), fit

def _arima_forecast(y, order):
    fit=ARIMA(y,order=tuple(order),trend="c" if tuple(order)[1]==0 else "n").fit()
    return float(fit.forecast(steps=1)[0]),fit

def _garch_forecast(y, horizon=1, distribution="t"):
    if arch_model is None: raise ImportError("Install arch to run GARCH.")
    fit=arch_model(y*100,mean="AR",lags=1,vol="GARCH",p=1,q=1,
                   dist=distribution,rescale=False).fit(disp="off")
    f=fit.forecast(horizon=horizon,reindex=False)
    mean=float(f.mean.iloc[-1,horizon-1]/100)
    variance=float(f.variance.iloc[-1,horizon-1]/10000)
    return mean,max(variance,EPS),fit

def rolling_evaluation(returns, exog, window=500, evaluation_size=250,
                       horizon=1, scheme="expanding", arima_order=(1,0,1),
                       garch_distribution="t"):
    """One-step rolling-origin forecast evaluation.

    For h>1, a fixed-origin h-step forecast is issued for each origin, but
    this compact implementation scores the target at origin+h-1. OLS uses
    exog[origin-1] as the latest known covariate. For direct multi-step OLS,
    provide a dedicated target/feature alignment in your extension.
    """
    y=np.asarray(returns,float); x=np.asarray(exog,float)
    if y.ndim!=1 or x.ndim!=2 or len(y)!=len(x) or x.shape[1]<2:
        raise ValueError("returns must be 1D; exog aligned 2D with >=2 columns required.")
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError("Inputs contain NaN/inf. Resolve missing data before modeling.")
    if scheme not in {"rolling","expanding"}: raise ValueError("scheme must be rolling or expanding.")
    if window<60 or window>=len(y): raise ValueError("window must be >=60 and less than sample length.")
    if horizon<1: raise ValueError("horizon must be >=1.")
    eval_size=int(evaluation_size)
    first=max(window,len(y)-eval_size)
    records=[]
    for origin in range(first,len(y)-horizon+1):
        start=max(0,origin-window) if scheme=="rolling" else 0
        train_y=y[start:origin]; train_x=x[start:origin]
        target=origin+horizon-1
        # Features for target are shifted in advance and available at origin.
        known_x=x[origin-1]
        try: ols,olsfit=_ols_fit_predict(train_y,train_x,known_x)
        except Exception: ols=float(np.mean(train_y))
        try: arima,arimafit=_arima_forecast(train_y,arima_order)
        except Exception: arima=float(np.mean(train_y))
        try: hybrid_mean,garch_var,garchfit=_garch_forecast(train_y,horizon,garch_distribution)
        except Exception:
            hybrid_mean=arima; garch_var=float(np.var(train_y,ddof=1))
        # Naive mean benchmark for returns: zero.
        naive=0.0
        actual=float(y[target]); rv=actual**2
        records.append({"origin_index":int(origin),"target_index":int(target),"actual":actual,
            "OLS":ols,"ARIMA":arima,"ARIMA_GARCH_mean":hybrid_mean,"Naive":naive,
            "GARCH_variance":max(float(garch_var),EPS),"realized_variance_proxy":max(rv,EPS)})
    if not records: raise ValueError("No forecasts produced; revise window/evaluation size/horizon.")
    actual=np.array([r["actual"] for r in records])
    names=("OLS","ARIMA","ARIMA_GARCH_mean","Naive")
    forecasts={n:np.array([r[n] for r in records]) for n in names}
    losses={n:(actual-forecasts[n])**2 for n in names}
    naive_rmse=max(rmse(actual,forecasts["Naive"]),EPS)
    mean_scores={}
    for n in names:
        mean_scores[n]={"RMSE":rmse(actual,forecasts[n]),"MAE":mae(actual,forecasts[n]),
            "RMSE_loss_ratio_vs_Naive":rmse(actual,forecasts[n])/naive_rmse,
            "directional_accuracy_pct":float(100*np.mean(np.sign(actual)==np.sign(forecasts[n]))),
            "cumulative_squared_loss":float(np.sum(losses[n]))}
    rv=np.array([r["realized_variance_proxy"] for r in records])
    gv=np.array([r["GARCH_variance"] for r in records])
    # Historical variance benchmark based on the estimation sample at each origin.
    hv=[]
    for r in records:
        origin=r["origin_index"]
        st=max(0,origin-window) if scheme=="rolling" else 0
        hv.append(max(float(np.var(y[st:origin],ddof=1)),EPS))
    hv=np.asarray(hv)
    var_scores={
      "GARCH":{"Variance_RMSE":rmse(rv,gv),"QLIKE":qlike(rv,gv)},
      "Historical_Variance_Naive":{"Variance_RMSE":rmse(rv,hv),"QLIKE":qlike(rv,hv)},
    }
    var_scores["GARCH"]["Variance_RMSE_loss_ratio_vs_Naive"]=var_scores["GARCH"]["Variance_RMSE"]/max(var_scores["Historical_Variance_Naive"]["Variance_RMSE"],EPS)
    var_scores["GARCH"]["QLIKE_loss_ratio_vs_Naive"]=var_scores["GARCH"]["QLIKE"]/max(var_scores["Historical_Variance_Naive"]["QLIKE"],EPS)
    dm={}
    for n in ("OLS","ARIMA","ARIMA_GARCH_mean"):
        dm[f"{n}_vs_Naive"]=dm_test(losses[n],losses["Naive"],horizon)
    dm["OLS_vs_ARIMA"]=dm_test(losses["OLS"],losses["ARIMA"],horizon)
    return {"design":{"scheme":scheme,"window":int(window),"evaluation_size":len(records),
        "horizon":int(horizon),"arima_order":list(arima_order),
        "first_target_index":records[0]["target_index"],"last_target_index":records[-1]["target_index"]},
        "mean_race":mean_scores,"volatility_race":var_scores,"die-bold_mariano":dm,"forecasts":records}

def fit_next_forecast(returns,exog,window=500,horizon=1,arima_order=(1,0,1)):
    y=np.asarray(returns,float); x=np.asarray(exog,float)
    if y.ndim!=1 or x.ndim!=2 or len(y)!=len(x) or x.shape[1]<2:
        raise ValueError("returns and exog must align; exog needs at least 2 columns.")
    if len(y)<60 or not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError("At least 60 finite observations are required.")
    start=max(0,len(y)-window); yy=y[start:]; xx=x[start:]
    try: ols,_=_ols_fit_predict(yy,xx,xx[-1])
    except Exception: ols=float(np.mean(yy))
    try: arima,_=_arima_forecast(yy,arima_order)
    except Exception: arima=float(np.mean(yy))
    try: hybrid_mean,var,_=_garch_forecast(yy,horizon)
    except Exception: hybrid_mean=arima; var=max(float(np.var(yy,ddof=1)),EPS)
    return {"OLS":ols,"ARIMA":arima,"ARIMA_GARCH_mean":hybrid_mean,"Naive":0.0,
            "GARCH_variance":var,"training_observations":len(yy),"window":window,"horizon":horizon}
