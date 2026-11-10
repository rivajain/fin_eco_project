import React from "react";
export default function SoundControls({enabled,onToggle,volume,onVolume}){
 return <div className="sound-controls"><button aria-label={enabled?"Mute audio":"Enable audio"} onClick={onToggle}>{enabled?"♫ SOUND ON":"🔇 SOUND OFF"}</button><input aria-label="Sound volume" type="range" min="0" max="1" step=".05" value={volume} onChange={e=>onVolume(+e.target.value)}/></div>
}
