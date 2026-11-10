let ctx=null, master=null, musicNodes=[], musicTimer=null, enabled=true, volume=.22;
function ensure(){
 if(!ctx){const C=window.AudioContext||window.webkitAudioContext;if(!C)return;ctx=new C();master=ctx.createGain();master.gain.value=volume;master.connect(ctx.destination);}
 if(ctx.state==="suspended")ctx.resume();
 return ctx;
}
function tone(freq,duration=.12,type="square",gain=.12,when=0){
 const c=ensure();if(!c||!enabled)return;const osc=c.createOscillator(),g=c.createGain();osc.type=type;osc.frequency.setValueAtTime(freq,c.currentTime+when);g.gain.setValueAtTime(.0001,c.currentTime+when);g.gain.exponentialRampToValueAtTime(Math.max(.001,gain),c.currentTime+when+.015);g.gain.exponentialRampToValueAtTime(.0001,c.currentTime+when+duration);osc.connect(g);g.connect(master);osc.start(c.currentTime+when);osc.stop(c.currentTime+when+duration+.03);
}
export function setSoundEnabled(v){enabled=v;if(v)ensure();if(master)master.gain.setTargetAtTime(v?volume:0,ctx.currentTime,.04);}
export function setSoundVolume(v){volume=v;if(master&&enabled)master.gain.setTargetAtTime(volume,ctx.currentTime,.04);}
export function clickSound(){tone(640,.055,"square",.08);}
export function startSound(){[440,660,880].forEach((f,i)=>tone(f,.14,"square",.1,i*.09));}
export function hoofbeats(){for(let i=0;i<10;i++){tone(i%2?115:155,.07,"triangle",.12,i*.18);tone(75,.045,"sine",.09,i*.18+.07);}}
export function winnerFanfare(){[523,659,784,1047].forEach((f,i)=>tone(f,.42,"square",.14,i*.16));}
export function startMusic(){
 const c=ensure();if(!c||!enabled||musicTimer)return;
 const notes=[261.63,329.63,392,329.63,293.66,349.23,440,392];let index=0;
 musicTimer=window.setInterval(()=>{if(!enabled)return;const f=notes[index++%notes.length];tone(f,.24,"triangle",.035);tone(f/2,.28,"sine",.025,.04);},320);
}
export function stopMusic(){if(musicTimer){clearInterval(musicTimer);musicTimer=null;}}
