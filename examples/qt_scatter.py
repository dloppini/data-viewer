"""A Python-controlled HTML scatter widget. Run with the project environment."""
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenu, QPushButton, QScrollArea, QVBoxLayout, QWidget)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_viewer.scatter import LABELS, OPS, defaults, demo_scatter, title, validate

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Scatter</title>
<style>html,body{margin:0;height:100%;font:14px system-ui}dv-scatter{--dv-height:calc(100vh - 84px)}</style>
<script src="telemetry-elements.js"></script><script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<dv-scatter frame="clean" label="Telemetry scatter"></dv-scatter><script>
const plot=document.querySelector('dv-scatter');
new QWebChannel(qt.webChannelTransport,({objects:{host}})=>{
 host.patch.connect((raw,figure)=>{try{const patch=JSON.parse(raw);if(figure)patch.figure=JSON.parse(figure);
     plot.updatePlot(patch);}catch(e){host.error(e.message);}});
 host.highlight.connect((source,id)=>plot.selectSample(source,id));
 plot.addEventListener("dv-select",e=>host.picked(JSON.stringify(e.detail)));
 plot.addEventListener("dv-range",e=>host.viewport(JSON.stringify(e.detail)));
 plot.addEventListener("dv-context",e=>{e.preventDefault();host.menu(e.detail.x,e.detail.y);});
 document.addEventListener("contextmenu",e=>{if(!e.defaultPrevented){e.preventDefault();host.menu(e.clientX,e.clientY);}});
 host.ready();
});</script></html>"""

def choices(entries, selected):
    control = QComboBox()
    for value, label in entries:
        control.addItem(label, value)
    control.setCurrentIndex(control.findData(selected))
    return control

def field(value):
    control = QLineEdit("" if value is None else str(value))
    control.setPlaceholderText("Auto")
    return control

def number(control):
    value = control.text().strip()
    if not value:
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("Enter a finite number.")
    return parsed

def validate_display(axes, marker):
    for key, axis in axes.items():
        scale, bounds = axis.get("scale"), axis.get("range")
        if key not in ("x","y") or scale not in ("linear","log"):
            raise ValueError("Choose a linear or logarithmic scale for each axis.")
        if bounds is not None and (len(bounds)!=2 or any(type(v) not in (float,int) or not math.isfinite(v) for v in bounds)
                or bounds[0]>=bounds[1] or (scale=="log" and bounds[0]<=0)):
            raise ValueError(f"Check the {key.upper()} limits. Enter two increasing limits, positive for log, or leave both blank.")
    if marker.get("shape") not in ("auto","circle","square","diamond","cross"):
        raise ValueError("Unknown marker shape.")
    size, opacity = marker.get("size"), marker.get("opacity")
    if size is not None and (type(size) not in (int,float) or not .5<=size<=12):
        raise ValueError("Radius must be between 0.5 and 12 px.")
    if opacity is not None and (type(opacity) not in (int,float) or not 0<opacity<=1):
        raise ValueError("Opacity must be greater than 0 and at most 100%.")

class Settings(QDialog):
    def __init__(self, state, labels, parent):
        super().__init__(parent)
        self.setWindowTitle("Scatter settings")
        self.setMinimumWidth(540)
        self.labels, self.axes, self.gates = labels, {}, []
        box = QVBoxLayout(self)
        grid = QGridLayout()
        box.addLayout(grid)
        for i, name in enumerate(("Axis", "Channel", "Scale", "Minimum", "Maximum")):
            grid.addWidget(QLabel(name), 0, i)
        q, marker = state["query"], state["marker"]
        for row, key in enumerate(("x", "y"), 1):
            axis = state["axes"][key]
            bounds = axis["range"] or [None, None]
            controls = (choices(labels.items(), q[key]),
                        choices([("linear","Linear"),("log","Logarithmic")], axis["scale"]),
                        field(bounds[0]), field(bounds[1]))
            self.axes[key] = controls
            for i, control in enumerate((QLabel(key.upper()), *controls)):
                grid.addWidget(control, row, i)
            for control, name in zip(controls,("channel","scale","minimum","maximum")):
                control.setAccessibleName(f"{key.upper()} {name}")
        gate_heading = QHBoxLayout()
        gate_heading.addWidget(QLabel("Sample gates · match all"))
        gate_heading.addStretch()
        self.add = QPushButton("Add gate")
        self.add.clicked.connect(lambda: self.add_gate())
        gate_heading.addWidget(self.add)
        box.addLayout(gate_heading)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        rows = QWidget()
        self.gate_rows = QVBoxLayout(rows)
        self.gate_rows.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(rows)
        box.addWidget(scroll)
        for gate in q["gates"]:
            self.add_gate(gate)
        form = QFormLayout()
        box.addLayout(form)
        self.shape = choices([(s, "Use plot style" if s=="auto" else s.title())
                              for s in ("auto","circle","square","diamond","cross")], marker["shape"])
        self.radius = field(marker["size"])
        self.opacity = field(None if marker["opacity"] is None else marker["opacity"]*100)
        self.colour = choices([("", "Series colour"), *labels.items()], q["colour"])
        self.size = choices([("", "Fixed size"), *labels.items()], q["size"])
        for label, control in (("Shape",self.shape),("Radius (px)",self.radius),
                ("Opacity (%)",self.opacity),("Colour by",self.colour),("Size by",self.size)):
            form.addRow(label,control)
        self.status = QLabel()
        box.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.commit)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)

    def add_gate(self, gate=None):
        gate = gate or {"channel": next(iter(self.labels)), "op": ">", "value": 0}
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0,0,0,0)
        channel = choices(self.labels.items(), gate["channel"])
        op = choices([(k,k) for k in OPS], gate["op"])
        value = field(gate["value"])
        for control,name in ((channel,"Gate channel"),(op,"Gate condition"),(value,"Gate threshold")):
            control.setAccessibleName(name)
        remove = QPushButton("Remove")
        for control in (channel, op, value, remove):
            line.addWidget(control)
        entry = (channel, op, value)
        def discard():
            self.gates.remove(entry)
            row.deleteLater()
            self.add.setEnabled(True)
        remove.clicked.connect(discard)
        self.gates.append(entry)
        self.gate_rows.addWidget(row)
        self.add.setEnabled(len(self.gates)<12)

    def commit(self):
        try:
            axes, query = {}, {"colour":self.colour.currentData(), "size":self.size.currentData(), "gates":[]}
            for key, (channel, scale, low, high) in self.axes.items():
                query[key] = channel.currentData()
                lo, hi = number(low), number(high)
                bounds = None if lo is None and hi is None else [lo,hi]
                axes[key] = {"range":bounds, "scale":scale.currentData()}
            for channel, op, threshold in self.gates:
                query["gates"].append({"channel":channel.currentData(),"op":op.currentData(),"value":number(threshold)})
            validate(query,self.labels)
            size, opacity = number(self.radius), number(self.opacity)
            self.settings = dict(query=query,axes=axes,marker=dict(shape=self.shape.currentData(),size=size,
                opacity=None if opacity is None else opacity/100))
            validate_display(axes,self.settings["marker"])
            self.accept()
        except ValueError as e:
            self.status.setText(str(e))

class Bridge(QObject):
    patch = pyqtSignal(str,str)
    highlight = pyqtSignal(str, float)
    @pyqtSlot()
    def ready(self):
        self.parent().connected = True
        self.parent().configure(**self.parent().desired, force=True)

    @pyqtSlot(int,int)
    def menu(self, x, y):
        self.parent().show_menu(QPoint(x,y))

    @pyqtSlot(str)
    def picked(self, raw):
        self.parent().samplePicked.emit(json.loads(raw))

    @pyqtSlot(str)
    def viewport(self, raw):
        self.parent().rangeChanged.emit(json.loads(raw)["range"])

    @pyqtSlot(str)
    def error(self, message):
        self.parent().failed.emit(message)

class ScatterView(QWebEngineView):
    """Pass a query -> figure callable and a mapping of channel IDs to display labels."""
    samplePicked = pyqtSignal(dict)
    rangeChanged = pyqtSignal(object)
    failed = pyqtSignal(str)
    _finished = pyqtSignal(object)

    def __init__(self, read, labels, query, parent=None):
        super().__init__(parent)
        self.read, self.labels = read, labels
        self.settings = dict(query=deepcopy(query), axes={k:dict(scale="linear",range=None) for k in ("x","y")},
                             marker=dict(shape="auto",size=None,opacity=None))
        self.desired = self.settings
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.job = None
        self.generation = 0
        self.loaded = False
        self.connected = False
        self.channel = QWebChannel(self.page())
        self.bridge = Bridge(self)
        self.channel.registerObject("host", self.bridge)
        self.page().setWebChannel(self.channel)
        self._finished.connect(self.finish)
        self.destroyed.connect(lambda _, pool=self.pool: pool.shutdown(wait=False,cancel_futures=True))
        self.setHtml(PAGE, QUrl.fromLocalFile(str(ROOT / "web")+"/"))

    def show_menu(self, point):
        menu = QMenu(self)
        settings = menu.addAction("Scatter settings…")
        if menu.exec(self.mapToGlobal(point)) == settings:
            dialog = Settings(self.desired,self.labels,self)
            if dialog.exec():
                self.configure(**dialog.settings)

    def configure(self, *, query=None, axes=None, marker=None, force=False):
        next_state = deepcopy(self.desired)
        if query is not None:
            validate(query,self.labels)
            next_state["query"] = deepcopy(query)
        for key, patch in (("axes",axes),("marker",marker)):
            if patch is not None:
                next_state[key].update(deepcopy(patch))
        validate_display(next_state["axes"],next_state["marker"])
        if self.loaded and not force and next_state == self.desired:
            return
        same_query = next_state["query"] == self.desired["query"]
        self.desired = next_state
        if not self.connected:
            return
        if self.job is not None and same_query and not force:
            return
        self.generation += 1
        generation = self.generation
        if self.job is not None:
            self.job.cancel()
            self.job = None
        if self.loaded and not force and next_state["query"] == self.settings["query"]:
            self.publish()
            return
        def read_figure(query):
            return json.dumps(self.read(query),separators=(",",":"),allow_nan=False)
        future = self.pool.submit(read_figure,deepcopy(next_state["query"]))
        self.job = future
        def notify(done):
            try:
                self._finished.emit((generation, done))
            except RuntimeError:
                pass  # The containing application has closed the widget.
        future.add_done_callback(notify)

    def finish(self, result):
        generation, future = result
        if generation != self.generation:
            return
        self.job = None
        try:
            self.publish(future.result())
        except Exception as e:
            self.desired = self.settings
            self.failed.emit(str(e))

    def publish(self, figure=""):
        patch = {k:self.desired[k] for k in ("axes","marker")}
        raw = json.dumps(patch, separators=(",",":"), allow_nan=False)
        self.settings = self.desired
        self.loaded = True
        self.bridge.patch.emit(raw,figure)

    def select_sample(self, source, sample_id):
        self.bridge.highlight.emit(source,sample_id)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    plot = ScatterView(lambda q: demo_scatter("scatter",q,1,2),
                       {k:title(LABELS,k) for k in LABELS},defaults("scatter"))
    window.setCentralWidget(plot)
    window.setWindowTitle("Data Viewer · Python scatter host")
    window.statusBar().showMessage("Right-click the plot for scatter settings.")
    plot.samplePicked.connect(lambda p:window.statusBar().showMessage(
        f"{p['source']} · sample {p['sampleId']} · {p['time']:.3f} s"))
    plot.failed.connect(window.statusBar().showMessage)
    window.resize(1000,650)
    window.show()
    sys.exit(app.exec())
