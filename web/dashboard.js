"use strict";
const byId=id=>document.getElementById(id);
const fileMode=location.protocol==="file:";
const root=document.documentElement;
let preferred;
try{preferred=localStorage.getItem("viewer-tone");}catch{}
const tone=new URLSearchParams(location.search).get("tone")||preferred;
root.dataset.tone=["dark","light"].includes(tone)?tone:matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light";
byId("guideTheme").value=root.dataset.tone;
byId("guideTheme").onchange=e=>{root.dataset.tone=e.target.value;try{localStorage.setItem("viewer-tone",e.target.value);}catch{}};

function makeMap(){
  const chapter=byId("map");
  const [stagesTable,routesTable]=chapter.querySelectorAll("table");
  const rows=t=>Array.from(t.tBodies[0].rows,row=>Array.from(row.cells,cell=>cell.textContent.trim()));
  const stages=new Map(rows(stagesTable).map(([name,tool,description])=>[name,{tool,description}]));
  const routes=rows(routesTable);
  const box=document.createElement("section");box.className="flowBox";
  box.innerHTML='<div class="flowHead"><h2>Data flow</h2><label>Workflow <select id="flowChoice"></select></label></div><ol class="flowNodes" aria-label="Processing stages"></ol><div class="flowFoot" aria-live="polite"><strong></strong><p></p><code></code></div>';
  for(const table of [stagesTable,routesTable]){table.previousElementSibling.hidden=true;table.hidden=true;}
  chapter.insertBefore(box,stagesTable);
  const picker=byId("flowChoice"),nodes=box.querySelector("ol"),foot=box.querySelector(".flowFoot");
  const note=document.createElement("p");note.className="flowNote";box.after(note);
  for(const [name] of routes)picker.add(new Option(name,name));
  function selectStage(name){
    const stage=stages.get(name),[tool,file]=stage.tool.split(" · ");
    for(const b of nodes.querySelectorAll("button"))b.setAttribute("aria-pressed",String(b.dataset.name===name));
    foot.querySelector("strong").textContent=name;
    foot.querySelector("p").textContent=stage.description;
    foot.querySelector("code").textContent=file||tool;
  }
  function showRoute(){
    const [,route,result]=routes[picker.selectedIndex],names=route.split(" → ");
    nodes.replaceChildren();
    for(const name of names){
      const li=document.createElement("li"),b=document.createElement("button"),small=document.createElement("small");
      b.type="button";b.dataset.name=name;b.textContent=name;small.textContent=stages.get(name).tool.split(" · ")[0];
      b.append(small);b.onclick=()=>selectStage(name);li.append(b);nodes.append(li);
    }
    note.textContent=result;selectStage(names.includes("XY query")?"XY query":names[0]);
  }
  picker.onchange=showRoute;showRoute();
  const actions=document.createElement("div");actions.className="jumpList";
  for(const [label,target] of [["First lap comparison","#start"],["Try the offline scatter","../examples/plugin-scatter.html"],["Embed in a viewer","#embed"]]){
    const a=document.createElement("a");a.textContent=label;a.href=target;actions.append(a);
  }
  note.after(actions);
}
makeMap();
byId("resources").append(byId("nativeExample").content.cloneNode(true));
const qt=byId("qt"),status=byId("qtStatus");
if(fileMode){qt.disabled=true;status.textContent="Open the dashboard with Start Data Viewer.cmd to launch Qt.";}
qt.onclick=async()=>{
  qt.disabled=true;status.textContent="Opening…";
  try{
    const session=await (await fetch("/api/session")).json();
    const response=await fetch("/api/qt-example",{method:"POST",headers:{"X-Viewer-Token":session.token}});
    const result=await response.json();status.textContent=result.message||result.error;
  }catch{status.textContent="The local service is unavailable. Reopen the dashboard from the launcher.";}
  finally{qt.disabled=false;}
};
function showChapter(moveFocus=false){
  const chapters=[...document.querySelectorAll(".manual article")];
  const current=chapters.find(c=>"#"+c.id===location.hash)||byId("map");
  for(const item of chapters)item.hidden=item!==current;
  for(const a of byId("chapters").querySelectorAll("a")){
    if(a.hash==="#"+current.id)a.setAttribute("aria-current","location");else a.removeAttribute("aria-current");
  }
  document.title=current.querySelector("h1").textContent+" · Data Viewer";
  if(moveFocus){byId("guideMain").focus({preventScroll:true});window.scrollTo(0,0);}
}
document.querySelector(".skip").addEventListener("click",event=>{
  event.preventDefault();
  byId("guideMain").focus();
});
showChapter();window.addEventListener("hashchange",()=>showChapter(true));
