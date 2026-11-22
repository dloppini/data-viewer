"""Desktop integration checks for the standalone custom elements."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from verify_scatter_controls import FIXTURE, PYTHON, ROOT, settle


def offline(browser):
    ctx=browser.new_context(offline=True,viewport={"width":1280,"height":820})
    page=ctx.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto((ROOT/"examples/plugin-scatter.html").as_uri())
    plot=page.locator("dv-scatter")
    canvas=plot.locator("canvas")
    canvas.wait_for()
    for tone in ("dark","light"):
        page.emulate_media(color_scheme=tone)
        plot.evaluate("(p,t)=>p.setAttribute('theme',t)",tone)
        settle(page)
        if folder:=os.environ.get("PLUGIN_SCREENSHOTS"):
            page.screenshot(path=str(Path(folder)/("plugin-offline-"+tone+".png")))
    assert page.locator("dialog").count()==0 and not plot.get_by_role("button").count()
    assert plot.evaluate("""p=>{const s=p.localSource,q=JSON.parse(p.getAttribute('query'));
      return p.data.matched===s.channels.brake.filter(v=>v<5).length &&
        p.data.data[0].ids.every((id,i)=>p.data.data[0].x[i]===s.channels[q.x][s.ids.indexOf(id)])}""")
    canvas.press("Home")
    settle(page)
    assert "Sample" in plot.locator("output").inner_text()
    plot.evaluate("""p=>{window.syncs=0;window.draws=0;window.lastPick=p.selected;
      p.addEventListener('dv-load',()=>syncs++);const fn=p.drawChart;
      p.drawChart=function(...a){draws++;return fn.apply(this,a)};}""")
    settle(page)
    page.evaluate("draws=0")
    plot.evaluate("""p=>{p.setAttribute('options','{"marker":{"shape":"square"}}');
      p.setAttribute('options','{"marker":{"shape":"diamond","size":5}}');
      p.setAttribute('plot-style','bold')}""")
    settle(page)
    assert page.evaluate("syncs===0 && draws===1")
    assert plot.evaluate("p=>p.shape==='diamond' && p.selected===lastPick")
    page.evaluate("draws=0")
    plot.evaluate("p=>p.setAttribute('frame','apple')")
    settle(page)
    assert page.evaluate("draws===0")
    plot.evaluate("p=>p.setAttribute('external-controls','')")
    assert not plot.locator("output").is_visible()
    canvas.press("ArrowRight")
    settle(page)
    assert page.evaluate("draws===0")
    plot.evaluate("""p=>{p.addEventListener('dv-context',e=>{e.preventDefault();window.menuHits=(window.menuHits||0)+1});
      p.setAttribute('query',JSON.stringify({x:'speed',y:'brake',size:'brake',gates:[{channel:'steer',op:'>',value:1}]}))}""")
    settle(page)
    assert plot.evaluate("p=>p.data.layout.xaxis.title.text==='Speed (km/h)' && p.data.data[0].marker.size.length>0")
    canvas.click(button="right")
    assert page.evaluate("menuHits===1")
    plot.evaluate("p=>p.setAttribute('query','{}')")
    plot.get_by_role("status").wait_for()
    assert "channel" in plot.get_by_role("status").inner_text()
    plot.get_by_role("status").press("Shift+F10")
    assert page.evaluate("menuHits===2")
    plot.evaluate("""p=>{p.data={channels:{x:Array.from({length:40000},(_,i)=>i),y:Array(40000).fill(4)}};
        p.setAttribute('query','{"x":"x","y":"y"}')}""")
    page.wait_for_function("document.querySelector('dv-scatter').data?.matched===40000")
    assert plot.evaluate("p=>p.data.data[0].ids.length===3200 && p.data.data[0].ids.every((id,i)=>id===p.data.data[0].x[i])")
    assert not errors,errors
    ctx.close()
    print("Offline named channels, original picks, stable sampling, error recovery and host controls passed.")


def remote(browser, origin):
    page=browser.new_page(viewport={"width":1440,"height":900})
    errors,reads=[],[]
    page.on("request",lambda r:reads.append(r.url) if "/api/scatter?" in r.url else None)
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.route("**/plugin-test.html",lambda route:route.fulfill(content_type="text/html",body="""
        <!doctype html><meta charset="utf-8"><script defer src="/telemetry-elements.js"></script>
        <dv-scatter id="plot" external-controls src="/api/scatter?source=local&amp;start=0&amp;end=10000"
        query='{"x":"steer","y":"throttle"}'></dv-scatter>"""))
    page.goto(origin+"/plugin-test.html")
    plot=page.locator("#plot");plot.locator("canvas").wait_for()
    assert len(reads)==1 and plot.evaluate("p=>p.data.matched===1000000 && p.data.data[0].ids.length===3200")
    settle(page)
    plot.evaluate("""p=>{window.draws=0;const f=p.drawChart;p.drawChart=function(...args){draws++;const r=f.apply(this,args);
      window.drawEnd=performance.now();return r};
      p.setAttribute('query','{"x":"time_s","y":"brake"}');
      p.setAttribute('query','{"x":"throttle","y":"brake","gates":[{"channel":"brake","op":">","value":10}]}');
      p.setAttribute('options','{"axes":{"y":{"scale":"linear","range":[0,50]}},"marker":{"shape":"diamond"}}')}""")
    page.wait_for_function("plot.shape==='diamond' && plot.data.matched<1000000")
    settle(page)
    assert len(reads)==2 and page.evaluate("draws===1")
    assert plot.evaluate("p=>p.data.matched===Math.floor(1000000/41)*30+Math.max(0,(1000000%41)-11)")
    latency=page.evaluate("drawEnd-performance.getEntriesByType('resource').filter(r=>r.name.includes('/api/scatter?')).at(-1).startTime")
    plot.evaluate("p=>{draws=0;p.setAttribute('options','{\"marker\":{\"shape\":\"square\"}}')}")
    settle(page)
    assert len(reads)==2 and page.evaluate("draws===1")
    plot.evaluate("p=>{draws=0;p.setPoint(0,3)}")
    settle(page)
    assert len(reads)==2 and page.evaluate("draws===0")
    plot.evaluate("""p=>p.setAttribute('options','{"marker":{"size":-2}}')""")
    plot.get_by_role("status").wait_for()
    plot.evaluate("p=>p.removeAttribute('options')")
    plot.locator("canvas").wait_for()
    assert len(reads)==2
    # A superseded in-flight response cannot overwrite the newest result.
    plot.evaluate("""p=>{const real=window.fetch.bind(window);window.fetch=(url,init)=>{
      if(String(url).includes('/old'))return new Promise(resolve=>window.late=()=>resolve(new Response('{"data":[{"x":[9],"y":[9]}]}')));
      return real(url,init)}; p.setAttribute('src','/old')}""")
    page.wait_for_function("typeof late==='function'")
    plot.evaluate("""p=>{p.removeAttribute('query');p.setAttribute('src','/api/chart?format=html&view=hist')}""")
    page.wait_for_function("plot.data.data[0].type==='bar'")
    page.evaluate("late()")
    settle(page)
    assert plot.evaluate("p=>p.data.data[0].type==='bar'")
    plot.evaluate("""p=>p.setAttribute('src','/missing-component-data')""")
    plot.get_by_text("Data source returned HTTP 404.").wait_for()
    plot.evaluate("""p=>{p.setAttribute('src','/api/chart?format=html&view=hist');
      document.body.insertAdjacentHTML('beforeend','<dv-stats src="/api/chart?format=html&amp;view=stats"></dv-stats><dv-dial src="/api/chart?format=html&amp;view=gauges"></dv-dial>')}""")
    plot.locator("canvas").wait_for()
    page.locator("dv-stats table").wait_for()
    page.locator("dv-dial .instrument").wait_for()
    assert not errors,errors
    page.close()
    print(f"1M source rows, 3,200 displayed. Combined edit: one request, one draw, {latency:.0f} ms request-to-draw. Visual edit: zero reads, one draw. Pick: zero reads or full draws.")


def library(browser,origin):
    page=browser.new_page(viewport={"width":1280,"height":820})
    page.goto(origin+"/library?object=hist")
    p=page.locator("#preview > dv-hist");p.locator("canvas").wait_for()
    page.get_by_text("Use in HTML",exact=True).click()
    assert 'src="./dv-hist.json"' in page.locator("#snippet").inner_text()
    with page.expect_download() as event:
        page.get_by_role("button",name="Download data JSON").click()
    assert event.value.suggested_filename=="dv-hist.json"
    assert json.loads(Path(event.value.path()).read_text(encoding="utf-8"))==p.evaluate("e=>e.data")
    def pixels():
        settle(page)
        return p.locator("canvas").evaluate("c=>c.toDataURL()")
    original=pixels()
    p.evaluate("""e=>e.setAttribute('options','{"line":{"width":5,"dash":[8,4]}}')""")
    line=pixels()
    p.evaluate("""e=>e.setAttribute('options','{"bar":{"fill":"solid","widthScale":0.4}}')""")
    assert len({original,line,pixels()})==3
    p.evaluate("e=>e.removeAttribute('options')")
    for theme in ("light","dark"):
        page.select_option("#toneChoice",theme)
        for width in (1024,1440):
            page.set_viewport_size({"width":width,"height":900})
            page.locator(".libraryFooter").scroll_into_view_if_needed()
            settle(page)
            positions=page.locator(".libraryFooter .actions > *").evaluate_all("a=>a.map(b=>{const r=b.getBoundingClientRect();return [r.left,r.right,r.top+r.height/2]})")
            assert all(0<=l<r<=width for l,r,_ in positions)
            assert len(set(round(c) for _,_,c in positions))==1,positions
            if folder:=os.environ.get("PLUGIN_SCREENSHOTS"):
                if width==1440:page.screenshot(path=str(Path(folder)/("plugin-library-"+theme+".png")))
    keys=page.locator("#object option").evaluate_all("a=>a.map(o=>o.value)")
    for key in keys:
        page.select_option("#object",key)
        live=page.locator("#preview > dv-"+key)
        live.locator("canvas, table, .instrument").first.wait_for()
        assert live.evaluate("""async e=>{
          const plugin=document.createElement(e.localName);
          const url=URL.createObjectURL(new Blob([JSON.stringify(e.data)],{type:'application/json'}));
          try{
            const ready=new Promise((resolve,reject)=>{
              plugin.addEventListener('dv-load',resolve,{once:true});
              plugin.addEventListener('dv-error',v=>reject(Error(v.detail.message)),{once:true})});
            plugin.setAttribute('src',url);document.body.append(plugin);await ready;
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            return !!plugin.shadowRoot.querySelector('canvas,table,.instrument,.gauges');
          }finally{plugin.remove();URL.revokeObjectURL(url)}
        }"""),key
    print(f"All {len(keys)} catalogue elements rendered from a JSON URL, including tables and instruments.")
    page.close()

if __name__=="__main__":
    with tempfile.TemporaryDirectory() as tmp:
        server=subprocess.Popen([str(PYTHON),"-u","-c",FIXTURE,tmp],cwd=ROOT,stdout=subprocess.PIPE,text=True)
        try:
            origin="http://127.0.0.1:"+str(int(server.stdout.readline()))
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel="chrome")
                offline(browser);remote(browser,origin);library(browser,origin)
                browser.close()
        finally:
            server.terminate();server.wait(timeout=10)
