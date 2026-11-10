import React from "react";
function Icon({type}){const icons={play:"▶",arena:"▥",lab:"⌁",learn:"▤",results:"♜",settings:"⚙",trophy:"♛",chart:"▥",target:"◎",info:"ℹ",flag:"⚑"};return <span className="icon">{icons[type]||"✦"}</span>;}
function HorseSprite({id, label, progress, rank, running=false, raceDuration=2}){return <div className={`race-horse horse-${id} ${progress>80?"finished":""} ${id==="you"&&running?"running":""} ${running?"race-running":""}`} style={{left:`${running?8:progress}%`,"--race-duration":`${raceDuration}s`,"--finish-position":`${({you:84,arima:78,ols:72,naive:66,garch:60}[id]||81)}%`}}><img src={`/pixel/reference-horse-${id}.png`} alt={`${label} pixel-art jockey and horse`}/><span className="horse-label">{label}</span>{rank&&<small className="horse-score">{rank}</small>}</div>}
function Chart({series}){let W=650,H=220,min=Math.min(...series)-.4,max=Math.max(...series)+.4;let pts=series.map((v,i)=>`${i/(series.length-1)*W},${H-(v-min)/(max-min)*H}`).join(" ");return <svg viewBox={`0 0 ${W} ${H}`} className="market-svg" role="img" aria-label="Historical synthetic return series"><defs><linearGradient id="goldfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f5cf4b" stopOpacity=".25"/><stop offset="1" stopColor="#f5cf4b" stopOpacity="0"/></linearGradient></defs>{[.2,.4,.6,.8].map(p=><g key={p}><line x1="0" x2={W} y1={H*p} y2={H*p} stroke="#2b4667" strokeDasharray="4 5"/><text x="0" y={H*p-5} fill="#8ba2bf" fontSize="11">{(max-(max-min)*p).toFixed(1)}</text></g>)}<polygon points={`0,${H} ${pts} ${W},${H}`} fill="url(#goldfade)"/><polyline points={pts} fill="none" stroke="#f5cf4b" strokeWidth="3" strokeLinejoin="round"/><line x1={W-2} x2={W-2} y1="0" y2={H} stroke="#c48bff" strokeDasharray="5 5" strokeWidth="2"/><text x={W-8} y="15" fill="#c48bff" textAnchor="end" fontSize="11">Forecast origin</text></svg>}
function CandlestickChart({candles}) {
 if(!candles?.length) return <p>No OHLC data loaded.</p>;
 const W=900,H=260,pad=30,lo=Math.min(...candles.map(c=>c.low)),hi=Math.max(...candles.map(c=>c.high));
 const y=v=>H-pad-(v-lo)/(hi-lo||1)*(H-2*pad), step=(W-2*pad)/candles.length;
 return <svg className="history-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Actual daily candlestick price chart">
  {[0,.25,.5,.75,1].map(t=><g key={t}><line x1={pad} x2={W-pad} y1={pad+t*(H-2*pad)} y2={pad+t*(H-2*pad)} stroke="#29476c"/><text x="2" y={pad+t*(H-2*pad)-3} fill="#9bb4d0" fontSize="11">{(hi-(hi-lo)*t).toFixed(2)}</text></g>)}
  {candles.map((c,i)=>{const x=pad+i*step+step/2,up=c.close>=c.open,color=up?"#44d69a":"#ff637b";return <g key={c.date}><line x1={x} x2={x} y1={y(c.high)} y2={y(c.low)} stroke={color} strokeWidth="1.2"/><rect x={x-Math.max(1,step*.32)} y={Math.min(y(c.open),y(c.close))} width={Math.max(2,step*.64)} height={Math.max(1,Math.abs(y(c.open)-y(c.close)))} fill={color}/></g>})}
 </svg>;
}
function LogReturnChart({returns}) {
 if(!returns?.length)return <p>No log returns loaded.</p>;
 const W=900,H=180,pad=28,max=Math.max(...returns.map(r=>Math.abs(r.value)),.0001),step=(W-2*pad)/returns.length,y0=H/2;
 return <svg className="history-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Actual daily logarithmic returns chart"><line x1={pad} x2={W-pad} y1={y0} y2={y0} stroke="#7992b2" strokeDasharray="4 4"/>{returns.map((r,i)=>{const h=(r.value/max)*(H/2-pad);return <rect key={r.date} x={pad+i*step} y={h>=0?y0-h:y0} width={Math.max(1,step*.7)} height={Math.max(1,Math.abs(h))} fill={r.value>=0?"#44d69a":"#ff637b"}/>})}<text x="3" y="15" fill="#9bb4d0" fontSize="11">{(max*100).toFixed(2)}%</text><text x="3" y={H-5} fill="#9bb4d0" fontSize="11">-{(max*100).toFixed(2)}%</text></svg>;
}


export {Icon,HorseSprite,Chart,CandlestickChart,LogReturnChart};
