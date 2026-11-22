/* Optional host controls. The standalone plot also accepts updatePlot() directly. */
class ScatterHost {
  constructor(container,button,onChange=()=>{}){
    this.container=container;this.button=button;this.onChange=onChange;this.saved=new Map();
    this.dialog=document.createElement("dialog");this.dialog.className="scatterSettings";
    this.dialog.setAttribute("aria-label","Scatter settings");document.body.append(this.dialog);
    this.dialog.innerHTML=`<form autocomplete="off"><header><h2>Scatter settings</h2><button type="button" data-close aria-label="Close settings">×</button></header>
      <fieldset class="ssBody"><legend class="ssSr">Plot configuration</legend>
      <div class="ssAxes"></div><section><div class="ssHeading"><h3>Sample gates</h3><button type="button" data-add>+ Add gate</button></div><div class="ssGates"></div></section>
      <section><h3>Markers</h3><div class="ssMarks"></div></section></fieldset>
      <footer><output role="status"></output><button type="button" data-cancel>Cancel</button><button class="primary" type="submit">Apply</button></footer></form>`;
    const find=s=>this.dialog.querySelector(s);
    this.form=find("form");this.body=find("fieldset");this.axes=find(".ssAxes");this.gates=find(".ssGates");this.marks=find(".ssMarks");this.status=find("output");
    find("[data-add]").onclick=()=>this.addGate();find("[data-close]").onclick=find("[data-cancel]").onclick=()=>this.close();
    this.dialog.oncancel=e=>{e.preventDefault();this.close();};
    this.form.onsubmit=e=>{e.preventDefault();this.apply();};
    button.onclick=()=>this.open();
    new ResizeObserver(()=>{
      if(this.dialog.open&&this.anchor)this.position();
    }).observe(this.dialog);
    container.addEventListener("dv-context",e=>{if(this.element&&e.target===this.element){e.preventDefault();this.open(e.detail);}});
    container.addEventListener("contextmenu",e=>{if(this.element&&!this.element.canvas){e.preventDefault();this.open({x:e.clientX,y:e.clientY});}});
  }
  close(){
    this.request?.abort();this.request=null;
    if(this.dialog.open)this.dialog.close();
  }
  prepare(key,defaults,labels,context={},scope=key){
    this.loading?.abort();this.loading=null;
    this.close();this.element=null;this.button.hidden=!defaults;this.button.disabled=true;
    this.key=key;this.context=context;this.labels=labels;this.scope=scope;
    if(!defaults)return;
    if(!this.saved.has(scope))this.saved.set(scope,{query:structuredClone(defaults),
      axes:{x:{scale:"linear",range:null},y:{scale:"linear",range:null}},marker:{shape:"auto",size:null,opacity:null}});
    this.state=this.saved.get(scope);
  }
  async figure(query=this.state.query,signal){
    if(!signal){
      this.loading?.abort();this.loading=new AbortController();signal=this.loading.signal;
    }
    const params=new URLSearchParams({...this.context,view:this.key,query:JSON.stringify(query)});
    const response=await fetch("/api/scatter?"+params,{signal});
    const data=await response.json();if(!response.ok)throw Error(data.error||"Could not load samples.");return data;
  }
  bind(element,figure){
    this.element=element;this.button.disabled=false;
    element.updatePlot({figure,axes:this.state.axes,marker:this.state.marker});this.onChange(this.state,element.data);
  }
  field(parent,label,name,options,value,type="number"){
    const wrap=document.createElement("label"),title=document.createElement("span");
    title.textContent=label;const input=document.createElement(options?"select":"input");input.name=name;
    if(options){for(const [key,text] of options)input.add(new Option(text,key));}
    else {input.type=type;input.step="any";input.placeholder="Auto";}
    input.value=value??"";wrap.append(title,input);parent.append(wrap);return input;
  }
  addGate(g){
    const row=document.createElement("div");row.className="ssGate";this.gates.append(row);
    const labels=Object.entries(this.labels);
    this.field(row,"Channel","gateChannel",labels,g?.channel??labels[0][0]);
    this.field(row,"Condition","gateOp",["<","<=","==","!=",">=",">"].map(k=>[k,k]),g?.op??">");
    const value=this.field(row,"Threshold","gateValue",null,g?.value??0);value.required=true;
    const remove=document.createElement("button");remove.type="button";remove.textContent="×";remove.setAttribute("aria-label","Remove gate");row.append(remove);
    const add=this.dialog.querySelector("[data-add]");add.disabled=this.gates.children.length>=12;
    remove.onclick=()=>{row.remove();add.disabled=false;};
  }
  open(point){
    if(!this.element||this.dialog.open)return;
    this.status.textContent="";this.body.disabled=false;this.form.querySelector('[type="submit"]').disabled=false;
    this.axes.replaceChildren();this.marks.replaceChildren();this.gates.replaceChildren();this.dialog.querySelector("[data-add]").disabled=false;
    const {query,axes,marker}=this.state,labels=Object.entries(this.labels);
    for(const axis of ["x","y"]){
      const row=document.createElement("div");row.className="ssAxis";this.axes.append(row);
      this.field(row,axis.toUpperCase()+" channel",axis,labels,query[axis]);
      this.field(row,"Scale",axis+"Scale",[["linear","Linear"],["log","Logarithmic"]],axes[axis].scale);
      this.field(row,"Minimum",axis+"Min",null,axes[axis].range?.[0]);
      this.field(row,"Maximum",axis+"Max",null,axes[axis].range?.[1]);
    }
    for(const g of query.gates)this.addGate(g);
    const shape=["auto","circle","square","diamond","cross"].map(s=>[s,s==="auto"?"Use plot style":s[0].toUpperCase()+s.slice(1)]);
    this.field(this.marks,"Shape","shape",shape,marker.shape);
    const size=this.field(this.marks,"Radius (px)","radius",null,marker.size);size.min=.5;size.max=12;
    const opacity=this.field(this.marks,"Opacity (%)","opacity",null,marker.opacity==null?null:marker.opacity*100);opacity.min=1;opacity.max=100;
    if(this.key!=="scatter-density")this.field(this.marks,"Colour by","colour",[["","Series colour"],...labels],query.colour);
    this.field(this.marks,"Size by","size",[["","Fixed size"],...labels],query.size);
    this.anchor=point;
    this.dialog.style.left=this.dialog.style.top="";this.dialog.showModal();
    if(point)this.position();
    this.form.elements.namedItem("x").focus();
  }
  position(){
    const rect=this.dialog.getBoundingClientRect();
    this.dialog.style.left=Math.max(8,Math.min(innerWidth-rect.width-8,this.anchor.x))+"px";
    this.dialog.style.top=Math.max(8,Math.min(innerHeight-rect.height-8,this.anchor.y))+"px";
  }
  async apply(){
    const get=k=>this.form.elements.namedItem(k), val=k=>get(k)?.value||"";
    const query={x:val("x"),y:val("y"),gates:[],colour:val("colour"),size:val("size")};
    for(const row of this.gates.children){
      const [channel,op,value]=row.querySelectorAll("select,input");
      query.gates.push({channel:channel.value,op:op.value,value:value.valueAsNumber});
    }
    const axes={};
    for(const k of ["x","y"]){
      const scale=val(k+"Scale"),min=val(k+"Min"),max=val(k+"Max");
      if((min==="")!==(max==="")||(min!==""&&(+min>=+max||(scale==="log"&&+min<=0)))){
        this.status.textContent=k.toUpperCase()+" limits must increase. Use two positive limits for log, or leave both blank for auto.";
        get(k+"Min").focus();return;
      }
      axes[k]={scale,range:min===""?null:[+min,+max]};
    }
    const marker={shape:val("shape"),size:val("radius")===""?null:+val("radius"),opacity:val("opacity")===""?null:+val("opacity")/100};
    const next={query,axes,marker};
    if(JSON.stringify(next)===JSON.stringify(this.state)){this.close();return;}
    const controller=new AbortController();this.request=controller;
    const button=this.form.querySelector('[type="submit"]');
    try{
      let figure;
      if(JSON.stringify(query)!==JSON.stringify(this.state.query)){
        this.body.disabled=button.disabled=true;this.status.textContent="Reading samples…";
        figure=await this.figure(query,controller.signal);
      }
      if(controller.signal.aborted)return;
      this.element.updatePlot({figure,axes,marker});this.state=next;this.saved.set(this.scope,next);
      this.onChange(next,this.element.data);this.close();
    }catch(e){if(!controller.signal.aborted)this.status.textContent=e.message;}
    finally{if(!controller.signal.aborted){button.disabled=this.body.disabled=false;this.request=null;}}
  }
}
