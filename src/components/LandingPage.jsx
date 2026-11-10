import React from "react";
export default function LandingPage({onPlay,onTutorial,onLearn,onSettings}){
 return <section className="arcade-landing">
  <div className="landing-brand"><span>🏇</span><div><h1>THE FORECASTING<br/>HORserace</h1><p>Econometric Models in Action</p></div><span>🏆</span></div>
  <div className="landing-racetrack"><div className="pixel-city"></div><div className="track-lanes"><img className="landing-horse horse-a" src="/pixel/reference-horse-ols.png"/><img className="landing-horse horse-b" src="/pixel/reference-horse-arima.png"/><img className="landing-horse horse-c" src="/pixel/reference-horse-garch.png"/></div></div>
  <nav className="landing-actions"><button className="primary" onClick={onPlay}>▶ PLAY GAME</button><button onClick={onTutorial}>▣ TUTORIAL</button><button onClick={onLearn}>ⓘ LEARN MORE</button><button onClick={onSettings}>♫ SOUND SETTINGS</button></nav>
  <p className="landing-tagline">Train your models. Race the forecasts. Celebrate the winner.</p>
 </section>
}
