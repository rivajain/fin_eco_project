import React from "react";
function EvaluationResults({data,error,loading}){
 if(loading)return <div className="eval-results"><h3>Running out-of-sample evaluation…</h3><p>Generating forecasts for each test origin. This may take a moment.</p></div>;
 if(error)return <div className="eval-results"><h3>Backtest could not run</h3><p>{error}</p><p>Check data length, estimation window, test size, and backend availability.</p></div>;
 if(!data)return <div className="eval-results"><h3>Evaluation not available</h3><p>Connect the backend and valid ticker data to generate the evaluation report.</p></div>;
 const mean=data.mean_race||{},vol=data.volatility_race||{},dm=data["die-bold_mariano"]||{},rows=data.forecasts||[];
 const seriesKeys=["OLS","ARIMA","ARIMA_GARCH_mean","Naive"];
 const scores=seriesKeys.map(name=>({name,...mean[name]}));
 const points=rows.slice(-Math.min(rows.length,250));
 const W=720,H=190,pad=26;
 const all=points.flatMap(r=>[r.actual,r.OLS,r.ARIMA,r.ARIMA_GARCH_mean]);
 const min=Math.min(...all,0),max=Math.max(...all,0),span=max-min||1;
 const x=i=>pad+i/(Math.max(1,points.length-1))*(W-2*pad);
 const y=v=>H-pad-(v-min)/span*(H-2*pad);
 const path=key=>points.map((r,i)=>`${i===0?"M":"L"}${x(i)},${y(r[key])}`).join(" ");
 let cum=0;const cumulative=points.map((r,i)=>{cum+=(r.actual-r.ARIMA)**2-(r.actual-r.Naive)**2;return {i,value:cum};});
 const cmin=Math.min(0,...cumulative.map(p=>p.value)),cmax=Math.max(0,...cumulative.map(p=>p.value)),cspan=cmax-cmin||1;
 const cy=v=>H-pad-(v-cmin)/cspan*(H-2*pad);
 const cpath=cumulative.map((p,i)=>`${i===0?"M":"L"}${x(i)},${cy(p.value)}`).join(" ");
 return <div className="eval-results">
 <div className="eval-title-row"><h3>Out-of-sample scorecard</h3><span>{data.design?.scheme} · {data.design?.evaluation_size} origins · h={data.design?.horizon}</span></div>
 <div className="eval-score-grid">{scores.map(s=><div className={`eval-score-card ${s.name==="Naive"?"benchmark":""}`} key={s.name}><b>{s.name==="ARIMA_GARCH_mean"?"ARIMA + GARCH mean":s.name}</b><span>RMSE {s.RMSE?.toFixed(5)??"—"}</span><span>MAE {s.MAE?.toFixed(5)??"—"}</span><small>RMSE loss ratio vs naive: {s.RMSE_loss_ratio_vs_Naive?.toFixed(3)??"—"}</small></div>)}</div>
 <h4>Forecasts vs actuals · Mean race</h4>
 <svg viewBox={`0 0 ${W} ${H}`} className="evaluation-chart" role="img" aria-label="Out of sample actual and forecast return series">
 {[.25,.5,.75].map(t=><line key={t} x1={pad} x2={W-pad} y1={H*t} y2={H*t} stroke="#29476c" strokeDasharray="3 4"/>)}<path d={path("actual")} fill="none" stroke="#f5d64c" strokeWidth="2.5"/><path d={path("OLS")} fill="none" stroke="#34e08b" strokeWidth="1.5"/><path d={path("ARIMA")} fill="none" stroke="#54bfff" strokeWidth="1.5"/><path d={path("ARIMA_GARCH_mean")} fill="none" stroke="#ffb44b" strokeWidth="1.5"/>
 </svg><div className="eval-legend"><span>● Actual</span><span>● OLS</span><span>● ARIMA</span><span>● ARIMA+GARCH mean</span></div>
 <h4>Cumulative loss differential · ARIMA vs Naive</h4><p className="eval-foot">Positive values indicate ARIMA has accumulated more squared loss than the naive benchmark; negative values indicate lower accumulated loss.</p>
 <svg viewBox={`0 0 ${W} ${H}`} className="evaluation-chart" role="img" aria-label="Cumulative squared loss differential of ARIMA compared with naive"><line x1={pad} x2={W-pad} y1={cy(0)} y2={cy(0)} stroke="#a7bad0" strokeDasharray="4 4"/><path d={cpath} fill="none" stroke="#c58aff" strokeWidth="2.5"/></svg>
 <h4>Volatility race</h4><div className="eval-score-grid"><div className="eval-score-card"><b>GARCH(1,1)</b><span>Variance RMSE {vol.GARCH?.Variance_RMSE?.toFixed(6)??"—"}</span><span>QLIKE {vol.GARCH?.QLIKE?.toFixed(5)??"—"}</span><small>Variance RMSE ratio vs naive: {vol.GARCH?.Variance_RMSE_loss_ratio_vs_Naive?.toFixed(3)??"—"}</small><small>QLIKE ratio vs naive: {vol.GARCH?.QLIKE_loss_ratio_vs_Naive?.toFixed(3)??"—"}</small></div><div className="eval-score-card benchmark"><b>Historical variance benchmark</b><span>Variance RMSE {vol.Historical_Variance_Naive?.Variance_RMSE?.toFixed(6)??"—"}</span><span>QLIKE {vol.Historical_Variance_Naive?.QLIKE?.toFixed(5)??"—"}</span></div></div>
 <h4>Diebold–Mariano tests · squared-error loss</h4><div className="eval-dm-table"><div><b>Comparison</b><b>DM statistic</b><b>p-value</b><b>Mean loss diff.</b></div>{Object.entries(dm).map(([name,v])=><div key={name}><span>{name.replaceAll("_"," ")}</span><span>{v.statistic?.toFixed(3)??"—"}</span><span>{v.p_value?.toFixed(4)??"—"}</span><span>{v.mean_loss_difference?.toFixed(6)??"—"}</span></div>)}</div>
 <p className="eval-foot">Metrics use the backend’s returned out-of-sample records. Daily squared return is a noisy realized-variance proxy. The DM p-values are approximate and interpretation depends on the loss-differential assumptions.</p>
 </div>;
}

export default EvaluationResults;
