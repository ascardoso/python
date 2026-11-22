const HARMONICS = 16;
const COLORS = ["#65d6c4","#78a9ff","#f5bd65","#d58cff","#ff8d9d","#8ed17d","#6ec9ed","#e6a66d",
                "#b6a0ff","#7bd5b4","#f08cae","#9bb8e8","#e2cf75","#8bd2d0","#d5a2ef","#a6c77b"];
const $ = id => document.getElementById(id);
const envCanvas = $("envelopeCanvas");
const envCtx = envCanvas.getContext("2d");
const waveCanvas = $("waveCanvas");
const waveCtx = waveCanvas.getContext("2d");
const spectrumCanvas = $("spectrumCanvas");
const spectrumCtx = spectrumCanvas.getContext("2d");

let curves = Array.from({length:HARMONICS}, (_,i) => defaultCurve(i));
let selected = 0;
let drawing = false;
let audioContext = null, master = null, analyser = null, activeNodes = [];
let noteStartedAt = 0, noteDuration = 3, playing = false;
let animationId = 0;

function defaultCurve(index) {
  // Higher partials begin more quietly and generally lose energy sooner.
  const peak = Math.max(.12, 0.82 / (1 + index * .16));
  const tail = Math.max(.04, peak * (0.78 - index * .025));
  return [{x:0,y:0},{x:.08,y:peak},{x:.22,y:tail},{x:1,y:tail}];
}
function resizeCanvas(canvas, ctx) {
  const rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width*dpr));
  canvas.height = Math.max(1, Math.round(rect.height*dpr));
  ctx.setTransform(dpr,0,0,dpr,0,0);
}
function dims(canvas) { const r=canvas.getBoundingClientRect(); return {w:r.width,h:r.height}; }
function renderEnvelope() {
  const {w,h}=dims(envCanvas), left=42, right=16, top=16, bottom=28;
  const pw=w-left-right, ph=h-top-bottom;
  envCtx.clearRect(0,0,w,h);
  envCtx.fillStyle="#0b1420"; envCtx.fillRect(0,0,w,h);
  envCtx.font="10px system-ui"; envCtx.textAlign="right"; envCtx.fillStyle="#70839a";
  for(let i=0;i<=4;i++) {
    const y=top+ph*i/4;
    envCtx.strokeStyle="#25364a"; envCtx.lineWidth=1; envCtx.beginPath(); envCtx.moveTo(left,y); envCtx.lineTo(w-right,y); envCtx.stroke();
    envCtx.fillText((1-i/4).toFixed(2),left-8,y+3);
  }
  for(let i=0;i<=6;i++) {
    const x=left+pw*i/6;
    envCtx.strokeStyle="#1d2c3e"; envCtx.beginPath(); envCtx.moveTo(x,top); envCtx.lineTo(x,h-bottom); envCtx.stroke();
    envCtx.textAlign="center"; envCtx.fillStyle="#70839a"; envCtx.fillText((noteDuration*i/6).toFixed(1)+"s",x,h-9);
  }
  if($("showAll").checked) curves.forEach((curve,i)=>{ if(i!==selected) drawCurve(curve,COLORS[i],1.4,.38,left,top,pw,ph,false); });
  drawCurve(curves[selected],COLORS[selected],2.8,1,left,top,pw,ph,true);
}
function drawCurve(points,color,width,alpha,left,top,pw,ph,handles) {
  envCtx.save(); envCtx.globalAlpha=alpha; envCtx.strokeStyle=color; envCtx.lineWidth=width; envCtx.lineJoin="round"; envCtx.lineCap="round";
  envCtx.beginPath();
  points.forEach((p,i)=>{const x=left+p.x*pw,y=top+(1-p.y)*ph; if(i===0)envCtx.moveTo(x,y);else envCtx.lineTo(x,y);});
  envCtx.stroke();
  if(handles) points.forEach(p=>{const x=left+p.x*pw,y=top+(1-p.y)*ph; envCtx.fillStyle=color; envCtx.beginPath(); envCtx.arc(x,y,3.2,0,Math.PI*2); envCtx.fill();});
  envCtx.restore();
}
function canvasPoint(e) {
  const r=envCanvas.getBoundingClientRect(), left=42,right=16,top=16,bottom=28;
  const x=Math.max(0,Math.min(1,(e.clientX-r.left-left)/(r.width-left-right)));
  const y=Math.max(0,Math.min(1,1-(e.clientY-r.top-top)/(r.height-top-bottom)));
  return {x,y};
}
function setCurvePoint(e) {
  const p=canvasPoint(e), arr=curves[selected];
  // Replace nearby points, otherwise add a point; endpoints remain anchored in time.
  let nearest=-1, distance=.025;
  arr.forEach((q,i)=>{const d=Math.abs(q.x-p.x);if(d<distance){distance=d;nearest=i;}});
  if(nearest>=0 && nearest!==0 && nearest!==arr.length-1) arr[nearest]=p;
  else if(p.x>.005 && p.x<.995) arr.push(p);
  arr.sort((a,b)=>a.x-b.x);
  // Keep a useful number of points while allowing detailed hand-drawn curves.
  if(arr.length>500) arr.splice(1,arr.length-2);
  renderEnvelope();
}
envCanvas.addEventListener("pointerdown",e=>{drawing=true;envCanvas.setPointerCapture(e.pointerId);setCurvePoint(e);});
envCanvas.addEventListener("pointermove",e=>{if(drawing)setCurvePoint(e);});
envCanvas.addEventListener("pointerup",()=>drawing=false);
envCanvas.addEventListener("pointercancel",()=>drawing=false);

function buildHarmonicButtons() {
  const host=$("harmonicButtons"); host.innerHTML="";
  for(let i=0;i<HARMONICS;i++) {
    const b=document.createElement("button"); b.className="harmonic-button"+(i===selected?" selected":"");
    b.textContent=`H${i+1}`; b.title=`${i+1} × fundamental`;
    b.addEventListener("click",()=>{selected=i;buildHarmonicButtons();renderEnvelope();});
    host.appendChild(b);
  }
}
function interpolate(points,x) {
  if(x<=points[0].x)return points[0].y;
  for(let i=1;i<points.length;i++) if(x<=points[i].x) {
    const a=points[i-1],b=points[i],t=(x-a.x)/(b.x-a.x||1);
    return a.y+(b.y-a.y)*t;
  }
  return points[points.length-1].y;
}
function makeCurveArray(points) {
  const values=new Float32Array(512);
  for(let i=0;i<values.length;i++) values[i]=interpolate(points,i/(values.length-1));
  return values;
}
async function ensureAudio() {
  if(!audioContext) {
    audioContext=new (window.AudioContext||window.webkitAudioContext)();
    master=audioContext.createGain(); master.gain.value=Number($("volume").value);
    analyser=audioContext.createAnalyser(); analyser.fftSize=4096; analyser.smoothingTimeConstant=.72;
    master.connect(analyser); analyser.connect(audioContext.destination);
  }
  if(audioContext.state==="suspended") await audioContext.resume();
}
function stopSound() {
  if(!audioContext)return;
  const now=audioContext.currentTime;
  activeNodes.forEach(({osc,gain})=>{try{gain.gain.cancelScheduledValues(now);gain.gain.setTargetAtTime(0,now,.015);osc.stop(now+.08);}catch{}});
  activeNodes=[]; playing=false; setStatus(false);
}
async function playSound() {
  await ensureAudio(); stopSound();
  const now=audioContext.currentTime, f0=Number($("fundamental").value);
  noteDuration=Number($("duration").value); noteStartedAt=now; playing=true; setStatus(true);
  for(let i=0;i<HARMONICS;i++) {
    const osc=audioContext.createOscillator(), gain=audioContext.createGain();
    osc.type="sine"; osc.frequency.value=f0*(i+1);
    gain.gain.setValueAtTime(0,now);
    gain.gain.setValueCurveAtTime(makeCurveArray(curves[i]),now,noteDuration);
    osc.connect(gain); gain.connect(master); osc.start(now); osc.stop(now+noteDuration+.03);
    activeNodes.push({osc,gain});
    osc.onended=()=>{osc.disconnect();gain.disconnect();};
  }
  window.setTimeout(()=>{if(playing && audioContext && audioContext.currentTime>=noteStartedAt+noteDuration){playing=false;activeNodes=[];setStatus(false);}},noteDuration*1000+100);
}
function setStatus(on) {
  $("statusDot").classList.toggle("playing",on);
  $("statusText").textContent=on?"Playing":"Ready";
}
function drawWave() {
  const {w,h}=dims(waveCanvas); waveCtx.clearRect(0,0,w,h); waveCtx.fillStyle="#0b1420";waveCtx.fillRect(0,0,w,h);
  waveCtx.strokeStyle="#26384c";waveCtx.beginPath();waveCtx.moveTo(0,h/2);waveCtx.lineTo(w,h/2);waveCtx.stroke();
  if(!analyser)return;
  const data=new Uint8Array(analyser.fftSize);analyser.getByteTimeDomainData(data);
  waveCtx.strokeStyle="#65d6c4";waveCtx.lineWidth=1.6;waveCtx.beginPath();
  for(let i=0;i<data.length;i++){const x=i/(data.length-1)*w,y=data[i]/255*h;if(i===0)waveCtx.moveTo(x,y);else waveCtx.lineTo(x,y);}
  waveCtx.stroke();
}
function drawSpectrum() {
  const {w,h}=dims(spectrumCanvas);spectrumCtx.clearRect(0,0,w,h);spectrumCtx.fillStyle="#0b1420";spectrumCtx.fillRect(0,0,w,h);
  if(!analyser)return;
  const data=new Uint8Array(analyser.frequencyBinCount);analyser.getByteFrequencyData(data);
  const nyquist=audioContext.sampleRate/2, maxHz=Math.min(8000,nyquist), bins=Math.floor(maxHz/nyquist*data.length);
  const barW=w/Math.max(1,bins);
  for(let i=1;i<bins;i++){const x=i*barW,barH=data[i]/255*(h-12);spectrumCtx.fillStyle="#78a9ff";spectrumCtx.fillRect(x,h-barH,Math.max(1,barW*.8),barH);}
  spectrumCtx.fillStyle="#70839a";spectrumCtx.font="10px system-ui";
  [0,1000,2000,4000,6000,8000].filter(v=>v<=maxHz).forEach(v=>{const x=v/maxHz*w;spectrumCtx.fillText(v>=1000?(v/1000)+"k":v,x+3,h-4);});
}
function animate() {drawWave();drawSpectrum();animationId=requestAnimationFrame(animate);}
function resizeAll(){[envCanvas,waveCanvas,spectrumCanvas].forEach(c=>resizeCanvas(c,c.getContext("2d")));renderEnvelope();}
function updateLabels() {
  $("fundamentalValue").textContent=$("fundamental").value+" Hz";
  $("durationValue").textContent=Number($("duration").value).toFixed(1)+" s";
  $("volumeValue").textContent=Math.round(Number($("volume").value)*100)+"%";
}
$("fundamental").addEventListener("input",updateLabels);
$("duration").addEventListener("input",()=>{updateLabels();noteDuration=Number($("duration").value);renderEnvelope();});
$("volume").addEventListener("input",()=>{updateLabels();if(master)master.gain.setTargetAtTime(Number($("volume").value),audioContext.currentTime,.02);});
$("playButton").addEventListener("click",playSound);
$("stopButton").addEventListener("click",stopSound);
$("resetButton").addEventListener("click",()=>{curves=Array.from({length:HARMONICS},(_,i)=>defaultCurve(i));renderEnvelope();});
$("flatButton").addEventListener("click",()=>{const y=curves[selected][Math.min(1,curves[selected].length-1)].y;curves[selected]=[{x:0,y},{x:1,y}];renderEnvelope();});
$("showAll").addEventListener("change",renderEnvelope);
window.addEventListener("resize",resizeAll);
updateLabels();buildHarmonicButtons();resizeAll();animate();
