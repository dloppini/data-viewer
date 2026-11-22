/* The workspaces are ordinary local pages, so the browser owns back, forward and deep links. */
if(location.pathname==="/workbook"){
  window.addEventListener("pagehide",()=>{
    try{sessionStorage.setItem("viewer-workbook-query",location.search);}catch{}
  });
}
for (const nav of document.querySelectorAll(".workspaceTabs")) {
  const offline=location.protocol==="file:";
  for (const [name,path] of [["Dashboard","/"],["Workbook","/workbook"],["HTML library","/library"],["Demos","/demo"]]) {
    const link=document.createElement("a");
    link.textContent=name;
    if(offline&&path!=="/")continue;
    link.href=offline?"#map":path;
    if(!offline && path==="/workbook" && nav.dataset.current!==path){
      try{
        const query=sessionStorage.getItem("viewer-workbook-query");
        if(query?.startsWith("?"))link.href=path+query;
      }catch{}
    }
    if(nav.dataset.current===path)link.setAttribute("aria-current","page");
    nav.append(link);
  }
}
