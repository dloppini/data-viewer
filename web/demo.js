"use strict";

const el = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const legacyDemo = params.get("prova") || "";
const legacyNames = {"barra-html":"brake-bar","tabella-html":"sample-table",cursori:"cursors",neumorfico:"neumorphic",pulito:"clean"};
const selectedDemo = params.get("demo") || legacyNames[legacyDemo] || legacyDemo.replace(/^grafico-/, "chart-");
const chartSlug = key => "chart-" + key;
let worksheets = [[chartSlug("scatter"), "G–G scatter plot"]];
if (selectedDemo?.startsWith("chart-")) {
  try {
    const {catalog} = await json("/api/session");
    worksheets = Object.entries(catalog).filter(([, [type]]) => ["Traces","Scatter","Distributions","Track","Report charts"].includes(type))
      .map(([key, [,name,note]]) => [chartSlug(key), name, note]);
  } catch (err) {
    el("status").textContent = err.message;
    throw err;
  }
}
const groups = [
  ["HTML elements", [
    ["brake-bar", "Brake indicator", "Move the time slider to see the brake input at the selected sample."],
    ["sample-table", "Sample table", "Move the time slider to scroll through the samples. The highlighted row shows the selected sample and the surrounding rows show its neighbours."]
  ]],
  ["Charts", worksheets],
  ["Libraries", [
    ["plotly", "Plotly", "Hover over the trace to inspect a value. Switch libraries to compare the same data on the same axes."],
    ["bokeh", "Bokeh", "Hover over the trace to inspect a value. Python builds the plot and BokehJS draws it."],
    ["uplot", "uPlot", "Hover over the trace to read the values in the legend. uPlot draws the same data on a canvas."]
  ]],
  ["Interactions", [
    ["zoom", "Zoom", "Drag horizontally to zoom. Use the buttons to focus on braking or restore the full 20 seconds."],
    ["pan", "Pan", "Drag left or right, or use the buttons. The window stays eight seconds wide."],
    ["pick", "Data pick", "Click the trace or enter a time. The marker snaps to the nearest original sample."],
    ["cursors", "A/B cursors", "Select A or B, then click the trace to move that cursor. Time and speed differences are calculated as B minus A."]
  ]],
  ["Styles", [
    ["apple", "Apple", "Compare the surfaces, colours and type. All three styles use the same trace, scale and dimensions."],
    ["neumorphic", "Neumorphic", "Inspect the soft relief around the trace. Switch styles to compare it with the same data."],
    ["clean", "Clean", "Inspect the thin lines and editorial type. The same trace sits on a flat surface."]
  ]]
];

const [family, choices] = groups.find(([, items]) => items.some(([id]) => id === selectedDemo)) || groups[0];
const [id, title, hint] = choices.find(([key]) => key === selectedDemo) || choices[0];
const styles = {apple:"apple", neumorphic:"soft", clean:"clean"};
const root = document.documentElement;
let preferredTone;
try {
  preferredTone = localStorage.getItem("viewer-tone");
} catch {}
const requestedTone = params.get("tone");
root.dataset.tone = ["light", "dark"].includes(requestedTone) ? requestedTone :
  preferredTone || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
root.dataset.style = styles[id] || "neutral";
document.title = title + " · Demo · Data Viewer";

function link(container, item, label, current) {
  const a = document.createElement("a");
  const query = new URLSearchParams({demo:item});
  if (["light","dark"].includes(requestedTone)) query.set("tone", requestedTone);
  a.href = "/demo?" + query;
  a.textContent = label;
  if (current) a.setAttribute("aria-current", current);
  container.append(a);
}
for (const [name, items] of groups) link(el("families"), name === "Charts" ? chartSlug("scatter") : items[0][0], name, name === family && "true");
for (const [key, name] of choices) link(el("choices"), key, name, key === id && "page");
if (family === "Charts") {
  const label = document.createElement("label");
  label.className = "chartSelect"; label.textContent = "Chart";
  const select = document.createElement("select");
  for (const a of el("choices").children) select.add(new Option(a.textContent, a.href, false, a.hasAttribute("aria-current")));
  select.onchange = () => location.assign(select.value);
  label.append(select); el("choices").after(label);
}
el("familyName").textContent = family;
el("demoTitle").textContent = title;
el("instruction").textContent = hint;

const graph = el("graph");
const fmt = (value, digits = 0) => Number(value).toLocaleString("en-GB", {minimumFractionDigits:digits, maximumFractionDigits:digits});
const signed = (n, digits) => (n > 0 ? "+" : "") + fmt(n, digits);
const css = key => getComputedStyle(root).getPropertyValue("--" + key).trim();
const controls = el("controls");
function controlMarkup(html) {
  controls.innerHTML = html;
  controls.hidden = false;
}
async function json(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error("Could not read local data.");
  return response.json();
}
function asset(path, stylesheet = false) {
  const tag = document.createElement(stylesheet ? "link" : "script");
  if (stylesheet) { tag.rel = "stylesheet"; tag.href = path; }
  else tag.src = path;
  return new Promise((resolve, reject) => {
    tag.onload = resolve;
    tag.onerror = () => reject(new Error("Local library unavailable."));
    document.head.append(tag);
  });
}

function htmlObject(data) {
  const meter = id === "brake-bar";
  el("figureTitle").textContent = meter ? "Brake input" : "Original samples";
  graph.innerHTML = meter ?
    '<div class="meterSpec"><strong class="measure"><span id="percent"></span><small>%</small></strong><meter id="brakeMeter" aria-label="Brake input" min="0" max="100"></meter><div class="scale"><span>0 %</span><span>100 %</span></div></div>' :
    '<table class="sampleTable" aria-label="Five samples from the simulated lap"><thead><tr><th scope="col">Time (s)</th><th scope="col">Speed (km/h)</th><th scope="col">Brake (%)</th></tr></thead><tbody></tbody></table>';
  controlMarkup('<label>Time <input type="range" id="sampleIndex" min="0" max="' + (data.t.length-1) + '" value="600"></label><output id="sampleTime" for="sampleIndex"></output>');
  function show() {
    const i = el("sampleIndex").valueAsNumber;
    el("sampleTime").textContent = fmt(data.t[i], 2) + " s";
    if (meter) {
      el("percent").textContent = fmt(data.brake[i]);
      el("brakeMeter").value = data.brake[i];
    } else {
      const first = Math.max(0, Math.min(i-2, data.t.length-5));
      const body = graph.querySelector("tbody");
      body.replaceChildren();
      for (let j=first; j<first+5; j++) {
        const row = body.insertRow();
        if (j === i) { row.className = "current"; row.setAttribute("aria-current", "true"); }
        for (const value of [fmt(data.t[j],2), fmt(data.speed[j],1), fmt(data.brake[j])]) row.insertCell().textContent = value;
      }
    }
  }
  el("sampleIndex").oninput = show;
  show();
}

async function uplot(data) {
  await Promise.all([asset("/demo-assets/uplot.js"), asset("/demo-assets/uplot.css", true)]);
  const axis = (label, size) => ({label, size, stroke:css("muted"), grid:{stroke:css("grid"), width:1}, ticks:{stroke:css("grid"), width:1}});
  const plot = new uPlot({
    width:graph.clientWidth, height:310, cursor:{drag:{x:false,y:false}, points:{size:5}},
    scales:{x:{time:false, range:[0,20]}, y:{range:[80,220]}},
    axes:[axis("Time (s)",36), axis("Speed (km/h)",48)],
    series:[{label:"Time", value:(_,v) => v == null ? "—" : fmt(v,2)+" s"},
            {label:"Speed", value:(_,v) => v == null ? "—" : fmt(v,1)+" km/h", stroke:css("series"),width:2,points:{show:false}}],
    legend:{show:true,live:true,isolate:false,markers:{show:false}}
  }, [data.t,data.speed], graph);
  new ResizeObserver(() => {
    if (graph.clientWidth > 0 && graph.clientWidth !== plot.width) plot.setSize({width:graph.clientWidth, height:310});
  }).observe(graph);
}

async function speedDemo(data) {
  const axis={gridcolor:css("grid"),zeroline:false,fixedrange:true};
  const line={x:data.t,y:data.speed,type:"scatter",mode:"lines",line:{color:css("series"),width:2},name:"Speed",
    hovertemplate:"%{x:.2f} s · %{y:.1f} km/h<extra></extra>"};
  const layout={height:310,margin:{l:60,r:15,t:12,b:52},showlegend:false,dragmode:false,hovermode:"x",
    paper_bgcolor:css("panel"),plot_bgcolor:css("panel"),font:{family:css("font"),color:css("muted")},
    xaxis:{...axis,title:{text:"Time (s)"},range:[0,20]},yaxis:{...axis,title:{text:"Speed (km/h)"},range:[80,220]}};
  if(id==="plotly"){
    await asset("/plotly.min.js");
    await Plotly.newPlot(graph,[line],layout,{responsive:true,displayModeBar:false,scrollZoom:false,doubleClick:false});
    return;
  }
  await asset("/telemetry-elements.js");
  const zoom=id==="zoom",pan=id==="pan",dual=id==="cursors";
  const chart=document.createElement("dv-trace");
  chart.setAttribute("label","Speed over time");
  chart.setAttribute("external-controls","");
  if(family==="Styles"){chart.setAttribute("static","");line.line.color=css("accent");}
  else chart.setAttribute("interaction",zoom?"zoom":pan?"pan":"pick");
  chart.data={data:[line],layout};
  if(pan)chart.range=[3,11];
  graph.replaceChildren(chart);
  if(family==="Styles")return;
  if (zoom || pan) {
    controlMarkup('<button id="left"></button><button id="right"></button><output id="span"></output>');
    el("left").textContent = zoom ? "Zoom to braking" : "← 2 s";
    el("right").textContent = zoom ? "Show full range" : "2 s →";
    function update() {
      const range=chart.range||[0,20];
      el("span").textContent = fmt(range[0],1) + " – " + fmt(range[1],1) + " s";
      if (pan) {
        el("left").disabled = range[0] <= 0;
        el("right").disabled = range[1] >= 20;
      }
    }
    function shift(forward) {
      if(zoom)chart.changeRange(forward?null:[4,10]);
      else chart.pan(forward?2:-2);
    }
    el("left").onclick = () => shift(false);
    el("right").onclick = () => shift(true);
    chart.addEventListener("dv-range",update);
    update();
  }
  if (zoom || pan) return;
  const times = dual ? [4,8] : [6];
  if (dual) controlMarkup('<label>Cursor <select id="active"><option>A</option><option>B</option></select></label>');
  else controlMarkup("");
  times.forEach((time,j) => {
    const label = document.createElement("label");
    label.textContent = (dual ? ["A","B"][j] : "Time") + " (s)";
    const input = document.createElement("input");
    input.type = "number"; input.id = "time" + j; input.min = 0; input.max = data.t.at(-1); input.step = .01; input.value = time;
    label.append(input); controls.append(label);
  });
  const result = document.createElement("output");
  controls.append(result);
  function nearest(time) {
    const step = data.t[1] - data.t[0];
    return Math.max(0, Math.min(data.t.length-1, Math.round(time/step)));
  }
  const colors = [css("series"),css("ref")];
  function mark() {
    const indices = times.map(nearest);
    chart.cursors=indices.map((i,j)=>({x:data.t[i],y:data.speed[i],color:colors[j],label:dual?["A","B"][j]:""}));
    const [a,b] = indices;
    result.textContent = dual ?
      "Δt " + signed(data.t[b]-data.t[a],2) + " s · Δv " + signed(data.speed[b]-data.speed[a],1) + " km/h" :
      fmt(data.t[a],2) + " s · " + fmt(data.speed[a],1) + " km/h";
  }
  function select(j,time) {
    if (!Number.isFinite(time)) { el("time"+j).value = times[j]; return; }
    times[j] = data.t[nearest(time)];
    el("time"+j).value = times[j].toFixed(2);
    mark();
  }
  times.forEach((_,j) => { el("time"+j).onchange = e => select(j,e.target.valueAsNumber); });
  chart.addEventListener("dv-select",e=>select(dual?el("active").selectedIndex:0,e.detail.x));
  mark();
}

async function worksheet() {
  const key = id.slice("chart-".length);
  el("demoLibrary").href="/library?object="+encodeURIComponent(key);
  const [payload] = await Promise.all([json("/api/chart?format=html&view="+encodeURIComponent(key)), asset("/telemetry-elements.js")]);
  const comparesLaps = ["history","scatter","timing","hist","susp","fft","pos","gps","rainbow-compare"].includes(key);
  el("figureTitle").textContent = comparesLaps ? "Lap 02 · Reference 03" :
    (["outing","sector-chart","channel-chart"].includes(key)?"Session · 4 laps":
     ["race","telemetry-position","telemetry-gps"].includes(key)?"Replay · 4 cars":key==="frf"?"Suspension rig":"Lap 02");
  document.querySelector("figcaption span").textContent = "Simulated telemetry · Levante Circuit";
  const component=document.createElement("dv-"+key);
  component.data=payload.figure;component.setAttribute("label",title);component.setAttribute("static","");
  graph.replaceChildren(component);
}

async function start() {
  if (family === "HTML elements") {
    htmlObject(await json("/api/demo/samples"));
  } else {
    graph.dataset.chart = "";
    el("figureTitle").textContent = "Speed over time";
    if (family === "Charts") {
      await worksheet();
    } else if (id === "bokeh") {
      const [item] = await Promise.all([json("/api/demo/bokeh?tone="+root.dataset.tone),asset("/demo-assets/bokeh.js")]);
      await Bokeh.embed.embed_item(item);
    } else {
      const data = await json("/api/demo/samples");
      if (id === "uplot") await uplot(data);
      else await speedDemo(data);
    }
  }
  el("status").textContent = "";
  graph.dataset.ready = "true";
}
start().catch(err => { el("status").textContent = "Demo unavailable. " + err.message; });
