"use strict";
const byId = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const frame = byId("frame"), content = byId("content"), object = byId("object"), tone = byId("toneChoice");
const instruments = {
  dial:["Speed dial","speed","km/h"], meter:["Throttle bar","throttle","%"],
  steering:["Steering wheel","steer","°"], gear:["Gear indicator","gear",""], rpm:["Engine speed","rpm"],
  lamp:["Brake light","brake",""]
};
let catalog, session, component, version=0;
const scatterHost=new ScatterHost(byId("preview"),byId("scatterSettings"),(state,fig)=>{
  const q=state.query,labels=scatterHost.labels;
  const preset=session.scatterDefaults[object.value];
  const title=q.x===preset.x&&q.y===preset.y?catalog[object.value][2]:labels[q.y]+" vs "+labels[q.x];
  byId("caption").textContent=title+" · "+fig.matched.toLocaleString("en-GB")+" matching samples"+
    (q.gates.length?" · "+q.gates.map(g=>labels[g.channel]+" "+g.op+" "+g.value).join(" and "):"");
  updateSnippet();
});
async function json(path) {
  const res=await fetch(path);if(!res.ok)throw new Error("Could not read the data.");return res.json();
}
function choice(select,value) {
  if([...select.options].some(o=>o.value===value))select.value=value;
}
function embedOptions(){
  const layout=component?.data?.layout;
  if(!layout?.dvAxes&&!layout?.dvMarker)return "";
  return JSON.stringify({axes:layout.dvAxes,marker:layout.dvMarker});
}
function updateSnippet(){
  if(!component)return;
  const tag=component.localName,options=embedOptions();
  const q=scatterHost.element===component?scatterHost.state.query:null;
  const escaped=text=>text.replaceAll("&","&amp;").replaceAll("'","&#39;").replaceAll("<","&lt;");
  const src=q?"/api/scatter?view="+encodeURIComponent(object.value):"./"+tag+".json";
  byId("snippet").textContent='<script defer src="telemetry-elements.js"></script>\n<'+tag+
    '\n  src="'+src+'"\n  frame="'+frame.value+'" plot-style="'+content.value+'" hide-tools'+
    (q?"\n  query='"+escaped(JSON.stringify(q))+"'":"")+
    (options?"\n  options='"+escaped(options)+"'":"")+'>\n</'+tag+'>';
  byId("embedHint").textContent=q?"This example reads the selected channels from the local viewer service. Download HTML for an offline snapshot.":"Serve the JS library and data JSON beside your page. Download HTML for an offline snapshot.";
}
function applyStyle() {
  const toneChanged=document.documentElement.dataset.tone!==tone.value;
  document.documentElement.dataset.tone=tone.value;
  if(component){
    if(toneChanged)component.schedule();
    component.setAttribute("frame",frame.value);
    component.setAttribute("plot-style",content.value);
    updateSnippet();
  }
  const url=new URL(location.href);
  for(const [key,value] of [["object",object.value],["frame",frame.value],["content",content.value],["tone",tone.value]])url.searchParams.set(key,value);
  history.replaceState(null,"",url);
}
async function sampleData(key) {
  if(key==="samples"||key==="trace"){
    const s=await json("/api/demo/samples");
    if(key==="trace")return {data:[{name:"Lap 02",x:s.t,y:s.speed,mode:"lines"}],layout:{xaxis:{title:{text:"Time (s)"}},yaxis:{title:{text:"Speed (km/h)"}}}};
    return {columns:["Time (s)","Speed (km/h)","Brake (%)"],selected:2,rows:s.t.slice(598,603).map((t,i)=>[t.toFixed(2),s.speed[598+i].toFixed(1),s.brake[598+i].toFixed(1)])};
  }
  const input=instruments[key], sheet=input?"gauges":key;
  const p=await json("/api/chart?format=html&view="+encodeURIComponent(sheet));
  if(input)return {label:input[0],value:p.gauge[input[1]],unit:input[2]};
  return p.figure||p.table||p.gauge;
}
async function show() {
  const serial=++version,key=object.value;
  const defaults=session.scatterDefaults?.[key];
  scatterHost.prepare(key,defaults,session.channels);
  component=null;byId("preview").replaceChildren();byId("export").disabled=byId("exportData").disabled=true;
  byId("title").textContent=catalog[key][1];byId("caption").textContent=catalog[key][2];
  byId("tagName").textContent="<dv-"+key+">";byId("status").textContent="Loading…";applyStyle();
  try {
    const data=defaults?await scatterHost.figure():await sampleData(key);if(serial!==version)return;
    component=document.createElement("dv-"+key);
    if(defaults)scatterHost.bind(component,data);else component.data=data;
    component.setAttribute("label",catalog[key][1]);applyStyle();
    byId("preview").replaceChildren(component);
    byId("status").textContent="";byId("export").disabled=byId("exportData").disabled=false;
  }catch(e){if(serial===version)byId("status").textContent=e.message;}
}
function download(filename,body,type){
  const a=document.createElement("a");a.download=filename;a.href=URL.createObjectURL(new Blob([body],{type}));
  a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}
async function downloadExample() {
  const current=component;if(!current)return;
  const label=current.getAttribute("label"), root=current.cloneNode(false);
  root.setAttribute("hide-tools","");
  const options=embedOptions();if(options)root.setAttribute("options",options);
  const inline=document.createElement("script");inline.type="application/json";
  inline.textContent=JSON.stringify(current.data).replaceAll("<","\\u003c");root.append(inline);
  const dark=tone.value==="dark";
  try {
    const response=await fetch("/telemetry-elements.js");if(!response.ok)throw new Error("Library unavailable.");
    const js=await response.text(),title=document.createElement("title");title.textContent=label;
    const heading=document.createElement("h1");heading.textContent=label;
    const example='<!doctype html>\n<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'+title.outerHTML+
      '<style>:root{color-scheme:'+(dark?"dark":"light")+'}body{max-width:1200px;margin:3vw auto;padding:16px;font:15px system-ui}h1{font-size:24px}</style>\n'+
      heading.outerHTML+"\n"+root.outerHTML+"\n<script>"+js.replace(/<\/script/gi,"<\\/script")+"</script></html>";
    download(root.localName+".html",example,"text/html");
  }catch(e){byId("status").textContent=e.message;}
}
async function start() {
  session=await json("/api/session");catalog=session.catalog;
  catalog.trace=["Traces","Single trace","Speed over the first 20 seconds of the simulated lap."];
  catalog.samples=["Report","Sample table","Five consecutive samples from the simulated lap."];
  for(const [key,[name]] of Object.entries(instruments))catalog[key]=["Instruments",name,"Value at the cursor on the simulated lap."];
  const groups=new Map();
  for(const [key,[family,name]] of Object.entries(catalog)){
    if(!groups.has(family)){const g=document.createElement("optgroup");g.label=family;groups.set(family,g);object.append(g);}
    groups.get(family).append(new Option(name,key));
  }
  choice(object,params.get("object")||"scatter");choice(frame,params.get("frame"));choice(content,params.get("content"));
  let preferred;try{preferred=localStorage.getItem("viewer-tone");}catch{}
  choice(tone,params.get("tone")||preferred||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light"));
  object.onchange=show;for(const select of [frame,content,tone])select.onchange=applyStyle;
  byId("exportData").onclick=()=>{if(component)download(component.localName+".json",JSON.stringify(component.data),"application/json");};
  byId("export").onclick=downloadExample;await show();
}
start().catch(e=>{byId("status").textContent=e.message;});
