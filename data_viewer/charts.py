"""Workbook catalogue. Analysis uses the original samples before display reduction."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .scatter import DEFAULTS, defaults, demo_scatter
from .analysis_plots import ANALYSIS, analysis_figure
from .plot_primitives import A, B, SCALE, axes, line, marked
from .telemetry import CHANNELS, LAPS, LENGTH, RATE, SPLITS, clock, position, sample, spectrum, split_times

CATALOG = {
 "history": ("Traces", "Channel history", "Speed, throttle and brake over a lap."),
 "scatter": ("Traces","G–G scatter plot","Lateral and longitudinal acceleration for each displayed sample."),
 "steer-throttle": ("Traces","Steering vs throttle","Throttle opening against steering angle. Select a point to read both channels."),
 "timing": ("Traces","Timing Story","Time gained or lost at the same distance. A negative delta means the active lap is faster."),
 "outing": ("Traces","Session history","Speed throughout the session, with each lap shown as a separate trace."),
 "colour": ("Traces","Time colour graph","Colour shows how speed changes over time."),
 "hist": ("Distributions","Speed histogram","Percentage of time samples in each speed bin."),
 "susp": ("Distributions","Suspension velocity histogram","Damper shaft velocity. Positive values indicate bump and negative values indicate rebound."),
 "fft": ("Distributions","FFT spectrum","Front-left damper travel amplitude by frequency, using a Hann window."),
 "mix": ("Distributions","Mixture map","Lambda against engine speed, grouped by load band."),
 "track": ("Track","Track report","Minimum speed in each sector, plotted where it occurred."),
 "rainbow": ("Track","Rainbow track map","Speed along the track centreline."),
 "pos": ("Track","Track position","Positions of the active and reference laps at the same elapsed time."),
 "gps": ("Track","GPS driving lines","Simulated driving lines in local east and north coordinates, in metres."),
 "race": ("Track","Race Control","Positions of four simulated cars at the cursor time."),
 "sectors": ("Report","Sector times","Sector splits and time differences from the reference lap."),
 "stats": ("Report","Channel statistics","Minimum, mean and maximum values for each channel across the lap."),
 "accel": ("Report","Acceleration times","Fastest continuous interval between two speeds without dropping below the starting speed."),
 "gauges": ("Instruments","Dashboard","Speed dial, throttle bar, steering wheel, gear, brake light and engine speed at the cursor."),
 "status": ("Instruments","Channel status","Signal values and availability at the selected sample."),
}
CATALOG.update(ANALYSIS)

def acceleration(lap,lo,hi):
    v,t=lap["speed"],lap["t"]
    best,start=None,None
    for i in np.flatnonzero(((v[:-1]<lo)&(v[1:]>=lo))|((v[:-1]<hi)&(v[1:]>=hi))|((v[:-1]>=lo)&(v[1:]<lo))):
        if v[i+1]<lo: start=None
        elif v[i]<lo:
            start=np.interp(lo,v[i:i+2],t[i:i+2])
        elif start is not None:
            elapsed=np.interp(hi,v[i:i+2],t[i:i+2])-start
            best=elapsed if best is None else min(best,elapsed)
            start=None
    return "—" if best is None else f"{best:.3f} s"

def figure(key,active,reference,axis,distance):
    lap,ref=LAPS[active],LAPS[reference]
    pair=[(lap,f"Lap {active+1:02}",A,"solid"),(ref,f"Ref. {reference+1:02}",B,"dot")]
    f=go.Figure()
    subtitle=CATALOG[key][2]
    pos=sample(lap,distance)
    if key in DEFAULTS:
        spec=demo_scatter(key,defaults(key),active,reference)
        f=go.Figure(data=spec["data"],layout=spec["layout"])
    elif key in ANALYSIS:
        f=analysis_figure(key,active,reference,distance)
    elif key=="history":
        f=make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[.66,.34],vertical_spacing=.13)
        for data,name,color,dash in pair:
            f.add_trace(line(data[axis][::10],data["speed"][::10],name,color,dash),row=1,col=1)
        for k,col in [("throttle","#008670"),("brake","#bd524d")]:
            f.add_trace(line(lap[axis][::10],lap[k][::10],CHANNELS[k][0],col),row=2,col=1)
        f.update_yaxes(title_text="km/h",row=1,col=1)
        f.update_yaxes(title_text="%",range=[-4,106],row=2,col=1)
        f.update_xaxes(title_text="Distance (m)" if axis=="d" else "Time (s)",row=2,col=1)
    elif key=="timing":
        x=np.linspace(0,LENGTH,1200)
        diff=np.interp(x,lap["d"],lap["t"])-np.interp(x,ref["d"],ref["t"])
        f.add_trace(line(x,diff,"Active − reference"))
        f.add_hline(y=0,line_dash="dot",line_color="#888888")
        for i,bound in enumerate(SPLITS[1:]):
            at=bound*LENGTH
            f.add_trace(marked([at],[np.interp(at,x,diff)],f"End S{i+1}",B))
        axes(f,"Distance (m)","Cumulative delta (s)")
    elif key=="outing":
        offset=0
        for i,data in enumerate(LAPS):
            f.add_trace(line(offset+data["t"][::12],data["speed"][::12],f"Lap {i+1:02}",[A,B,"#008670","#9368ba"][i]))
            offset+=data["t"][-1]
        axes(f,"Session time (s)","Speed (km/h)")
    elif key=="colour":
        f.add_trace(go.Heatmap(x=lap["t"][::10],y=["Speed"],z=[lap["speed"][::10]],colorscale=SCALE,colorbar=dict(title="km/h")))
        f.update_xaxes(title_text="Time (s)")
    elif key in ("hist","susp"):
        for data,name,color,dash in pair:
            val=data["speed"][:-1] if key=="hist" else np.diff(data["damper"][:-1])*RATE
            bins=np.arange(30,246,5) if key=="hist" else np.linspace(-150,150,61)
            counts,edges=np.histogram(val,bins)
            pct=100*counts/len(val)
            if dash=="solid":
                f.add_trace(go.Bar(x=(edges[1:]+edges[:-1])/2,y=pct,name=name,marker_color=color,opacity=.8))
            else: f.add_trace(line((edges[1:]+edges[:-1])/2,pct,name,color,dash))
        axes(f,"Speed (km/h)" if key=="hist" else "Front-left damper velocity (mm/s)","Samples (%)")
    elif key=="fft":
        for data,name,color,dash in pair:
            hz,amp=spectrum(data)
            f.add_trace(line(hz,amp,name,color,dash))
        axes(f,"Frequency (Hz)","Amplitude (mm)")
        f.update_xaxes(range=[0,16])
    elif key=="mix":
        for lo,hi,col in [(0,33,A),(33,66,B),(66,101,"#008670")]:
            mask=(lap["throttle"][::5]>=lo)&(lap["throttle"][::5]<hi)
            f.add_trace(go.Scatter(x=lap["rpm"][::5][mask],y=lap["lambda"][::5][mask],name=f"{lo}–{min(hi,100)}% load",
                                   mode="markers",marker=dict(color=col,size=4,opacity=.55)))
        axes(f,"Engine speed (rpm)","Lambda (λ)")
    elif key in ("track","rainbow","pos","gps","race"):
        x,y=position(lap["d"][::8])
        if key=="rainbow":
            f.add_trace(go.Scatter(x=x,y=y,mode="markers",name="Speed",marker=dict(size=8,color=lap["speed"][::8],colorscale=SCALE,showscale=True,colorbar=dict(title="km/h"))))
        elif key=="gps":
            for data,name,color,dash in pair:
                x,y=position(data["d"][::8])
                variation=4*np.sin(data["d"][::8]/85+.04*data["lat"][::8])+3*data["lat"][::8]
                f.add_trace(line(x+variation,y-variation,name,color,dash))
            axes(f,"East (m)","North (m)")
        else:
            f.add_trace(line(x,y,"Track","#83919d"))
            if key=="track":
                for j,(a,b) in enumerate(zip(SPLITS[:-1],SPLITS[1:])):
                    idx=np.flatnonzero((lap["d"]>=a*LENGTH)&(lap["d"]<=b*LENGTH))
                    m=idx[lap["speed"][idx].argmin()]
                    px,py=position(lap["d"][m])
                    f.add_trace(marked([px],[py],f"S{j+1} · {lap['speed'][m]:.0f} km/h",A))
                    f.add_annotation(x=px,y=py,text=f"S{j+1}",showarrow=True,ay=-25,ax=14)
            else:
                drivers=pair if key=="pos" else [(data,f"Car {i+1:02}",[A,B,"#008670","#9368ba"][i],"solid") for i,data in enumerate(LAPS)]
                for i,(data,name,color,_) in enumerate(drivers):
                    elapsed=pos["t"] if key=="pos" else (pos["t"]+i*4)%data["t"][-1]
                    px,py=position(np.interp(elapsed,data["t"],data["d"]))
                    f.add_trace(marked([px],[py],name,color))
        f.update_yaxes(scaleanchor="x",scaleratio=1)
        if key!="gps":
            f.update_xaxes(visible=False); f.update_yaxes(visible=False)
    elif key in ("sectors","stats","accel","status"):
        if key=="sectors":
            cols=["Section",pair[0][1],pair[1][1],"Delta"]
            a,b=split_times(lap),split_times(ref)
            rows=[[s,clock(v),clock(r),f"{v-r:+.3f} s"] for s,v,r in zip(["S1","S2","S3","Lap"],[*a,a.sum()],[*b,b.sum()])]
        elif key=="stats":
            cols=["Channel","Unit","Min","Mean","Max"]
            rows=[[label,unit or "—",*[f"{v:.2f}" for v in (lap[k][:-1].min(),lap[k][:-1].mean(),lap[k][:-1].max())]] for k,(label,unit) in CHANNELS.items()]
        elif key=="accel":
            cols=["Range",pair[0][1],pair[1][1]]
            rows=[[f"{lo} → {hi} km/h",acceleration(lap,lo,hi),acceleration(ref,lo,hi)] for lo,hi in [(100,140),(120,160),(140,180),(160,200)]]
        else:
            cols=["Signal","Value","Status"]
            rows=[[label,f"{pos[k]:.2f} {unit}","Available" if np.isfinite(pos[k]) else "Missing"] for k,(label,unit) in CHANNELS.items()]
        return dict(table=dict(columns=cols,rows=rows),description=subtitle)
    elif key=="gauges":
        return dict(gauge=pos,description=subtitle)
    f.update_layout(template="none",margin=dict(l=54,r=24,t=16,b=48),showlegend=False,
                    hovermode="closest",dragmode="zoom",bargap=.12)
    return dict(figure=f,description=subtitle)
