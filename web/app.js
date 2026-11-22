"use strict";
const $ = id => document.getElementById(id);
const scatterButton=document.createElement("button");scatterButton.textContent="Scatter settings";scatterButton.className="scatterAction";scatterButton.hidden=true;
document.querySelector(".boardhead").append(scatterButton);
const scatterHost=new ScatterHost($("plot"),scatterButton,(state,fig)=>{
 const q=state.query, labels=scatterHost.labels;
 const text=labels[q.y]+" vs "+labels[q.x];
 $("boardTitle").textContent=text;
 const shown=fig.data.reduce((n,t)=>n+(t.ids?.length||0),0);
 const summary=fmt(fig.matched)+" matching samples · "+fmt(shown)+" displayed"+(q.gates.length?" · "+q.gates.length+" active gate"+(q.gates.length===1?"":"s"):"");
 if(log)$("logInfo").textContent=summary;
 else {$("source").textContent="Simulated data · "+summary; if(q.x!==S.scatterDefaults[view].x||q.y!==S.scatterDefaults[view].y||JSON.stringify(q.gates)!==JSON.stringify(S.scatterDefaults[view].gates))$("desc").textContent=text;else $("desc").textContent=S.catalog[view][2];}
});
function localScatter(){return !!log&&$("logPlot").value==="scatter";}
const ns = "http://www.w3.org/2000/svg";
const node = (tag, text) => { const el=document.createElement(tag); if(text!=null) el.textContent=text; return el; };
const glyphs={
 history:"M2 16h4l3-10 3 13 4-12 3 6h3",scatter:"M4 16h2m1-5h2m3 4h2m1-9h2m1 5h2",
 timing:"M3 17l5-3 5 2 8-10",outing:"M2 17l3-7 3 5 3-9 3 8 3-5 3 7",
 colour:"M3 8h18M3 12h12M3 16h7",hist:"M3 19v-5h3v5m2 0V8h3v11m2 0V4h3v15m2 0v-9h3v9",
 track:"M4 8l9-3 6 1 2 4-3 2-3-1-2 5-5 2-4-2 2-5z",
 report:"M4 5h16v14H4zM4 10h16M10 10v9",
 gauges:"M3 17a9 9 0 1 1 18 0M12 15l5-6",
 moon:"M20 15a9 9 0 0 1-11-11 9 9 0 1 0 11 11z",
 sun:"M12 3v2m0 14v2M3 12h2m14 0h2M6 6l1 1m10 10 1 1M6 18l1-1M17 7l1-1M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z"};
function icon(key){const svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox","0 0 24 24");svg.setAttribute("aria-hidden","true");const p=document.createElementNS(ns,"path");p.setAttribute("d",glyphs[key]||glyphs.report);svg.append(p);return svg;}
function familyIcon(key){return glyphs[key]?key:({Traces:"history",Scatter:"scatter",Distributions:"hist",Track:"track",Instruments:"gauges"})[S.catalog[key]?.[0]]||"report";}
let S,view="history",log=null,cursorData,lastSheet,version=0,cursorVersion=0,rangeTimer,openTimer;
const params=new URLSearchParams(location.search);
const prefs=(key,fallback)=>{try{return localStorage.getItem("viewer-"+key)||fallback;}catch{return fallback;}};
function save(key,v){try{localStorage.setItem("viewer-"+key,v);}catch{}}
function tone(type){return getComputedStyle(document.documentElement).getPropertyValue("--"+type).trim();}
function appearance(){
 const root=document.documentElement;
 root.dataset.style=$("style").value;save("style",root.dataset.style);save("tone",root.dataset.tone);
 const dark=root.dataset.tone==="dark";$("tone").replaceChildren(icon(dark?"sun":"moon"));$("tone").setAttribute("aria-label",dark?"Switch to light theme":"Switch to dark theme");
}
$("style").value=["apple","soft","clean"].includes(params.get("style"))?params.get("style"):prefs("style","apple");
const contentStyle=prefs("plot-style","fine");
$("plotStyle").value=["fine","bold","pattern"].includes(contentStyle)?contentStyle:"fine";
document.documentElement.dataset.tone=params.get("tone")==="dark"?"dark":params.get("tone")==="light"?"light":prefs("tone","light");
appearance();
const fmt=(n,dec=0)=>Number(n).toLocaleString("en-GB",{minimumFractionDigits:dec,maximumFractionDigits:dec});
async function api(path,options){const res=await fetch(path,options);const body=await res.json();if(!res.ok)throw Error(body.error||"Could not read the data.");return body;}
function warn(e){$("notice").textContent=e.message||String(e);}
function nav(){
 const groups=new Map();for(const [key,[group,name]] of Object.entries(S.catalog)){
  if(!groups.has(group)){const wrap=node("details"),options=node("optgroup");options.label=group;wrap.append(node("summary",group));$("tree").append(wrap);$("mobileView").append(options);groups.set(group,[wrap,options]);}
  const [wrap,options]=groups.get(group),b=node("button"),option=node("option",name);
  b.append(icon(familyIcon(key)),document.createTextNode(name));b.dataset.view=key;b.onclick=()=>choose(key);
  option.value=key;options.append(option);wrap.append(b);
 }
 for(const [i,lap] of S.laps.entries())for(const id of ["lap","ref"]){const opt=node("option",String(i+1).padStart(2,"0")+" · "+lap);opt.value=i;$(id).append(opt);}
 $("lap").value="1";$("ref").value="2";
}
function choose(key){
 if(!S.catalog[key])return;
 view=key;log=null;$("mobileView").value=key;
 for(const b of document.querySelectorAll("nav button")){if(b.dataset.view===key){b.setAttribute("aria-current","page");b.parentNode.open=true;}else b.removeAttribute("aria-current");}
 const url=new URL(location.href);url.searchParams.delete("source");url.searchParams.set("view",key);history.replaceState(null,"",url);
 redraw();
}
function formatAxis(){return $("time").getAttribute("aria-pressed")==="true"?"t":"d";}
function chartQuery(){return new URLSearchParams({format:"html",view,lap:$("lap").value,ref:$("ref").value,axis:formatAxis(),at:$("cursor").value});}
function gridTrack(){
 const xy=S.track,xx=xy.map(p=>p[0]),yy=xy.map(p=>p[1]),minX=Math.min(...xx),minY=Math.min(...yy);
 const k=Math.min(179/(Math.max(...xx)-minX),62/(Math.max(...yy)-minY));
 const coords=xy.map(([x,y])=>[10+(x-minX)*k,8+(y-minY)*k]);
 const svg=$("miniTrack");svg.replaceChildren();
 const shape=(tag,attr)=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attr))el.setAttribute(k,v);svg.append(el);};
 for(const [i,color] of [tone("accent"),tone("muted"),tone("ref")].entries()){
  const start=Math.floor(S.splits[i]*(coords.length-1)),end=Math.ceil(S.splits[i+1]*(coords.length-1));
  shape("polyline",{points:coords.slice(start,end+1).map(p=>p.join(",")).join(" "),fill:"none",stroke:color,"stroke-width":3.5,"stroke-linecap":"round","stroke-linejoin":"round"});
 }
 const [cx,cy]=coords[Math.round(Number($("cursor").value)/S.length*(coords.length-1))];
 shape("circle",{cx,cy,r:4.5,fill:tone("ink"),stroke:tone("panel"),"stroke-width":2});
}
function inspector(){
 if(!cursorData||log)return;
 const s=cursorData.sample,delta=s.t-cursorData.ref.t;
 $("marker").textContent=fmt(s.d)+" m";$("sector").textContent="Sector "+(s.d<S.length*.31?1:s.d<S.length*.66?2:3);
 $("inspectTime").textContent=fmt(s.t,3)+" s · "+(delta>=0?"+":"")+fmt(delta,3)+" s vs reference";
 $("values").replaceChildren();
 for(const [label,value,unit] of [["Speed",fmt(s.speed,1),"km/h"],["Throttle",fmt(s.throttle),"%"],["Brake",fmt(s.brake),"%"],["Engine",fmt(s.rpm),"rpm"],["Gear",fmt(s.gear),""]]){
  const box=node("div");box.className="value";box.append(node("small",label),node("strong",value),node("em",unit));$("values").append(box);
 }
 gridTrack();
}
function cursorX(){
 if(!cursorData||log||!["history","timing","colour","bits"].includes(view))return null;
 return ["colour","bits"].includes(view)||(view==="history"&&formatAxis()==="t")?cursorData.sample.t:cursorData.sample.d;
}
$("plot").addEventListener("dv-select",async event=>{
 if(scatterHost.element===event.target){
  if(!log&&Number.isFinite(event.detail.distance)){$("cursor").value=Math.round(event.detail.distance);queueCursor();}
  return;
 }
 if(cursorX()===null)return;
 const current=version;
 try{
  let x=event.detail.x;
  if(["colour","bits"].includes(view)||(view==="history"&&formatAxis()==="t")){
   const q=chartQuery();q.set("elapsed",x);const c=await api("/api/cursor?"+q);x=c.sample.d;
  }
  if(current===version){$("cursor").value=Math.round(x);queueCursor();}
 }catch(e){if(current===version)warn(e);}
});
$("plot").addEventListener("dv-range",event=>{
 if(!log||localScatter())return;
 const [start,end]=event.detail.range||[log.start,log.end];
 $("from").value=Math.max(log.start,start);$("to").value=Math.min(log.end,end);scheduleWindow();
});
async function draw(payload,serial){
 if(serial!==version)return;
 const kind=log?$("logPlot").value:view, host=$("plot"),data=payload.figure||payload.table||payload.gauge;
 let component=host.firstElementChild;
 if(component?.localName!=="dv-"+kind){
  component=document.createElement("dv-"+kind);host.replaceChildren(component);
 }
 host.hidden=false;
 const identity=[view,$("lap").value,$("ref").value,formatAxis()].join("|");
 const previousRange=!log&&component.dataset.identity===identity?component.range:null;
 component.dataset.identity=identity;
 component.setAttribute("label",$("heading").textContent);
 component.setAttribute("plot-style",$("plotStyle").value);
 if(lastSheet!==payload){
   if(scatterHost.button.hidden)component.data=data;
   else scatterHost.bind(component,data);
   if(previousRange)component.range=previousRange;
 }
 component.cursor=cursorX();
 component.schedule();lastSheet=payload;
}
async function redraw(){
 if(!S)return;const serial=++version;++cursorVersion;lastSheet=null;
 document.querySelector(".libraryEntry").href="/library?object="+encodeURIComponent(log?$("logPlot").value:view);
 scatterHost.prepare(null,null);
 document.querySelector("aside .session").hidden=!!log;$("localSession").hidden=!log;
 $("axisGroup").hidden=!!log||view!=="history";$("demoControls").hidden=!!log;$("logControls").hidden=!log;
 $("cursorBar").hidden=!!log;$("inspection").hidden=!!log;$("logInfo").hidden=!log;
 $("notice").textContent="Loading…";
 try{
 if(log){
  $("heading").textContent=log.name;$("family").textContent="Local log";$("desc").textContent=fmt(log.rows)+" samples · "+log.channels.length+" numeric channels";
  $("boardTitle").textContent=$("channel").value;$("plotIcon").replaceChildren(icon("history"));$("source").textContent="Local file on this computer";
  const start=Number($("from").value),end=Number($("to").value);
  if($("from").value===""||$("to").value===""||start>end)throw Error("Enter a start time less than or equal to the end time.");
  $("logChannel").hidden=localScatter();
  if(localScatter()){
   const labels=Object.fromEntries(["time_s",...log.channels].map(k=>[k,k==="time_s"?"Session time (s)":k]));
   const defaults={x:log.channels[0],y:log.channels[1]||"time_s",gates:[],colour:"",size:""};
   scatterHost.prepare("scatter",defaults,labels,{source:"local",start,end},log);
   const figure=await scatterHost.figure();if(serial!==version)return;
   await draw({figure},serial);$("notice").textContent="";return;
  }
  const q=new URLSearchParams({start,end,channel:$("channel").value,bins:Math.max(80,Math.floor($("board").clientWidth*.75))});
  const w=await api("/api/window?"+q);if(serial!==version)return;
  $("logInfo").textContent=fmt(w.rows)+" samples in view · "+fmt(w.x.length)+" points displayed · "+(w.reduced?"min/max envelope":"original samples");
  await draw({figure:{data:[{x:w.x,y:w.y,type:"scatter",mode:w.x.length===1?"markers":"lines",name:$("channel").value,line:{color:"#2464df",width:1.8},connectgaps:false}],
   layout:{xaxis:{title:{text:"Session time (s)"},range:start===end?undefined:[start,end]},yaxis:{title:{text:$("channel").value}}}}},serial);
 }else{
  const [group,name,desc]=S.catalog[view];$("heading").textContent=name;$("desc").textContent=desc;$("family").textContent=group;
  $("boardTitle").textContent=view==="history"?"Speed and pedals":({scatter:"G–G diagram",timing:"Delta to reference",fft:"Damper travel",mix:"Lambda by load"})[view]||name;
  $("source").textContent="Simulated data · "+S.rate+" Hz";$("plotIcon").replaceChildren(icon(familyIcon(view)));
  const q=chartQuery(), defaults=S.scatterDefaults?.[view];
  scatterHost.prepare(view,defaults,S.channels,{lap:$("lap").value,ref:$("ref").value});
  const [p,c]=await Promise.all([defaults?scatterHost.figure().then(figure=>({figure})):api("/api/chart?"+q),api("/api/cursor?"+q)]);
  if(serial!==version)return;cursorData=c;inspector();await draw(p,serial);
 }
 if(serial===version)$("notice").textContent="";
 }catch(e){if(serial===version){$("plot").hidden=true;warn(e);}}
}
function scheduleWindow(){clearTimeout(rangeTimer);rangeTimer=setTimeout(redraw,100);}
function queueCursor(){
 const serial=++cursorVersion;clearTimeout(rangeTimer);$("marker").textContent=fmt($("cursor").value)+" m";
 rangeTimer=setTimeout(async()=>{try{
  if(["gauges","status","pos","race","rainbow-compare","telemetry-position","telemetry-gps"].includes(view))return redraw();
  const c=await api("/api/cursor?"+chartQuery());if(serial!==cursorVersion||log)return;
  cursorData=c;inspector();
  if($("plot").firstElementChild)$("plot").firstElementChild.cursor=cursorX();
 }catch(e){warn(e);}},45);
}
function enterLog(info){
 if(log)scatterHost.saved.delete(log);
 $("logPlot").value="trace";
 const url=new URL(location.href);url.searchParams.set("source","local");history.replaceState(null,"",url);
 log=info;$("channel").replaceChildren(...info.channels.map(c=>node("option",c)));
 $("localName").textContent=info.name;$("localCount").textContent=fmt(info.rows)+" samples";
 $("from").value=info.start;$("to").value=info.end;
 for(const b of document.querySelectorAll("nav [aria-current]"))b.removeAttribute("aria-current");
 $("mobileView").selectedIndex=-1;if($("openDialog").open)$("openDialog").close();redraw();
}
async function watchOpen(){
 try{const state=await api("/api/state");if(state.state==="ready"){enterLog(state.info);return;}
 if(state.state==="error")throw Error(state.error);if(state.state==="cancelled"){$("openStatus").textContent="Selection cancelled.";return;}
 $("openStatus").textContent=state.state==="choosing"?"Choose a file in the Windows file picker…":state.progress>0?"Checking timestamps… "+fmt(state.progress*100)+"%":"Preparing the local file…";
 clearTimeout(openTimer);openTimer=setTimeout(watchOpen,400);
 }catch(e){$("openStatus").textContent=e.message;warn(e);}
}
async function openFile(path){try{await api("/api/open",{method:"POST",headers:{"Content-Type":"application/json","X-Viewer-Token":S.token},body:JSON.stringify({path})});watchOpen();}catch(e){$("openStatus").textContent=e.message;}}
$("open").onclick=()=>{$("openStatus").textContent="";$("openDialog").showModal();};$("closeDialog").onclick=()=>$("openDialog").close();
$("openForm").onsubmit=e=>{e.preventDefault();const path=$("path").value.trim().replace(/^"|"$/g,"");if(path)openFile(path);else $("openStatus").textContent="Enter a file path or choose Browse.";};
$("browse").onclick=()=>openFile("");$("channel").onchange=redraw;$("apply").onclick=redraw;$("all").onclick=()=>{$("from").value=log.start;$("to").value=log.end;redraw();};
$("logPlot").onchange=redraw;
$("demo").onclick=()=>choose(view);$("cursor").oninput=queueCursor;$("mobileView").onchange=e=>choose(e.target.value);
$("lap").onchange=redraw;$("ref").onchange=redraw;
for(const id of ["distance","time"])$(id).onclick=()=>{for(const other of ["distance","time"])$(other).setAttribute("aria-pressed",String(other===id));redraw();};
function restyle(){appearance();if(S)gridTrack();if(lastSheet)draw(lastSheet,version).catch(warn);}
$("style").onchange=restyle;$("tone").onclick=()=>{const root=document.documentElement;root.dataset.tone=root.dataset.tone==="dark"?"light":"dark";restyle();};
$("plotStyle").onchange=()=>{save("plot-style",$("plotStyle").value);if(lastSheet)draw(lastSheet,version).catch(warn);};
(async()=>{try{S=await api("/api/session");nav();choose(S.catalog[params.get("view")]?params.get("view"):"history");
 if(params.get("source")==="local"){const state=await api("/api/state");if(state.state==="ready")enterLog(state.info);else if(["loading","choosing"].includes(state.state)){if(!$("openDialog").open)$("openDialog").showModal();watchOpen();}else if(state.state==="error"){warn(Error(state.error));}}
 }catch(e){warn(e);}})();
