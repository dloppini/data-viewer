/* Data Viewer HTML elements. Standalone classic script, no build step. */
(() => {
  "use strict";
  const format = new Intl.NumberFormat("en-GB", {maximumFractionDigits:3});
  const legendNumber = new Intl.NumberFormat("en-GB", {maximumFractionDigits:1});
  const number = n => Number.isFinite(n) ? format.format(n) : "—";
  const html = (tag, text) => {
    const item = document.createElement(tag);
    if (text != null) item.textContent = text;
    return item;
  };
  const charts = ["history","scatter","steer-throttle","timing","outing","colour","hist","susp","fft","mix","track","rainbow","pos","gps","race","trace",
    "scatter-density","scatter-colour","scatter-size","scatter-gate","scatter-average","scatter-linear","scatter-polynomial",
    "hist-colour","susp-zones","susp-four","frf","mix-trend","bits","sector-chart","channel-chart","rainbow-compare","telemetry-position","telemetry-gps"];
  const reports = ["sectors","stats","accel","status","samples"];
  const instruments = {
    dial:["speed","Speed","km/h"], meter:["throttle","Throttle","%"], steering:["steer","Steering","°"],
    gear:["gear","Gear",""], rpm:["rpm","Engine speed","rpm"], lamp:["brake","Brake light",""]
  };
  const inks = {
    fine:{width:1.3, radius:2.2, shape:"circle", fill:false, dash:[], grid:[1,4], gridAlpha:.58},
    bold:{width:2.7, radius:3, shape:"diamond", fill:true, dash:[], grid:[], gridAlpha:.36},
    pattern:{width:1.8, radius:2.6, shape:"square", fill:false, dash:[7,4], grid:[3,5], gridAlpha:.56}
  };
  const css = `
    :host{display:block;min-width:0;color:var(--ink,CanvasText);font:14px/1.4 var(--font,system-ui,sans-serif);font-variant-numeric:tabular-nums}
    :host([theme=dark]){color-scheme:dark}:host([theme=light]){color-scheme:light}
    *{box-sizing:border-box}.frame{background:var(--panel,Canvas);color:inherit;min-width:0;container-type:inline-size}
    :host([frame=apple]) .frame{border:1px solid var(--border,#a5afbc);border-radius:17px;box-shadow:0 2px 9px #151c2714;padding:8px}
    :host([frame=neumorphic]) .frame{border:1px solid color-mix(in srgb,currentColor 10%,transparent);border-radius:22px;background:color-mix(in srgb,var(--panel,Canvas) 92%,#86a096);box-shadow:5px 6px 13px #30413930,-4px -4px 12px #b2c4bb33;padding:8px}
    :host([frame=clean]) .frame{border:1px solid transparent;border-block-color:var(--border,#9aa6af);border-top:2px solid currentColor;padding:8px}
    .keybar,.detail{display:flex;align-items:center;flex-wrap:wrap;gap:4px 15px;padding:3px 10px;color:var(--muted,GrayText);font-size:12px}
    .keybar:empty,.detail:empty{display:none}.keybar span{display:inline-flex;align-items:center;gap:5px}.keybar i{display:inline-block;width:13px;height:3px}
    .detail{min-height:30px;justify-content:space-between}:host([external-controls]) .detail,:host([hide-tools]) .tools{display:none}.tools{display:inline-flex;gap:3px}
    button{font:inherit;color:inherit;background:transparent;border:1px solid var(--border,#acb6bf);border-radius:4px;min-height:26px;padding:2px 7px;cursor:pointer}
    :focus-visible{outline:2px solid currentColor;outline-offset:2px}
    canvas.plot{width:100%;height:var(--dv-height,310px);display:block;touch-action:pan-y;cursor:crosshair}
    .tableWrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:end;padding:7px 12px;border-block-end:1px solid var(--border,#aab3bd65)}th:first-child,td:first-child{text-align:start}
    thead th{color:var(--muted,GrayText);font-weight:600}tbody tr[aria-selected=true]{background:var(--select,#568bd322);font-weight:650}
    :host([plot-style=bold]) tbody tr:nth-child(even){background:color-mix(in srgb,currentColor 6%,transparent)}
    :host([plot-style=bold]) tbody td{font-weight:600}
    :host([plot-style=pattern]) td,:host([plot-style=pattern]) th{border-bottom-style:dashed}
    .instrument{display:grid;align-content:center;justify-items:center;gap:5px;padding:15px}.instrument small{color:var(--muted,GrayText)}.instrument strong{font-size:clamp(21px,5cqw,36px)}
    :host([plot-style=fine]) .instrument strong{font-weight:500}
    :host([plot-style=bold]) .instrument strong{font-weight:800}
    :host([plot-style=pattern]) .instrument strong{font-family:ui-monospace,monospace;border-bottom:2px dashed var(--muted,GrayText)}
    .instrument canvas{width:150px;height:84px;max-width:100%}.instrument meter{width:min(260px,90%);height:24px;accent-color:var(--series,#2863c9)}
    :host([plot-style=pattern]) meter::-webkit-meter-optimum-value{background:repeating-linear-gradient(120deg,#2661aa 0 4px,#80a0c2 4px 6px)}
    :host([plot-style=bold]) meter{height:36px}
    .lamp{display:inline-block;width:13px;height:13px;border:2px solid currentColor;margin-inline-end:8px}
    .gauges{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(140px,100%),1fr));gap:8px}
    output{overflow-wrap:anywhere}.error{padding:12px}
  `;
  const colors = ["#245acd","#b45428","#14806d","#965dbc"];
  function palette(host) {
    const s=getComputedStyle(host), token=(k,f)=>s.getPropertyValue("--"+k).trim()||f;
    const fg=s.color, dark=s.colorScheme==="dark" || (s.colorScheme!=="light" && matchMedia("(prefers-color-scheme:dark)").matches);
    return {fg, dark, text:token("muted",fg), grid:token("border",dark?"#7891a1":"#a7b4c1"),
      accent:token("series",dark?"#8bb6ff":colors[0]),ref:token("ref",dark?"#ffc094":colors[1]),
      green:dark?"#75d8c3":"#11725f", red:dark?"#ffa59c":"#a74545"};
  }
  function traceColor(trace,p,i) {
    const c=trace.line?.color || trace.marker?.color;
    if(typeof c!=="string") return i===0?p.accent:colors[i%colors.length];
    return ({"#2464df":p.accent,"#b75724":p.ref,"#008670":p.green,"#bd524d":p.red})[c]||c;
  }
  function limits(min,max) {
    if(!Number.isFinite(min)||!Number.isFinite(max))return [0,1];
    if(min===max){const pad=Math.abs(min)*.05||1;return [min-pad,max+pad];}
    return [min,max];
  }
  function extent(values) {
    let min=Infinity,max=-Infinity;
    for(const value of values)if(Number.isFinite(value)){min=Math.min(min,value);max=Math.max(max,value);}
    return limits(min,max);
  }
  function ticks([lo,hi],count) {
    const step=(hi-lo)/Math.max(2,count), power=10**Math.floor(Math.log10(step)), scaled=step/power;
    const nice=(scaled<=1?1:scaled<=2?2:scaled<=2.5?2.5:scaled<=5?5:10)*power;
    const out=[];
    for(let j=Math.ceil(lo/nice);j<=Math.floor(hi/nice)&&out.length<30;j++)out.push(j*nice);
    return out;
  }
  function axisRange(values,axis,setting) {
    if(setting?.range)return setting.range;
    if(setting?.scale!=="log")return (!setting&&axis?.range)||extent(values);
    let lo=Infinity,hi=0;
    for(const v of values)if(v>0&&Number.isFinite(v)){lo=Math.min(lo,v);hi=Math.max(hi,v);}
    if(!hi)return [1,10];
    return lo===hi?[lo/1.1,hi*1.1]:[lo,hi];
  }
  function axisTicks(range,count,log){
    if(!log)return ticks(range,count);
    const powers=range.map(Math.log10), step=Math.max(1,Math.ceil((powers[1]-powers[0])/count)), out=[];
    for(let i=Math.ceil(powers[0]);i<=powers[1];i+=step)out.push(10**i);
    return out.length>=2?out:ticks(range,count).filter(v=>v>0);
  }
  function checkAxis(axis) {
    if(!axis||!["linear","log"].includes(axis.scale))throw Error("Choose a linear or logarithmic scale.");
    if(axis.range!=null&&(!Array.isArray(axis.range)||axis.range.length!==2||!axis.range.every(Number.isFinite)||
      axis.range[0]>=axis.range[1]||(axis.scale==="log"&&axis.range[0]<=0)))throw Error("Axis limits must increase. Log limits must be positive.");
  }
  function checkDisplay({axes={},marker={},line={},bar={}}){
    if(Object.keys(axes).some(k=>k!=="x"&&k!=="y"))throw Error("Select the x or y axis.");
    for(const axis of Object.values(axes))checkAxis(axis);
    if(marker.shape&&!["auto","circle","diamond","square","cross"].includes(marker.shape))throw Error("Unknown marker shape.");
    if(marker.size!=null&&(!Number.isFinite(marker.size)||marker.size<.5||marker.size>12))throw Error("Marker size must be between 0.5 and 12.");
    if(marker.opacity!=null&&(!Number.isFinite(marker.opacity)||marker.opacity<=0||marker.opacity>1))throw Error("Opacity must be greater than zero and at most one.");
    if(line.width!=null&&(!Number.isFinite(line.width)||line.width<=0||line.width>16))throw Error("Line width must be greater than zero and at most 16 px.");
    if(line.dash!=null&&(!Array.isArray(line.dash)||!line.dash.every(v=>Number.isFinite(v)&&v>0)))throw Error("Use positive dash lengths or an empty array for a solid line.");
    if(bar.fill!=null&&!["solid","outline","pattern"].includes(bar.fill))throw Error("Use solid, outline or pattern for bar fill.");
    if(bar.widthScale!=null&&(!Number.isFinite(bar.widthScale)||bar.widthScale<=0||bar.widthScale>1))throw Error("Bar width scale must be greater than zero and at most one.");
  }
  function jsonObject(el,name){
    const raw=el.getAttribute(name);
    if(raw===null)return {};
    const value=JSON.parse(raw);
    if(!value||typeof value!=="object"||Array.isArray(value))throw Error(name+" must be a JSON object.");
    return value;
  }
  const compare={"<":(a,b)=>a<b,"<=":(a,b)=>a<=b,"==":(a,b)=>a===b,"!=":(a,b)=>a!==b,">=":(a,b)=>a>=b,">":(a,b)=>a>b};
  async function projectScatter(source,q,signal){
    const {channels,labels={},ids,timeChannel,distanceChannel}=source;
    const column=name=>{
      if(typeof name!=="string"||!Object.hasOwn(channels,name)||!Array.isArray(channels[name]))throw Error("Unknown scatter channel: "+name);
      return channels[name];
    };
    const x=column(q.x),y=column(q.y),colour=q.colour?column(q.colour):null,size=q.size?column(q.size):null;
    const time=timeChannel?column(timeChannel):null,distance=distanceChannel?column(distanceChannel):null;
    const gates=q.gates??[];
    if(!Array.isArray(gates)||gates.length>12)throw Error("Use up to 12 gates.");
    const tests=gates.map(g=>{
      if(!g||!Object.hasOwn(compare,g.op)||!Number.isFinite(g.value))throw Error("Each gate needs a comparison and a finite threshold.");
      return {values:column(g.channel),test:compare[g.op],value:g.value};
    });
    if([y,colour,size,time,distance,ids,...tests.map(g=>g.values)].some(a=>a!=null&&(!Array.isArray(a)||a.length!==x.length)))throw Error("Channel and ID lengths must match.");
    // Seeded reservoir sampling bounds browser work after the original rows have been gated.
    const rows=[];let matched=0,seed=1,maxSize=0,lastYield=performance.now();
    for(let i=0;i<x.length;i++){
      if(i%8192===0&&performance.now()-lastYield>8){
        if(globalThis.scheduler?.yield)await scheduler.yield();else await new Promise(resolve=>setTimeout(resolve,0));
        if(signal.aborted)return;
        lastYield=performance.now();
      }
      if(!Number.isFinite(x[i])||!Number.isFinite(y[i])||(colour&&!Number.isFinite(colour[i]))||(size&&!Number.isFinite(size[i])))continue;
      if(!tests.every(g=>Number.isFinite(g.values[i])&&g.test(g.values[i],g.value)))continue;
      matched++;
      if(size)maxSize=Math.max(maxSize,Math.abs(size[i]));
      if(rows.length<3200){rows.push(i);continue;}
      seed=(Math.imul(seed,1664525)+1013904223)>>>0;
      const slot=Math.floor((seed/4294967296)*matched);if(slot<rows.length)rows[slot]=i;
    }
    rows.sort((a,b)=>a-b);
    const take=values=>rows.map(i=>values[i]), label=k=>String(labels[k]??k);
    const meta={source:source.source??"inline"};
    if(time)meta.time=take(time);if(distance)meta.distance=take(distance);
    const marker={};
    if(colour){marker.color=take(colour);marker.colorbar={title:{text:label(q.colour)}};}
    const trace={x:take(x),y:take(y),ids:ids?take(ids):rows,meta,marker,mode:"markers",name:source.name??""};
    if(size){
      trace.customdata=take(size);meta.pick=label(q.size);
      marker.size=trace.customdata.map(v=>Math.sqrt(9+160*Math.abs(v)/(maxSize||1)));
    }
    return {data:[trace],matched,layout:{xaxis:{title:{text:label(q.x)}},yaxis:{title:{text:label(q.y)}}}};
  }
  function marker(ctx,shape,x,y,r,fill) {
    ctx.beginPath();
    if(shape==="cross"){ctx.moveTo(x-r,y);ctx.lineTo(x+r,y);ctx.moveTo(x,y-r);ctx.lineTo(x,y+r);ctx.stroke();return;}
    if(shape==="square")ctx.rect(x-r,y-r,r*2,r*2);
    else if(shape==="diamond"){ctx.moveTo(x,y-r*1.3);ctx.lineTo(x+r,y);ctx.lineTo(x,y+r*1.3);ctx.lineTo(x-r,y);ctx.closePath();}
    else ctx.arc(x,y,r,0,Math.PI*2);
    if(fill)ctx.fill();else ctx.stroke();
  }
  function canvasContext(canvas,w,h) {
    const ratio=window.devicePixelRatio||1;
    const pw=Math.round(w*ratio),ph=Math.round(h*ratio);
    if(canvas.width!==pw||canvas.height!==ph){canvas.width=pw;canvas.height=ph;}
    const ctx=canvas.getContext("2d");
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);return ctx;
  }
  function ramp(value,[lo,hi],scale,dark=false) {
    const t=Math.max(0,Math.min(1,(value-lo)/(hi-lo)));
    const stops=scale||[[0,"#41399b"],[.5,"#188b91"],[1,"#ca512c"]];
    let k=1;while(k<stops.length-1&&stops[k][0]<t)k++;
    const [a,ca]=stops[k-1],[b,cb]=stops[k],f=(t-a)/(b-a||1);
    const rgb=[1,3,5].map(i=>{
      const v=parseInt(ca.slice(i,i+2),16)*(1-f)+parseInt(cb.slice(i,i+2),16)*f;
      return Math.round(dark?v*.8+51:v);
    });
    return "rgb("+rgb.join(",")+")";
  }
  function stripePattern(ctx,color) {
    const tile=document.createElement("canvas");tile.width=tile.height=8;
    const pen=tile.getContext("2d");pen.strokeStyle=color;pen.lineWidth=1.6;
    pen.beginPath();pen.moveTo(-2,2);pen.lineTo(2,-2);pen.moveTo(0,8);pen.lineTo(8,0);pen.moveTo(6,10);pen.lineTo(10,6);pen.stroke();
    return ctx.createPattern(tile,"repeat");
  }
  class TelemetryElement extends HTMLElement {
    static observedAttributes=["frame","plot-style","theme","marker","label","static","src","options","query"];
    constructor(){
      super();this.attachShadow({mode:"open"});
      const style=html("style",css);this.frame=html("div");this.frame.className="frame";this.shadowRoot.append(style,this.frame);
      this.frame.oncontextmenu=e=>{if(charts.includes(this.kind))this.contextRequest(e,e.clientX,e.clientY);};
      this.frame.onkeydown=e=>{
        if(charts.includes(this.kind)&&(e.key==="ContextMenu"||(e.shiftKey&&e.key==="F10"))){
          const b=e.target.getBoundingClientRect();this.contextRequest(e,b.left+16,b.top+16);
        }
      };
      this.watch=new ResizeObserver(()=>{
        if(this.canvas&&(this.canvas.clientWidth!==this.drawWidth||this.canvas.clientHeight!==this.drawHeight))this.schedule();
      });
      this.scheme=matchMedia("(prefers-color-scheme: dark)");this.themeChange=()=>this.schedule();
    }
    connectedCallback(){
      this.scheme.addEventListener("change",this.themeChange);
      if(Object.hasOwn(this,"data")){const assigned=this.data;delete this.data;this.data=assigned;}
      if(this.ownerDocument.readyState==="loading"){
        this.onParsed=()=>{if(!this.hasAttribute("src")&&this.localSource===undefined){this.sourceKey=undefined;this.queueInputs();}};
        this.ownerDocument.addEventListener("DOMContentLoaded",this.onParsed,{once:true});
      }
      if(charts.includes(this.kind)){this.watch.observe(this);if(this.canvas)this.watch.observe(this.canvas);}
      this.queueInputs();
      this.schedule();
    }
    disconnectedCallback(){
      this.scheme.removeEventListener("change",this.themeChange);
      if(this.onParsed)this.ownerDocument.removeEventListener("DOMContentLoaded",this.onParsed);
      if(this.loading){this.cancelRead();this.sourceKey=undefined;}
      this.watch.disconnect();cancelAnimationFrame(this.pending);this.pending=0;
    }
    attributeChangedCallback(name,oldValue,newValue){
      if(oldValue===newValue)return;
      if(["src","options","query"].includes(name))this.queueInputs();
      else if(name!=="frame")this.schedule();
    }
    get kind(){return this.localName.slice(3);}
    get data(){return this._data;}
    set data(value){
      if(!this.hasAttribute("src")&&this.localSource!==value){this.selected=null;this.range=null;}
      this.localSource=value;
      if(this.hasAttribute("src"))return;
      this.cancelRead();
      this.sourceKey=undefined;this.inputError=null;
      if(value?.channels||this.hasAttribute("query"))this.queueInputs();
      else {this.replaceData(value);this.sourceKey=JSON.stringify(null);}
    }
    replaceData(value){this._data=value;this.selected=null;this.range=null;this.schedule();}
    get axes(){const base=this.data?.layout?.dvAxes;return this.display?.axes?{...base,...this.display.axes}:base??{};}
    get markerStyle(){const base=this.data?.layout?.dvMarker;return this.display?.marker?{...base,...this.display.marker}:base??{};}
    queueInputs(){
      if(!this.isConnected||this.inputPending)return;
      this.inputPending=true;
      queueMicrotask(()=>{this.inputPending=false;if(this.isConnected)this.syncInputs();});
    }
    cancelRead(){this.loading?.abort();this.loading=null;this.removeAttribute("aria-busy");}
    async syncInputs(){
      let controller,checkingDisplay=true;
      try{
        const raw=this.getAttribute("options");
        if(raw!==this.optionsText){
          const next=jsonObject(this,"options");
          if(Object.keys(next).some(k=>!["axes","marker","line","bar"].includes(k)))throw Error("Use axes, marker, line or bar in options.");
          for(const v of Object.values(next))if(!v||typeof v!=="object"||Array.isArray(v))throw Error("Plot options must be objects.");
          checkDisplay(next);
          this.optionsText=raw;
          if(JSON.stringify(this.display??{})!==JSON.stringify(next)){
            const x=this.axes.x;this.display=next;
            if(JSON.stringify(x)!==JSON.stringify(this.axes.x))this.range=null;
            this.checkSelection();this.schedule();
          }
        }
        checkingDisplay=false;
        const src=this.getAttribute("src"),hasQuery=this.hasAttribute("query"),query=hasQuery?jsonObject(this,"query"):null;
        const url=src?new URL(src,this.baseURI):null;
        if(url&&hasQuery)url.searchParams.set("query",JSON.stringify(query));
        const key=url?.href??JSON.stringify(query);
        if(key===this.sourceKey){
          if(this.inputError){this.inputError=null;this.schedule();}
          return;
        }
        const wasRemote=this.remote;
        this.cancelRead();this.sourceKey=key;this.remote=!!url;this.inputError=null;
        let value;
        if(url){
          controller=new AbortController();this.loading=controller;this.setAttribute("aria-busy","true");this.schedule();
          const response=await fetch(url,{signal:controller.signal});
          if(!response.ok)throw Error("Data source returned HTTP "+response.status+".");
          value=await response.json();if(controller.signal.aborted)return;
          if(charts.includes(this.kind))value=value?.figure??value;
          else if(reports.includes(this.kind))value=value?.table??value;
          else if(value?.gauge)value=this.kind==="gauges"?value.gauge:{value:value.gauge[instruments[this.kind][0]]};
        }else{
          if(this.localSource===undefined){
            const input=this.querySelector('script[type="application/json"]');
            if(input?.textContent.trim())this.localSource=JSON.parse(input.textContent);
          }
          value=this.localSource;
          if(value===undefined){
            if(wasRemote)this.replaceData(undefined);
            return;
          }
          if(value?.channels){
            if(!["scatter","steer-throttle"].includes(this.kind))throw Error("Named inline channels require an XY scatter element.");
            controller=new AbortController();this.loading=controller;this.setAttribute("aria-busy","true");
            value=await projectScatter(value,query??{},controller.signal);
            if(controller.signal.aborted)return;
          }else if(hasQuery)throw Error("Use named inline channels or a data service for a query.");
        }
        if(charts.includes(this.kind)){
          if(!Array.isArray(value?.data)||value.data.some(t=>!Array.isArray(t?.x)||!(Array.isArray(t.y)||Array.isArray(t.z))))throw Error("Expected a figure with numeric series.");
          if(url||this.localSource?.channels)this.updatePlot({figure:value},false);
          else if(value!==this.data)this.replaceData(value);
        }else if(!value||typeof value!=="object")throw Error("Expected component data.");
        else if(value!==this.data)this.replaceData(value);
        if(controller===this.loading){this.loading=null;this.removeAttribute("aria-busy");}
        this.dispatchEvent(new CustomEvent("dv-load",{bubbles:true,composed:true,detail:{matched:value?.matched}}));
      }catch(err){
        if(controller?.signal.aborted)return;
        if(!checkingDisplay||this.loading)this.sourceKey=undefined;
        this.cancelRead();this.inputError=err.message;this.schedule();
        this.dispatchEvent(new CustomEvent("dv-error",{bubbles:true,composed:true,detail:{message:err.message}}));
      }
    }
    reload(){this.sourceKey=undefined;this.queueInputs();}
    setAxes(axes){this.updatePlot({axes});}
    updatePlot({figure,axes,marker}={},inheritDisplay=true){
      const next=figure??this.data;
      if(!next||!Array.isArray(next.data))throw Error("A figure with data series is required.");
      const old=this.data?.layout||{}, layout={...next.layout};
      const base=inheritDisplay?old:{};
      const nextAxes={...base.dvAxes,...layout.dvAxes,...axes}, nextMarker={...base.dvMarker,...layout.dvMarker,...marker};
      checkDisplay({axes:nextAxes,marker:nextMarker});
      if(!figure&&JSON.stringify(nextAxes)===JSON.stringify(old.dvAxes||{})&&JSON.stringify(nextMarker)===JSON.stringify(old.dvMarker||{}))return;
      if(JSON.stringify(nextAxes.x)!==JSON.stringify(old.dvAxes?.x)||figure&&layout.xaxis?.title?.text!==old.xaxis?.title?.text)this.range=null;
      if(figure&&this.selected){
        const {series,index}=this.selected, prior=this.data.data[series], id=prior?.ids?.[index];
        const s=id==null?-1:next.data.findIndex(t=>t.meta?.source===prior.meta?.source&&t.ids?.includes(id));
        this.selected=s<0?null:{series:s,index:next.data[s].ids.indexOf(id)};
      }
      this._data={...next,layout:{...layout,dvAxes:nextAxes,dvMarker:nextMarker}};
      this.checkSelection();this.schedule();
    }
    checkSelection(){
      if(!this.selected)return;
      const {series,index}=this.selected,t=this.data?.data?.[series],axes=this.axes;
      if(!t||(axes.x?.scale==="log"&&!(t.x[index]>0))||(axes.y?.scale==="log"&&!(t.y?.[index]>0)))this.selected=null;
    }
    set cursor(value){if(this._cursor!==value){this._cursor=value;this.schedule();}}
    get cursor(){return this._cursor;}
    set cursors(value){this._cursors=value;this.schedule();}
    get cursors(){return this._cursors;}
    schedule(selectionOnly=false){
      if(!selectionOnly)this.fullDraw=true;
      if(!this.isConnected||this.pending)return;
      this.pending=requestAnimationFrame(()=>{
        this.pending=0;const full=this.fullDraw;this.fullDraw=false;
        if(!full&&this.canvas&&this.layers){this.paintPick();return;}
        this.render();
      });
    }
    render(){
      const theme=this.getAttribute("plot-style")||"fine";
      this.pen=Object.hasOwn(inks,theme)?inks[theme]:inks.fine;this.colors=palette(this);
      if(this.inputError){this.message(this.inputError);return;}
      if(this.loading){if(!this.data)this.message("Loading…");return;}
      const shape=this.markerStyle.shape;
      this.shape=(shape&&shape!=="auto"?shape:null)||this.getAttribute("marker")||this.pen.shape;
      if(!this.data){this.message("No data");return;}
      if(charts.includes(this.kind))this.chart();
      else if(reports.includes(this.kind))this.table();
      else this.instrument();
    }
    message(text){
      if(this.canvas)this.watch.unobserve(this.canvas);
      const p=html("p",text);p.className="error";p.setAttribute("role","status");
      if(charts.includes(this.kind)&&!this.hasAttribute("static"))p.tabIndex=0;
      this.frame.replaceChildren(p);this.canvas=null;this.layers=null;this.legendSignature=null;
    }
    chart(){
      const traces=this.data.data;
      if(!Array.isArray(traces)||!traces.some(t=>Array.isArray(t.x)&&t.x.length)){this.message("No samples");return;}
      const {x,y}=this.axes;
      if((x?.scale==="log"||y?.scale==="log")&&!traces.some(t=>t.x.some((v,i)=>(x?.scale!=="log"||v>0)&&(y?.scale!=="log"||t.y?.[i]>0)))){
        this.message("No samples with positive values on the logarithmic axes.");return;
      }
      if(!this.canvas){
        this.keys=html("div");this.keys.className="keybar";
        this.canvas=html("canvas");this.canvas.className="plot";this.canvas.setAttribute("role","img");
        this.readout=html("output");this.bar=html("div");this.bar.className="detail";
        this.tools=html("span");this.tools.className="tools";
        for(const [label,description,action] of [["−","Zoom out",()=>this.zoom(2)],["+","Zoom in",()=>this.zoom(.5)],["↺","Reset zoom",()=>this.changeRange(null)]]){
          const b=html("button",label);b.type="button";b.title=description;b.setAttribute("aria-label",description);b.onclick=action;this.tools.append(b);
        }
        this.bar.append(this.readout,this.tools);this.frame.replaceChildren(this.keys,this.canvas,this.bar);this.wire();this.watch.observe(this.canvas);
      }
      const still=this.hasAttribute("static");
      this.canvas.tabIndex=still?-1:0;this.tools.hidden=still;this.tools.style.display=still?"none":"";
      this.bar.style.display=still?"none":"";
      this.canvas.setAttribute("aria-label",(this.getAttribute("label")||this.kind)+(still?"":". Use the arrow keys to select a sample. Drag to zoom. Hold Shift and drag to pan."));
      this.drawChart(traces);
    }
    drawChart(traces){
      const c=this.canvas,w=c.clientWidth,h=c.clientHeight;this.drawWidth=w;this.drawHeight=h;if(w<40||h<40)return;
      const ctx=canvasContext(c,w,h), layout=this.data.layout||{},p=this.colors;
      const layers=traces.map((t,i)=>({t,i,axis:t.yaxis||"y",heat:t.type==="heatmap"||(this.kind==="colour"&&!!t.z),color:traceColor(t,p,i)}));
      const axisIds=[...new Set(layers.map(s=>s.axis))], map=layout.yaxis?.scaleanchor==="x"||["track","rainbow","pos","gps","race"].includes(this.kind);
      const sideBySide=axisIds.length===2 && layout.xaxis?.domain?.[1]<=layout.xaxis2?.domain?.[0];
      const axes=layout.xaxis?.visible??(!map||this.kind==="gps");
      const points=layers.flatMap(s=>s.t.x.filter(Number.isFinite));
      for(const {t} of layers.filter(s=>this.isBar(s.t)&&s.t.x.length)){
        const half=Number.isFinite(t.width)?t.width/2:Math.abs((t.x[1]??t.x[0]+1)-t.x[0])*.43;
        const [lo,hi]=extent(t.x);points.push(lo-half,hi+half);
      }
      const settings=this.axes, logX=settings.x?.scale==="log",logY=settings.y?.scale==="log";
      this.full=axisRange(points,layout.xaxis,settings.x);
      const xr=this.range||this.full;
      const ctxFont=getComputedStyle(this).fontFamily;
      ctx.font="11px "+ctxFont;ctx.lineWidth=1;
      this.geometries=[];
      const names=[], keyStrings=[];
      for(const s of layers){
        const t=s.t,values=s.heat?t.z?.[0]:Array.isArray(t.marker?.color)?t.marker.color:null;
        if(values){s.values=values;s.limits=Number.isFinite(t.marker?.cmin)&&Number.isFinite(t.marker?.cmax)?limits(t.marker.cmin,t.marker.cmax):extent(values);}
        let name=t.name;
        if(sideBySide&&s.values){if(t.marker.showscale===false)continue;name=t.marker.colorbar?.title?.text==="km/h"?"Speed":"";}
        if(s.values){const unit=(t.colorbar||t.marker?.colorbar)?.title?.text||"";name=(name?name+" · ":"")+s.limits.map(v=>legendNumber.format(v)).join("–")+" "+unit;}
        if(name){names.push([name,s]);keyStrings.push([name,s.color,!!s.values,p.dark,this.shape,t.line?.dash,this.getAttribute("plot-style")]);}
      }
      const signature=JSON.stringify(keyStrings);
      if(signature!==this.legendSignature){
        this.legendSignature=signature;this.keys.replaceChildren();
        for(const [name,s] of names){
          const key=html("span"), sw=html("i");sw.style.background=s.color;
          if(s.values){
            const scale=s.t.colorscale||s.t.marker?.colorscale;
            sw.style.width="36px";sw.style.height="4px";
            sw.style.background="linear-gradient(90deg,"+[0,.25,.5,.75,1].map(v=>ramp(v,[0,1],scale,p.dark)).join(",")+")";
          }
          if(s.t.line?.dash==="dot")sw.style.background="repeating-linear-gradient(to right,"+s.color+" 0 3px,transparent 3px 5px)";
          key.append(sw,document.createTextNode(name));this.keys.append(key);
        }
      }
      const bottom=axes?39:8,top=axes?9:8;
      const gap=18, available=h-top-bottom-(sideBySide?0:gap*(axisIds.length-1));
      const ranges=axisIds.map(id=>{
        const axis=layout["yaxis"+id.slice(1)]||{}, related=layers.filter(s=>s.axis===id);
        const ys=related.flatMap(s=>s.heat?[0,1]:s.t.y||[]);
        if(related.some(s=>this.isBar(s.t)))ys.push(0);
        return axisRange(ys,axis,settings.y);
      });
      const outerLeft=axes?Math.ceil(Math.max(19,...ranges.flatMap(r=>ticks(r,5).map(v=>ctx.measureText(number(v)).width))))+12:8;
      const outerRight=w-10;
      let nextTop=top;
      axisIds.forEach((id,j)=>{
        const axis=layout["yaxis"+id.slice(1)]||{},yTitle=axis.title?.text||"",heat=layers.some(s=>s.axis===id&&s.heat);
        const xAxis=layout["xaxis"+id.slice(1)]||layout.xaxis||{};
        const domain=sideBySide?xAxis.domain:[0,1];
        const left=outerLeft+(outerRight-outerLeft)*domain[0],right=outerLeft+(outerRight-outerLeft)*domain[1];
        const share=sideBySide?1:axisIds.length===2?(j===0?.65:.35):1/axisIds.length;
        const y1=nextTop+((axes&&yTitle)||sideBySide?13:0),y2=nextTop+available*share;
        if(!sideBySide)nextTop=y2+gap;
        const box={l:left,r:right,t:y1,b:y2};
        let [xl,xh]=xr,[yl,yh]=ranges[j];
        if(map&&!logX&&!logY){
          const fit=Math.max((this.full[1]-this.full[0])/(right-left),(yh-yl)/(y2-y1))*1.04;
          const unit=this.range ? fit*(xh-xl)/(this.full[1]-this.full[0]) : fit;
          const xm=(xl+xh)/2,ym=(yl+yh)/2;
          xl=xm-unit*(right-left)/2;xh=xm+unit*(right-left)/2;
          yl=ym-unit*(y2-y1)/2;yh=ym+unit*(y2-y1)/2;
        }
        const fx=logX?Math.log10:v=>v, fy=logY?Math.log10:v=>v;
        const lx=fx(xl),dx=fx(xh)-lx,ly=fy(yl),dy=fy(yh)-ly;
        const X=x=>left+(fx(x)-lx)/dx*(right-left),Y=y=>y2-(fy(y)-ly)/dy*(y2-y1);
        const fromFraction=f=>logX?10**(lx+f*dx):xl+f*dx;
        const g={id,box,X,Y,xl,xh,yl,yh,heat,fromFraction};this.geometries.push(g);
        if(sideBySide){ctx.fillStyle=p.text;ctx.textAlign="left";ctx.fillText(layers.find(s=>s.axis===id)?.t.name||"",left,y1-4);}
        if(axes){
          ctx.font="11px "+ctxFont;ctx.fillStyle=p.text;ctx.textAlign="left";
          if(yTitle)ctx.fillText(yTitle,left,y1-4,Math.max(20,right-left));
          const axisLine=(x,y,xx,yy)=>{ctx.save();ctx.globalAlpha=this.pen.gridAlpha;ctx.strokeStyle=p.grid;ctx.setLineDash(this.pen.grid);ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(xx,yy);ctx.stroke();ctx.restore();};
          for(const v of axis.tickvals||axisTicks([yl,yh],Math.max(2,Math.floor((y2-y1)/44)),logY)){
            if(heat)break;
            const y=Y(v);axisLine(left,y,right,y);ctx.textAlign="right";ctx.fillText(number(v),left-6,y+3);
          }
          const tickList=xAxis.tickvals||axisTicks([xl,xh],Math.max(2,Math.floor((right-left)/85)),logX);
          let last=-Infinity;
          for(const v of tickList){
            if(v<xl||v>xh)continue;
            const x=X(v);axisLine(x,y1,x,y2);
            if(j!==axisIds.length-1)continue;
            const label=xAxis.ticktext?.[tickList.indexOf(v)]||number(v),width=ctx.measureText(label).width,place=Math.min(w-width/2-2,Math.max(width/2+2,x));
            if(place-width/2>last+5){ctx.textAlign="center";ctx.fillText(label,place,y2+14);last=place+width/2;}
          }
          if(j===axisIds.length-1){
            ctx.textAlign="center";ctx.fillText(xAxis.title?.text||layout.xaxis?.title?.text||"", (left+right)/2,h-4,right-left);
          }
        }
        ctx.save();ctx.beginPath();ctx.rect(left,y1,right-left,y2-y1);ctx.clip();
        for(const s of layers.filter(layer=>layer.axis===id))this.drawTrace(ctx,s,g);
        for(const sh of layout.shapes||[]){
          if(sh.y0===sh.y1 && Number.isFinite(sh.y0)){
            ctx.strokeStyle=p.text;ctx.lineWidth=1;ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(left,Y(sh.y0));ctx.lineTo(right,Y(sh.y0));ctx.stroke();ctx.setLineDash([]);
          }
        }
        if(Number.isFinite(this._cursor)){ctx.strokeStyle=p.text;ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(X(this._cursor),y1);ctx.lineTo(X(this._cursor),y2);ctx.stroke();ctx.setLineDash([]);}
        for(const point of this._cursors||[]){
          if((point.axis||"y")!==id||!Number.isFinite(point.x)||!Number.isFinite(point.y))continue;
          const px=X(point.x),py=Y(point.y);
          ctx.strokeStyle=ctx.fillStyle=point.color||p.accent;ctx.setLineDash([3,4]);ctx.lineWidth=1;
          ctx.beginPath();ctx.moveTo(px,y1);ctx.lineTo(px,y2);ctx.stroke();ctx.setLineDash([]);
          marker(ctx,this.shape,px,py,4,this.pen.fill);
          if(point.label){ctx.textAlign="left";ctx.fillText(point.label,Math.min(px+6,right-12),Math.max(y1+10,py-6));}
        }
        ctx.restore();
      });
      this.layers=layers;
      this.hasPickBase=false;
      if(!this._cursors?.length)this.paintPick();
    }
    paintPick(){
      const c=this.canvas,ctx=c.getContext("2d");
      if(this.hasPickBase){
        ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,c.width,c.height);ctx.drawImage(this.pickBase,0,0);ctx.restore();
      }else if(this.selected){
        this.pickBase??=document.createElement("canvas");
        this.pickBase.width=c.width;this.pickBase.height=c.height;
        this.pickBase.getContext("2d").drawImage(c,0,0);this.hasPickBase=true;
      }
      this.drawSelection(ctx);
    }
    isBar(t){return t.type==="bar"||(!t.type&&!t.mode&&["hist","susp"].includes(this.kind));}
    drawTrace(ctx,s,g){
      const {t,heat,color,values}=s,{X,Y,box}=g,pen=this.pen;
      ctx.save();ctx.strokeStyle=ctx.fillStyle=color;ctx.lineWidth=this.display?.line?.width??pen.width;
      const n=t.x.length, mode=t.mode||(["scatter","steer-throttle","mix","rainbow"].includes(this.kind)?"markers":"lines");
      const bar=this.isBar(t),dots=mode.includes("markers")||n===1;
      const bin=Math.abs(X(t.x[1]??(t.x[0]+1))-X(t.x[0]));
      const barOptions=this.display?.bar;
      const widthScale=bar?(barOptions?.widthScale??1):1;
      const bandWidth=Number.isFinite(t.width)?Math.abs(X(t.width)-X(0)):bin*(heat?1:.86);
      const normalWidth=Number.isFinite(bandWidth)?Math.max(1,bandWidth*widthScale):1;
      const logBins=(heat||bar)&&this.axes.x?.scale==="log";
      const binUnits=Number.isFinite(t.width)?t.width:Math.abs((t.x[1]??t.x[0]+1)-t.x[0])*(heat?1:.86);
      const baseline=bar&&this.axes.y?.scale==="log"?box.b:Y(0);
      const striped=bar&&(barOptions?.fill?barOptions.fill==="pattern":this.getAttribute("plot-style")==="pattern");
      const filled=barOptions?.fill?barOptions.fill==="solid":pen.fill;
      const pattern=striped&&!values?stripePattern(ctx,color):null;
      if(!heat&&!bar&&mode.includes("lines")){
        ctx.beginPath();let connected=false;
        for(let i=0;i<n;i++){
          if(!Number.isFinite(t.x[i])||!Number.isFinite(t.y[i])){connected=false;continue;}
          const x=X(t.x[i]),y=Y(t.y[i]);
          if(!Number.isFinite(x)||!Number.isFinite(y)){connected=false;continue;}
          if(connected){if(t.line?.shape==="hv")ctx.lineTo(x,Y(t.y[i-1]));ctx.lineTo(x,y);}
          else ctx.moveTo(x,y);
          connected=true;
        }
        ctx.setLineDash(this.display?.line?.dash??(t.line?.dash==="dot"?[2,4]:pen.dash));ctx.stroke();ctx.setLineDash([]);
      }
      if(heat||bar||dots){
        const settings=this.markerStyle, sizes=t.marker?.size;
        const large=typeof sizes==="number"&&sizes>=8, radius=settings?.size??(large?pen.radius+2:pen.radius);
        const base=settings?.size??pen.radius;
        const shape=t.marker?.symbol==="cross"&&!this.hasAttribute("marker")&&(!settings?.shape||settings.shape==="auto")?"cross":this.shape;
        if(dots&&!bar&&!heat)ctx.globalAlpha=settings?.opacity??(values||large?1:.76);
        ctx.lineWidth=pen.fill?1:1.1;
        const valuesPalette=values?Array.from({length:96},(_,i)=>ramp(i,[0,95],t.colorscale||t.marker?.colorscale,this.colors.dark)):null;
        for(let i=0;i<n;i++){
          if(!Number.isFinite(t.x[i])||(!heat&&!Number.isFinite(t.y[i])))continue;
          const x=X(t.x[i]),y=heat?box.t:Y(t.y[i]);
          const bw=logBins?Math.max(1,2*(X(t.x[i]+binUnits*widthScale/2)-x)):normalWidth;
          if(!Number.isFinite(x)||!Number.isFinite(y)||x<box.l-bw||x>box.r+bw)continue;
          if(values){
            if(!Number.isFinite(values[i]))continue;
            const index=Math.round(95*(values[i]-s.limits[0])/(s.limits[1]-s.limits[0]));
            ctx.fillStyle=ctx.strokeStyle=valuesPalette[Math.max(0,Math.min(95,index))];
          }
          if(heat){
            const hh=box.b-box.t;
            const band=this.getAttribute("plot-style")==="bold"?.70:this.getAttribute("plot-style")==="pattern"?.32:.47;
            ctx.fillRect(x-bw/2,y+(1-band)*hh/2,bw+1,band*hh);
          }else if(bar){
            const bh=baseline-y;
            if(filled||striped){ctx.fillStyle=striped?(pattern||stripePattern(ctx,ctx.strokeStyle)):ctx.strokeStyle;ctx.fillRect(x-bw/2,y,bw,bh);}
            if(!filled)ctx.strokeRect(x-bw/2,y,bw,bh);
          }else{
            const pointRadius=Array.isArray(sizes)?Math.max(.5,sizes[i]*base/4.4):radius;
            if(n===1&&this.data.layout?.yaxis?.scaleanchor==="x"){
              ctx.save();ctx.fillStyle=this.colors.fg;marker(ctx,shape,x,y,pointRadius+1.4,true);ctx.restore();
              marker(ctx,shape,x,y,pointRadius,true);continue;
            }
            marker(ctx,shape,x,y,pointRadius,pen.fill||!!values);
          }
        }
      }
      ctx.restore();
    }
    drawSelection(ctx){
      const pick=this.selected;if(!pick){this.readout.textContent="Click to inspect · Drag to zoom";return;}
      const layer=this.layers[pick.series], t=layer?.t;if(!t)return;
      const g=this.geometries.find(item=>item.id===layer.axis),i=pick.index;
      const x=t.x[i],y=layer.heat?layer.values[i]:t.y[i];
      const px=g.X(x),py=layer.heat?(g.box.t+g.box.b)/2:g.Y(y);
      if(px>=g.box.l-1&&px<=g.box.r+1&&py>=g.box.t-1&&py<=g.box.b+1){
        ctx.save();ctx.strokeStyle=this.colors.fg;ctx.lineWidth=2;marker(ctx,this.shape,px,py,6,false);ctx.restore();
      }
      const layout=this.data.layout||{};
      const map=layout.yaxis?.scaleanchor==="x";
      const xAxis=layout["xaxis"+layer.axis.slice(1)]||layout.xaxis||{};
      const xLabel=xAxis.title?.text||Object.values(layout).find(a=>typeof a?.anchor==="string"&&a.anchor.startsWith("y")&&a.title?.text)?.title.text||(map?"East (m)":"X");
      const yLabel=layout["yaxis"+layer.axis.slice(1)]?.title?.text||(layer.heat?"Speed":map?"North (m)":"Y");
      const extra=t.meta?.pick&&Number.isFinite(t.customdata?.[i])?" · "+t.meta.pick+" "+number(t.customdata[i]):
        layer.values&&!layer.heat?" · "+number(layer.values[i])+" "+(t.marker?.colorbar?.title?.text||""):"";
      const xText=xAxis.ticktext?.[xAxis.tickvals?.indexOf(x)]||number(x);
      const origin=t.ids?.[i]==null?"":" · Sample "+t.ids[i]+(Number.isFinite(t.meta?.time?.[i])?" · "+number(t.meta.time[i])+" s":"");
      this.readout.textContent=[t.name,xLabel+" "+xText,yLabel+" "+number(y)+(layer.heat?" "+(t.colorbar?.title?.text||""):"")].filter(Boolean).join(" · ")+extra+origin;
    }
    selectSample(source,id,emit=false){
      const series=this.data?.data?.findIndex(t=>t.meta?.source===source&&t.ids?.includes(id));
      if(series==null||series<0)return false;
      return this.setPoint(series,this.data.data[series].ids.indexOf(id),emit);
    }
    setPoint(series,index,emit=true){
      const t=this.data?.data?.[series],heat=t?.type==="heatmap"||(this.kind==="colour"&&!!t?.z);
      const x=t?.x[index],y=heat?t.z?.[0]?.[index]:t?.y?.[index],axes=this.axes;
      if(!Number.isFinite(x)||!Number.isFinite(y)||(axes?.x?.scale==="log"&&x<=0)||(axes?.y?.scale==="log"&&y<=0))return false;
      this.selected={series,index};this.schedule(true);
      if(emit)this.dispatchEvent(new CustomEvent("dv-select",{bubbles:true,composed:true,detail:{series,index,x,y,
        source:t.meta?.source,sampleId:t.ids?.[index],time:t.meta?.time?.[index],distance:t.meta?.distance?.[index]}}));
      return true;
    }
    changeRange(range){
      this.range=range;this.schedule();
      this.dispatchEvent(new CustomEvent("dv-range",{bubbles:true,composed:true,detail:{range:range?.slice()||null}}));
    }
    zoom(factor){
      if(!this.full)return;
      const logarithmic=this.axes.x?.scale==="log";
      const f=logarithmic?Math.log10:v=>v,inv=logarithmic?v=>10**v:v=>v;
      const [lo,hi]=(this.range||this.full).map(f),[low,high]=this.full.map(f);
      let mid=(lo+hi)/2;
      const selected=this.selected,point=selected&&this.layers[selected.series].t.x[selected.index];
      if(Number.isFinite(point)&&f(point)>=lo&&f(point)<=hi)mid=f(point);
      const span=(hi-lo)*factor;
      if(span>=high-low){this.changeRange(null);return;}
      const left=Math.max(low,Math.min(high-span,mid-span/2));
      this.changeRange([inv(left),inv(left+span)]);
    }
    pan(offset){
      if(!this.range)return;
      if(this.axes.x?.scale==="log"){
        const [a,b]=this.range.map(Math.log10),[lo,hi]=this.full.map(Math.log10);
        const delta=offset/(this.range[1]-this.range[0])*(b-a);
        const left=Math.min(hi-(b-a),Math.max(lo,a+delta));
        this.changeRange([10**left,10**(left+b-a)]);return;
      }
      const span=this.range[1]-this.range[0];
      const left=Math.max(this.full[0],Math.min(this.full[1]-span,this.range[0]+offset));
      this.changeRange([left,left+span]);
    }
    contextRequest(e,x,y){
      const native=this.dispatchEvent(new CustomEvent("dv-context",{bubbles:true,composed:true,cancelable:true,detail:{x,y}}));
      if(!native)e.preventDefault();
    }
    wire(){
      const canvas=this.canvas;
      const local=e=>{const r=canvas.getBoundingClientRect();return [e.clientX-r.left,e.clientY-r.top];};
      canvas.onpointerdown=e=>{
        if(this.hasAttribute("static")||e.button!==0)return;
        const [x,y]=local(e),g=this.geometries?.find(({box:b})=>x>=b.l&&x<=b.r&&y>=b.t&&y<=b.b);
        const mode=this.getAttribute("interaction");
        if(g){this.drag={x,y,g,pan:mode==="pan"||(!mode&&e.shiftKey)};canvas.setPointerCapture(e.pointerId);}
      };
      canvas.onpointercancel=()=>{this.drag=null;};
      canvas.onpointerup=e=>{
        const start=this.drag;this.drag=null;if(!start)return;
        const [x,y]=local(e),{g}=start;
        const mode=this.getAttribute("interaction");
        if(Math.abs(x-start.x)>7){
          if(mode==="pick")return;
          if(start.pan){this.pan((start.x-x)/(g.box.r-g.box.l)*(g.xh-g.xl));return;}
          const at=xp=>g.fromFraction((Math.max(g.box.l,Math.min(g.box.r,xp))-g.box.l)/(g.box.r-g.box.l));
          const range=[at(Math.min(x,start.x)),at(Math.max(x,start.x))];if(range[1]>range[0])this.changeRange(range);return;
        }
        if(mode==="zoom"||mode==="pan")return;
        let best=null,score=Infinity;
        const byX=mode==="pick"&&this.kind!=="scatter"&&this.kind!=="steer-throttle"&&!this.kind.startsWith("scatter-");
        for(const layer of this.layers.filter(s=>s.axis===g.id)){
          const t=layer.t;
          for(let i=0;i<t.x.length;i++){
            const px=g.X(t.x[i]),py=layer.heat?y:g.Y(t.y[i]);
            if(!Number.isFinite(t.x[i])||(!layer.heat&&!Number.isFinite(t.y[i]))||px<g.box.l-.5||px>g.box.r+.5||py<g.box.t-.5||py>g.box.b+.5)continue;
            const d=(px-x)**2+(byX?0:(py-y)**2);
            if(d<score){score=d;best=[layer.i,i];}
          }
        }
        if(best)this.setPoint(...best);
      };
      canvas.ondblclick=()=>{if(!this.hasAttribute("static")&&!["pick","pan"].includes(this.getAttribute("interaction")))this.changeRange(null);};
      canvas.onkeydown=e=>{
        if(this.hasAttribute("static"))return;
        if(["zoom","pan"].includes(this.getAttribute("interaction")))return;
        if(e.shiftKey&&this.range&&["ArrowLeft","ArrowRight"].includes(e.key)){
          e.preventDefault();this.pan((e.key==="ArrowLeft"?-1:1)*(this.range[1]-this.range[0])*.2);return;
        }
        if(["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Home","End"].includes(e.key)){
          e.preventDefault();
          let series=this.selected?.series??0;
          if(e.key==="ArrowUp"||e.key==="ArrowDown")series=(series+(e.key==="ArrowUp"?1:-1)+this.layers.length)%this.layers.length;
          const t=this.layers[series].t,n=t.x.length, step=["ArrowLeft","End"].includes(e.key)?-1:1;
          let i=this.selected?.index??-1;
          if(e.key==="Home")i=0;else if(e.key==="End")i=n-1;else if(e.key==="ArrowLeft"||e.key==="ArrowRight")i+=step;
          i=Math.min(n-1,Math.max(0,i));
          while(i>=0&&i<n){if(this.setPoint(series,i))break;i+=step;}
        }else if(e.key==="Escape"&&this.getAttribute("interaction")!=="pick"){this.changeRange(null);}
      };
    }
    table(){
      const data=this.data;
      if(!Array.isArray(data.columns)||!Array.isArray(data.rows)){this.message("Invalid table");return;}
      const wrap=html("div"),table=html("table"),head=table.createTHead().insertRow(),body=table.createTBody();wrap.className="tableWrap";
      table.setAttribute("aria-label",this.getAttribute("label")||this.kind);
      for(const col of data.columns){const th=html("th",col);th.scope="col";head.append(th);}
      data.rows.forEach((cells,i)=>{
        const row=body.insertRow();
        if(i===data.selected)row.setAttribute("aria-selected","true");
        cells.forEach((value,j)=>{const cell=html(j?"td":"th",value);if(!j)cell.scope="row";row.append(cell);});
      });
      wrap.append(table);this.frame.replaceChildren(wrap);
    }
    instrument(){
      if(this.kind==="gauges"){
        const wrap=html("div");wrap.className="gauges";
        for(const [kind,[channel,label,unit]] of Object.entries(instruments)){
          const part=html("dv-"+kind);
          part.setAttribute("plot-style",this.getAttribute("plot-style")||"fine");
          if(this.hasAttribute("marker"))part.setAttribute("marker",this.getAttribute("marker"));
          part.data={value:this.data[channel],label,unit};wrap.append(part);
        }
        this.frame.replaceChildren(wrap);return;
      }
      const [,defaultLabel,defaultUnit]=instruments[this.kind],{value,label=defaultLabel,unit=defaultUnit,min=0,max=this.kind==="dial"?250:100}=this.data;
      if(!Number.isFinite(value)){this.message("No value");return;}
      const wrap=html("div"),caption=html("small",label),read=html("strong",this.kind==="lamp"?(value>5?"On":"Off"):number(Math.round(value*10)/10)+(unit?" "+unit:""));
      wrap.className="instrument";wrap.append(caption,read);
      if(this.kind==="meter"){
        const m=html("meter");m.min=min;m.max=max;m.value=value;m.setAttribute("aria-label",label);wrap.append(m);
      }else if(this.kind==="lamp"){
        const lamp=html("i");lamp.className="lamp";lamp.style.color=value>5?this.colors.ref:this.colors.text;
        if(this.pen.fill||value>5)lamp.style.background="currentColor";lamp.style.borderRadius=this.shape==="circle"?"100%":"0";
        if(this.shape==="diamond")lamp.style.transform="rotate(45deg)";read.prepend(lamp);
      }else if(this.kind==="dial"||this.kind==="steering"){
        const c=html("canvas");c.setAttribute("aria-hidden","true");wrap.append(c);
        const ctx=canvasContext(c,150,84),p=this.colors;
        ctx.lineWidth=this.pen.width*2;ctx.strokeStyle=p.accent;ctx.setLineDash(this.pen.dash);
        if(this.kind==="dial"){
          ctx.strokeStyle=p.grid;ctx.beginPath();ctx.arc(75,72,54,Math.PI,Math.PI*2);ctx.stroke();
          const angle=Math.PI*(1+Math.max(0,Math.min(1,(value-min)/(max-min||1))));
          ctx.strokeStyle=p.accent;ctx.beginPath();ctx.moveTo(75,72);ctx.lineTo(75+48*Math.cos(angle),72+48*Math.sin(angle));ctx.stroke();
          ctx.setLineDash([]);marker(ctx,this.shape,75,72,4,this.pen.fill);
        }else{
          ctx.translate(75,42);ctx.rotate(value*Math.PI/180);ctx.beginPath();ctx.arc(0,0,33,0,Math.PI*2);
          ctx.moveTo(-30,-9);ctx.lineTo(0,4);ctx.lineTo(30,-9);ctx.moveTo(0,4);ctx.lineTo(0,32);ctx.stroke();
        }
      }
      this.frame.replaceChildren(wrap);
    }
  }
  for(const name of [...charts,...reports,"gauges",...Object.keys(instruments)]){
    if(!customElements.get("dv-"+name))customElements.define("dv-"+name,class extends TelemetryElement {});
  }
})();
