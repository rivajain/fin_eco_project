import React, { useEffect, useState } from "react";
export default function CoachTutorial({step,steps,onNext,onBack,onSkip,ticker,modelName}){
 const current=steps[step-1];
 const [visibleText,setVisibleText]=useState("");
 useEffect(()=>{
  if(window.matchMedia("(prefers-reduced-motion: reduce)").matches){
   setVisibleText(current.text);
   return;
  }
  setVisibleText("");
  let character=0;
  const timer=window.setInterval(()=>{
   character+=1;
   setVisibleText(current.text.slice(0,character));
   if(character>=current.text.length)window.clearInterval(timer);
  },20);
  return()=>window.clearInterval(timer);
 },[current.text]);
 useEffect(()=>{
  const handleKeyDown=event=>{
   if(event.code!=="Space"||event.repeat||event.ctrlKey||event.metaKey||event.altKey)return;
   const target=event.target;
   if(target instanceof HTMLElement&&(target.isContentEditable||["INPUT","SELECT","TEXTAREA"].includes(target.tagName)))return;
   event.preventDefault();
   if(step===steps.length)onSkip();
   else onNext();
  };
  window.addEventListener("keydown",handleKeyDown);
  return()=>window.removeEventListener("keydown",handleKeyDown);
 },[onNext,onSkip,step,steps.length]);
 return <div className="coach-tutorial-overlay"><section className="coach-tutorial" role="dialog" aria-modal="true">
  <div className="tutorial-top"><button className="tutorial-back" onClick={onBack} disabled={step===1} aria-label="Go back">←</button><span>THE FORECASTING HORSERACE</span><span className="tutorial-step-count">{step} / {steps.length}</span></div>
  <div className="coach-world">
   <div className="coach-portrait">
    <img className="coach-character" src="/pixel/tutorial-coach.png" alt="Coach Pixel"/>
   </div>
   <div className="coach-speech"><span className="coach-speech-name">COACH PIXEL</span><h2>{current.title}</h2><p key={step} aria-label={current.text}>{visibleText}<span className="typing-cursor" aria-hidden="true">▌</span></p></div>
  </div>
  <div className="tutorial-dots">{steps.map((s,i)=><i key={i} className={i<step?"active":""}/>)}</div>
  <button className="text-skip" onClick={onSkip}>Skip tutorial</button>
 </section></div>
}
