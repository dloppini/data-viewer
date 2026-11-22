"""Measure full canvas draws and queries through the desktop workbook and library."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/Scripts/python.exe"
FIXTURE = """
from pathlib import Path
import sys
import numpy as np
import pyarrow as pa, pyarrow.parquet as pq
from http.server import ThreadingHTTPServer
import viewer
from data_viewer.logstore import prepare
ids=np.arange(1_000_000)
path=Path(sys.argv[1])/'session.parquet'
pq.write_table(pa.table(dict(time_s=ids/100,steer=ids%181-90,throttle=ids%101,brake=ids%41)),path,row_group_size=65536)
viewer.LOG=prepare(path)
viewer.set_state(state='ready',info=viewer.LOG.info())
with ThreadingHTTPServer(('127.0.0.1',0),viewer.Handler) as server:
    print(server.server_port,flush=True)
    server.serve_forever()
"""

def settle(page):
    page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")

def verify(browser, origin, local):
    page = browser.new_page(viewport={"width":1440,"height":900},locale="en-GB")
    errors, requests = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url) if "/api/scatter?" in r.url else None)
    page.goto(origin+("/?source=local" if local else "/library?object=scatter"))
    if local:
        page.locator("#localName").get_by_text("session.parquet").wait_for()
        page.select_option("#logPlot","scatter")
    el = page.locator(("#plot" if local else "#preview")+" > dv-scatter")
    canvas = el.locator("canvas")
    canvas.wait_for()
    button = page.get_by_role("button",name="Scatter settings",exact=True)
    dialog = page.get_by_role("dialog",name="Scatter settings")
    result = []
    el.evaluate("""e=>{window.plotUnderTest=e;window.fullDraws=[];window.picked=null;
      const draw=e.drawChart;e.drawChart=function(...args){const t=performance.now();const v=draw.apply(this,args);
      window.lastFullDraw=performance.now();fullDraws.push(lastFullDraw-t);return v};
      e.addEventListener('dv-select',event=>window.picked=event.detail);}""")
    def start():
        settle(page)
        requests.clear()
        page.evaluate("fullDraws.length=0")
    def counts(action, reads, draws):
        settle(page)
        durations=page.evaluate("fullDraws.slice()")
        assert (len(requests),len(durations))==(reads,draws),(action,requests,durations)
        result.append([action,reads,draws,durations])
        if reads:
            latency=page.evaluate("""()=>lastFullDraw-performance.getEntriesByType('resource')
              .filter(r=>new URL(r.name).pathname==='/api/scatter').at(-1).startTime""")
            result[-1].append({"query_to_draw_ms":round(latency,1)})
    def apply():
        dialog.get_by_role("button",name="Apply").click()
        dialog.wait_for(state="hidden")
    def select(name,val):
        dialog.locator('[name="'+name+'"]').select_option(val)
    def fill(name,val):
        dialog.locator('[name="'+name+'"]').fill(str(val))
    start()
    canvas.click(button="right")
    dialog.wait_for()
    fill("radius",4)
    select("shape","diamond")
    assert page.evaluate("fullDraws.length")==0
    apply()
    counts("marker changes",0,1)
    before=el.evaluate("e=>e.data.data")
    start()
    canvas.press("Shift+F10")
    fill("xMin",0)
    fill("xMax",100)
    apply()
    counts("axis limits",0,1)
    assert before==el.evaluate("e=>e.data.data")
    start()
    button.click()
    apply()
    counts("unchanged Apply",0,0)
    start()
    button.click()
    fill("xMax",8)
    dialog.get_by_role("button",name="Cancel").click()
    counts("Cancel",0,0)
    start()
    button.click()
    select("x","throttle")
    select("y","time_s" if local else "rpm")
    select("size","brake")
    select("colour","steer")
    select("xScale","log")
    fill("xMin",1)
    fill("xMax",100)
    fill("opacity",65)
    dialog.get_by_role("button",name="Add gate").click()
    select("gateChannel","brake")
    select("gateOp",">")
    fill("gateValue",10)
    apply()
    counts("channels, gate, scale and markers",1,1)
    fig=el.evaluate("e=>e.data")
    assert fig["layout"]["dvAxes"]["x"]==dict(scale="log",range=[1,100])
    assert fig["layout"]["dvMarker"]["opacity"]==.65
    if local:
        assert fig["matched"]==sum(i%41>10 for i in range(1_000_000))
        assert len(fig["data"][0]["ids"])==3200
    coords=el.evaluate("e=>[1,10,100].map(e.geometries[0].X)")
    assert abs((coords[2]-coords[1])-(coords[1]-coords[0]))<1e-6
    start()
    canvas.press("Home")
    counts("sample pick",0,0)
    selected=page.evaluate("picked")
    assert isinstance(selected["sampleId"],int) and selected["source"] and selected["x"]>0
    if local:
        i=selected["sampleId"]
        assert selected["time"]==i/100 and selected["x"]==i%101 and i%41>10
    assert el.evaluate("(e,p)=>e.selectSample(p.source,p.sampleId)",selected)
    original=el.evaluate("e=>e.selected")
    el.evaluate("e=>e.updatePlot({figure:e.data})")
    settle(page)
    assert el.evaluate("e=>e.selected")==original
    start()
    el.evaluate("""e=>{e.updatePlot({marker:{size:3}});e.updatePlot({marker:{size:4}});e.updatePlot({marker:{size:5}})}""")
    counts("three updates in one frame",0,1)
    start()
    button.click()
    fill("gateValue",999999)
    apply()
    el.get_by_text("No samples",exact=True).wait_for()
    assert el.evaluate("e=>e.selected===null") and len(requests)==1
    button.click()
    dialog.get_by_role("button",name="Remove gate").click()
    apply()
    canvas.wait_for()
    for theme in ("light","dark"):
        if local:
            if page.locator("html").get_attribute("data-tone")!=theme:
                page.click("#tone")
        else:
            page.select_option("#toneChoice",theme)
        canvas.click(button="right")
        rect = dialog.bounding_box()
        assert rect["x"]>=0 and rect["x"]+rect["width"]<=1440.1
        assert rect["y"]>=0 and rect["y"]+rect["height"]<=900.1
        bottoms=dialog.locator(".ssAxis").first.locator("input,select").evaluate_all("a=>a.map(e=>e.getBoundingClientRect().bottom)")
        assert max(bottoms)-min(bottoms)<=1, bottoms
        assert dialog.evaluate("e=>e.scrollWidth===e.clientWidth")
        if local and (shots:=os.environ.get("SCATTER_SCREENSHOTS")):
            page.screenshot(path=str(Path(shots)/("scatter-"+theme+".png")))
        dialog.press("Escape")
    assert not errors,errors
    print(("Parquet" if local else "Library"),json.dumps(result),flush=True)
    page.close()

def presets(browser, origin):
    page=browser.new_page(viewport={"width":1280,"height":820})
    session=page.request.get(origin+"/api/session").json()
    for key in session["scatterDefaults"]:
        page.goto(origin+"/?view="+key)
        component=page.locator("#plot > dv-"+key)
        component.locator("canvas").wait_for()
        page.get_by_role("button",name="Scatter settings").click()
        dialog=page.get_by_role("dialog",name="Scatter settings")
        dialog.locator('[name="yMin"]').fill("8")
        dialog.locator('[name="yMax"]').fill("1")
        dialog.get_by_role("button",name="Apply").click()
        assert "limits must increase" in dialog.locator("output").inner_text()
        dialog.locator('[name="yMin"]').fill("")
        dialog.locator('[name="yMax"]').fill("")
        dialog.locator('[name="x"]').select_option("t")
        dialog.locator('[name="shape"]').select_option("cross")
        dialog.get_by_role("button",name="Apply").click()
        dialog.wait_for(state="hidden")
        assert component.evaluate("e=>e.data.layout.dvMarker.shape==='cross' && e.data.layout.xaxis.title.text.includes('time')")
    print("All nine workbook scatter presets accepted channel and marker changes and rejected invalid limits.",flush=True)
    page.close()

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tempdir:
        server = subprocess.Popen([str(PYTHON),"-u","-c",FIXTURE,tempdir],cwd=ROOT,stdout=subprocess.PIPE,text=True)
        try:
            port=int(server.stdout.readline())
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel="chrome")
                for local in (False,True):
                    verify(browser,"http://127.0.0.1:"+str(port),local)
                presets(browser,"http://127.0.0.1:"+str(port))
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
