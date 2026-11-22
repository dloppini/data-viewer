"""Exercise the native Python menu and the HTML widget through Qt WebChannel."""
import json
import sys
from pathlib import Path
from time import monotonic

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMenu

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"examples"))
from qt_scatter import ScatterView, Settings, LABELS, defaults, demo_scatter, title


def until(test, seconds=12):
    end=monotonic()+seconds
    while monotonic()<end:
        if test():
            return
        QTest.qWait(15)
    raise AssertionError("Timed out waiting for the native widget")


if __name__=="__main__":
    app=QApplication(sys.argv)
    reads, patches, picks, errors=[],[],[],[]
    def read(query):
        reads.append(query)
        return demo_scatter("scatter",query,1,2)
    view=ScatterView(read,{k:title(LABELS,k) for k in LABELS},defaults("scatter"))
    view.failed.connect(errors.append)
    view.samplePicked.connect(picks.append)
    view.bridge.patch.connect(lambda config,figure: patches.append(
        {**json.loads(config),**({"figure":json.loads(figure)} if figure else {})}))
    view.resize(900,560)
    view.show()
    def js(expr):
        values=[]
        view.page().runJavaScript(expr,0,values.append)
        until(lambda:bool(values))
        return values[0]
    until(lambda:view.loaded)
    until(lambda:js("Boolean(plot.layers?.length)"))
    assert len(reads)==len(patches)==1
    interactions=[]
    def interact():
        menu=app.activePopupWidget()
        if isinstance(menu,QMenu) and "menu" not in interactions:
            interactions.append("menu")
            menu.setActiveAction(menu.actions()[0])
            QTest.keyClick(menu,Qt.Key.Key_Return)
            return
        dialog=app.activeModalWidget()
        if isinstance(dialog,Settings) and "dialog" not in interactions:
            interactions.append("dialog")
            dialog.axes["x"][0].setCurrentIndex(dialog.axes["x"][0].findData("throttle"))
            dialog.add_gate({"channel":"brake","op":">","value":10})
            dialog.radius.setText("5")
            dialog.commit()
    timer=QTimer()
    timer.timeout.connect(interact)
    timer.start(20)
    view.page().runJavaScript("plot.canvas.dispatchEvent(new MouseEvent('contextmenu',{clientX:180,clientY:80,cancelable:true,bubbles:true}))")
    until(lambda:len(patches)==2)
    timer.stop()
    assert interactions==["menu","dialog"] and len(reads)==2
    until(lambda:js("plot.data?.layout?.dvMarker?.size===5"))
    assert js("plot.data.data.every(t=>t.x.length>0)") and patches[-1]["figure"]["matched"]>0
    view.configure(marker={"shape":"square"})
    until(lambda:js("plot.shape==='square'"))
    assert len(patches)==3 and len(reads)==2 and "figure" not in patches[-1]
    view.configure(marker={"shape":"square"})
    assert len(patches)==3
    js("plot.setPoint(0,4)")
    until(lambda:bool(picks))
    picked=picks[0]
    assert picked["sampleId"]==js("plot.data.data[0].ids[4]") and picked["source"]
    view.select_sample(picked["source"],js("plot.data.data[0].ids[5]"))
    until(lambda:js("plot.selected?.index===5"))
    assert len(picks)==1 and not errors,errors
    view.close()
    print("Qt native right-click menu, combined Apply, visual-only and no-op updates, two-way sample picking passed.")
