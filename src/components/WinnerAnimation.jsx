import React from "react";
export default function WinnerAnimation({name,onPlayAgain,onSettings}){
 return <div className="winner-celebration"><div className="confetti">✦ ✧ ✦ ✧ ✦</div><div className="winner-cup">🏆</div><h1>{name} WINS!</h1><div className="winner-horse"><img src="/pixel/reference-horse-garch.png" alt="Winning pixel horse"/></div><p>Fantastic finish! The winning forecast crossed the line.</p><div><button onClick={onPlayAgain}>↻ PLAY AGAIN</button><button onClick={onSettings}>⚙ CHANGE SETTINGS</button></div></div>
}
