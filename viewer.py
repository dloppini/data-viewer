"""Data Viewer runs locally using resources on this computer."""
import argparse
import base64
import json
import importlib.util
import mimetypes
import os
import secrets
import subprocess
import sys
import sysconfig
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import urlopen

import numpy as np
import plotly
from plotly.utils import PlotlyJSONEncoder
from data_viewer.charts import CATALOG, figure
from data_viewer.scatter import DEFAULTS, LABELS, defaults, demo_scatter, log_scatter, title
from data_viewer.demo_data import demo_samples, bokeh_speed
from data_viewer.logstore import prepare
from data_viewer.telemetry import LAPS, LENGTH, RATE, SPLITS, clock, position, sample

ROOT = Path(__file__).resolve().parent
TOKEN = secrets.token_urlsafe(24)
STATE = {"state":"idle"}
LOCK = threading.Lock()
READ_SLOT = threading.Semaphore(1)
LOG = None
QT_PROCESS = None
FILES = {"/":"documentation/dashboard.html","/workbook":"web/index.html","/app.js":"web/app.js","/style.css":"web/style.css",
         "/library":"web/library.html","/library.js":"web/library.js",
         "/scatter-host.js":"web/scatter-host.js","/scatter.css":"web/scatter.css",
         "/telemetry-elements.js":"web/telemetry-elements.js",
         "/demo":"web/demo.html","/demo.js":"web/demo.js","/demo.css":"web/demo.css",
         "/demo-assets/uplot.js":"web/vendor/uplot-1.6.32/uPlot.iife.min.js",
         "/demo-assets/uplot.css":"web/vendor/uplot-1.6.32/uPlot.min.css",
         "/demo-assets/bokeh.js":Path(sysconfig.get_path("purelib"))/"bokeh/server/static/js/bokeh.min.js",
         "/web/telemetry-elements.js":"web/telemetry-elements.js"}
for name in ("web/workspace-nav.js","web/dashboard.js","web/dashboard.css","web/style.css","documentation/dashboard.html",
             "documentation/Data Viewer Manual.pdf","documentation/manual.md",
             "examples/styles.html","examples/plugin-scatter.html","examples/histogram.html","documentation/references/coverage.html"):
    FILES["/"+name]=name
for folder in ("documentation/research","documentation/references/MoTeC","examples/previews"):
    for item in (ROOT/folder).iterdir():
        if item.is_file() and item.suffix.lower() in {".png",".html",".htm",".pdf",".chm",".json"}:
            name=item.relative_to(ROOT).as_posix()
            FILES["/"+name]=name
REDIRECTS={"/architecture":"/#map","/architettura":"/#map","/dashboard":"/","/guide":"/",
           "/mockup":"/examples/styles.html","/loading-study":"/documentation/research/data-loading.html",
           "/studio":"/documentation/research/data-loading.html"}
PLOTLY = Path(plotly.__file__).parent/"package_data"/"plotly.min.js"
for preview in (ROOT/"examples/previews").glob("*.png"):
    FILES["/previews/"+preview.name]=FILES["/anteprime/"+preview.name]="examples/previews/"+preview.name

def set_state(**kwargs):
    with LOCK: STATE.update(kwargs)

def html_arrays(value):
    """Export portable JSON arrays from Plotly's compact numeric representation."""
    if isinstance(value, list):
        return [html_arrays(item) for item in value]
    if isinstance(value, dict):
        if "bdata" in value and "dtype" in value:
            array = np.frombuffer(base64.b64decode(value["bdata"]), dtype=value["dtype"])
            if "shape" in value:
                array = array.reshape(tuple(int(size) for size in value["shape"].split(",")))
            return array.tolist()
        return {key: html_arrays(item) for key, item in value.items()}
    return value

def open_log(path):
    global LOG
    try:
        if not path:
            code = ("from tkinter import Tk,filedialog; r=Tk();r.withdraw();r.attributes('-topmost',True);"
                    "print(filedialog.askopenfilename(title='Open local log',filetypes=[('Log','*.csv *.parquet')]),end='');r.destroy()")
            env={**os.environ,"PYTHONIOENCODING":"utf-8"}
            path=subprocess.check_output([sys.executable,"-c",code],encoding="utf-8",env=env)
        if not path:
            set_state(state="cancelled")
            return
        set_state(state="loading")
        log=prepare(path,progress=lambda n:set_state(progress=n))
        with LOCK:
            LOG=log
            STATE.update(state="ready",info=log.info(),progress=1)
    except Exception as err:
        set_state(state="error",error=str(err))

def session():
    d=np.linspace(0,LENGTH,220)
    x,y=position(d)
    return dict(app="data-viewer-local",language="en",scatterApi=1,dashboardVersion=1,
                scatterDefaults={key:defaults(key) for key in DEFAULTS},
                channels={key:title(LABELS,key) for key in LABELS},
                length=LENGTH,rate=RATE,catalog=CATALOG,laps=[clock(l["t"][-1]) for l in LAPS],
                track=np.column_stack([x,-y]).round(1).tolist(),splits=SPLITS.tolist(),token=TOKEN)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass

    def reply(self,body,mime="application/json",status=200):
        if not isinstance(body,bytes):
            body=json.dumps(body,cls=PlotlyJSONEncoder,ensure_ascii=False,separators=(",",":")).encode()
        self.send_response(status)
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","private, max-age=86400" if self.path=="/plotly.min.js" else "no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        try: self.wfile.write(body)
        except (ConnectionResetError,BrokenPipeError,ConnectionAbortedError): pass

    def local_host(self):
        return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}")

    def do_GET(self):
        if not self.local_host():
            return self.reply({"error":"Invalid host"},status=403)
        url=urlsplit(self.path)
        path=unquote(url.path)
        q={k:v[-1] for k,v in parse_qs(url.query).items()}
        try:
            redirect=REDIRECTS.get(path)
            if path=="/" and any(key in q for key in ("view","source","style","tone")):
                redirect="/workbook?"+url.query
            if redirect:
                self.send_response(302)
                self.send_header("Location",redirect)
                self.end_headers()
            elif path in FILES or path=="/plotly.min.js":
                target=PLOTLY if path=="/plotly.min.js" else ROOT/FILES[path]
                mime=mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                self.reply(target.read_bytes(),mime+("; charset=utf-8" if mime.startswith("text/") else ""))
            elif url.path=="/api/session": self.reply(session())
            elif url.path=="/api/demo/samples": self.reply(demo_samples())
            elif url.path=="/api/demo/bokeh": self.reply(bokeh_speed(q.get("tone")=="dark"))
            elif url.path=="/api/state":
                with LOCK: result=STATE.copy()
                self.reply(result)
            elif url.path in ("/api/chart","/api/cursor"):
                key=q.get("view","history")
                active,reference=int(q.get("lap",1)),int(q.get("ref",2))
                distance=float(q.get("at",LENGTH*.43))
                axis=q.get("axis","d")
                if key not in CATALOG or not(0<=active<len(LAPS) and 0<=reference<len(LAPS)) or axis not in ("t","d") or not(0<=distance<=LENGTH):
                    raise ValueError("Invalid worksheet parameters.")
                if url.path=="/api/cursor":
                    if "elapsed" in q:
                        elapsed=float(q["elapsed"])
                        if not np.isfinite(elapsed): raise ValueError("Invalid time.")
                        distance=float(np.interp(elapsed,LAPS[active]["t"],LAPS[active]["d"]))
                    self.reply(dict(sample=sample(LAPS[active],distance),ref=sample(LAPS[reference],distance)))
                else:
                    payload=figure(key,active,reference,axis,distance)
                    if "figure" in payload:
                        spec = payload["figure"].to_plotly_json()
                        payload["figure"] = html_arrays(spec) if q.get("format") == "html" else spec
                    self.reply(payload)
            elif url.path=="/api/scatter":
                query=json.loads(q["query"])
                if q.get("source")=="local":
                    with LOCK: log=LOG
                    if not log: raise ValueError("No log is open.")
                    with READ_SLOT: result=log_scatter(log,query,float(q["start"]),float(q["end"]))
                else:
                    result=demo_scatter(q.get("view","scatter"),query,int(q.get("lap",1)),int(q.get("ref",2)))
                self.reply(result)
            elif url.path=="/api/window":
                with LOCK: log=LOG
                if not log: raise ValueError("No log is open.")
                with READ_SLOT:
                    window=log.window(q.get("channel",""),float(q["start"]),float(q["end"]),int(q.get("bins",800)))
                self.reply(window)
            else: self.reply({"error":"Not found"},status=404)
        except (ValueError,KeyError,OSError,OverflowError) as err:
            self.reply({"error":str(err)},status=400)

    def do_POST(self):
        global QT_PROCESS
        if not self.local_host() or self.path not in ("/api/open","/api/qt-example") or not secrets.compare_digest(self.headers.get("X-Viewer-Token",""),TOKEN):
            return self.reply({"error":"Invalid request."},status=403)
        if self.path=="/api/qt-example":
            try:
                if importlib.util.find_spec("PyQt6.QtWebEngineWidgets") is None:
                    raise ModuleNotFoundError
                with LOCK:
                    if QT_PROCESS is not None and QT_PROCESS.poll() is None:
                        return self.reply({"message":"The Qt example is already open."})
                    QT_PROCESS=subprocess.Popen([sys.executable,str(ROOT/"examples/qt_scatter.py")],cwd=ROOT,
                        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                return self.reply({"message":"Qt example started in a desktop window."},status=202)
            except ModuleNotFoundError:
                return self.reply({"error":"Install PyQt6-WebEngine in the project environment to open the native example."},status=409)
            except OSError as err:
                return self.reply({"error":str(err)},status=500)
        try:
            size=int(self.headers.get("Content-Length",0))
            if not 0<size<=16_384: raise ValueError("Invalid file path.")
            path=json.loads(self.rfile.read(size)).get("path")
            if not isinstance(path,str): raise ValueError("Invalid file path.")
        except (TypeError,ValueError,AttributeError) as err:
            return self.reply({"error":str(err)},status=400)
        with LOCK:
            busy=STATE["state"] in ("choosing","loading")
            if not busy:
                STATE.update(state="loading" if path else "choosing",progress=0,error="")
        if busy: return self.reply({"error":"A file is already opening."},status=409)
        threading.Thread(target=open_log,args=(path,),daemon=True).start()
        self.reply({"ok":True},status=202)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int)
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("file",nargs="?")
    args=parser.parse_args()
    port=8769 if args.port is None else args.port
    if os.name == "nt":
        # Two Windows listeners using SO_REUSEADDR can serve different viewer versions on one port.
        ThreadingHTTPServer.allow_reuse_address = False
    for candidate in ([port] if args.port is not None else [*range(port,port+16),0]):
        try:
            server=ThreadingHTTPServer(("127.0.0.1",candidate),Handler)
            break
        except OSError:
            if args.port is not None or candidate==0: raise
            if not args.file and not args.no_browser:
                try:
                    with urlopen(f"http://127.0.0.1:{candidate}/api/session",timeout=1) as res:
                        session=json.load(res)
                    if session.get("app")=="data-viewer-local" and session.get("dashboardVersion")==1 and CATALOG.keys()==session.get("catalog",{}).keys():
                        webbrowser.open(f"http://127.0.0.1:{candidate}")
                        return
                except (OSError,ValueError,AttributeError): pass
    if args.file:
        set_state(state="loading")
        threading.Thread(target=open_log,args=(args.file,),daemon=True).start()
    url=f"http://127.0.0.1:{server.server_port}"+("/workbook?source=local" if args.file else "/")
    print(url,flush=True)
    if not args.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__": main()
