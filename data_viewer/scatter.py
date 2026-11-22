"""Python-side channel selection, sample gating and bounded XY projections."""
import operator
import hashlib

import numpy as np
import pyarrow.parquet as pq

from .telemetry import CHANNELS, LAPS
from .logstore import BATCH, TIME, stamp
from .plot_primitives import A, B, SCALE

LIMIT = 3200  # Per source, after gating.
OPS = {"<":operator.lt, "<=":operator.le, ">":operator.gt, ">=":operator.ge,
       "==":operator.eq, "!=":operator.ne}
LABELS = {**CHANNELS, "t":("Lap time","s"), "d":("Lap distance","m")}
DEFAULTS = {
    "scatter":("lat","long"), "steer-throttle":("steer","throttle"),
    "scatter-density":("lat","long"), "scatter-colour":("steer","throttle"),
    "scatter-size":("lat","long"), "scatter-gate":("lat","long"),
    "scatter-average":("throttle","lambda"), "scatter-linear":("throttle","lambda"),
    "scatter-polynomial":("steer","speed")
}

def defaults(key):
    x,y = DEFAULTS[key]
    gates = [{"channel":"brake","op":">","value":10}] if key=="scatter-gate" else []
    return dict(x=x,y=y,gates=gates,colour="speed" if key=="scatter-colour" else "",
                size="brake" if key=="scatter-size" else "")

def title(labels, key):
    name, unit = labels[key]
    return f"{name} ({unit})" if unit else name

def validate(query, labels):
    if not isinstance(query,dict) or query.keys()-{"x","y","gates","colour","size"}:
        raise ValueError("Invalid scatter query.")
    for key in ("x","y","colour","size"):
        value=query.get(key,"")
        if key in ("colour","size") and value=="": continue
        if not isinstance(value,str) or value not in labels: raise ValueError(f"Unknown {key} channel.")
    gates=query.get("gates",[])
    if not isinstance(gates,list) or len(gates)>12: raise ValueError("Use up to 12 gates.")
    for g in gates:
        if not isinstance(g,dict) or not isinstance(g.get("channel"),str) or g["channel"] not in labels:
            raise ValueError("Unknown gate channel.")
        if not isinstance(g.get("op"),str) or g["op"] not in OPS or type(g.get("value")) not in (int,float) or not np.isfinite(float(g["value"])):
            raise ValueError("Each gate needs a comparison and a finite numeric threshold.")

def channels(query):
    return list(dict.fromkeys(k for k in [query["x"],query["y"],query.get("colour"),
        query.get("size"),*(g["channel"] for g in query.get("gates",[]))] if k))

def eligible(data, query):
    mask=np.isfinite(data[query["x"]]) & np.isfinite(data[query["y"]])
    for key in ("colour","size"):
        if query.get(key): mask &= np.isfinite(data[query[key]])
    for gate in query.get("gates",[]):
        values=data[gate["channel"]]
        mask &= np.isfinite(values) & OPS[gate["op"]](values,gate["value"])
    return mask

def priorities(ids):
    # Deterministic hash priorities keep the same random sample across batch boundaries.
    h=ids.astype(np.uint64)+np.uint64(0x9e3779b97f4a7c15)
    h=(h^(h>>30))*np.uint64(0xbf58476d1ce4e5b9)
    h=(h^(h>>27))*np.uint64(0x94d049bb133111eb)
    return h^(h>>31)

def sample_positions(ids):
    if len(ids)<=LIMIT: return np.arange(len(ids))
    return np.sort(np.argpartition(priorities(ids),LIMIT-1)[:LIMIT])

def trace(data, ids, positions, query, labels, source, name, colour, time_key):
    take=lambda k:data[k][positions]
    marker=dict(color=colour,size=4)
    meta=dict(source=source,time=take(time_key).tolist())
    if "d" in data and source.startswith("lap:"): meta["distance"]=take("d").tolist()
    if query.get("colour"):
        key=query["colour"]
        marker.update(color=take(key).tolist(),colorscale=SCALE,colorbar=dict(title=dict(text=title(labels,key))))
    if query.get("size"):
        key=query["size"]; values=take(key)
        # Radius grows with absolute channel magnitude. The pick readout retains the original units.
        maximum=np.max(abs(data[key]),initial=0) or 1
        marker["size"]=np.sqrt(9+160*np.abs(values)/maximum).tolist()
        meta["pick"]=title(labels,key)
    result=dict(x=take(query["x"]).tolist(),y=take(query["y"]).tolist(),ids=ids[positions].tolist(),
                name=name, mode="markers",type="scatter",marker=marker,meta=meta)
    if query.get("size"): result["customdata"]=values.tolist()
    return result

def layout(query, labels):
    return {axis+"axis":dict(title=dict(text=title(labels,query[axis]))) for axis in ("x","y")}

def demo_scatter(key, query, active, reference):
    from .analysis_plots import interval_mean
    validate(query,LABELS)
    if key not in DEFAULTS or not all(0<=i<len(LAPS) for i in (active,reference)): raise ValueError("Invalid scatter selection.")
    sources=[(active,f"Lap {active+1:02}",A)]
    if key=="scatter" and reference!=active: sources.insert(0,(reference,f"Ref. {reference+1:02}",B))
    series=[]; total=0
    for index,name,ink in sources:
        lap=LAPS[index]; indices=np.flatnonzero(eligible(lap,query))
        if key.startswith("scatter-"): indices=indices[indices<len(lap["t"])-1]
        keys=set(channels(query))|{"t","d"}
        data={k:lap[k][indices] for k in keys}
        x,y=data[query["x"]],data[query["y"]]
        pick=sample_positions(indices)
        dots=trace(data,indices,pick,query,LABELS,f"lap:{index}",name,ink,"t")
        series.append(dots); total+=len(indices)
        if not len(indices): continue
        if key=="scatter-density":
            counts,xe,ye=np.histogram2d(x,y,bins=48)
            ix=np.searchsorted(xe[1:-1],x[pick],side="right")
            iy=np.searchsorted(ye[1:-1],y[pick],side="right")
            dots["marker"].update(color=counts[ix,iy].tolist(),colorscale=SCALE,colorbar=dict(title=dict(text="samples/cell")))
        elif key in ("scatter-average","scatter-linear","scatter-polynomial"):
            degree=2 if key=="scatter-polynomial" else 1
            if len(np.unique(x))<=degree: continue
            if key=="scatter-average":
                edges=np.linspace(x.min(),x.max(),21)
                grid,fit=interval_mean(x,y,edges); label="Bin mean"
            else:
                grid=np.linspace(x.min(),x.max(),120)
                fit=np.polynomial.Polynomial.fit(x,y,degree)(grid); label=f"Regression · degree {degree}"
            series.append(dict(x=grid.tolist(),y=[float(v) if np.isfinite(v) else None for v in fit],
                               name=label,mode="lines",type="scatter",line=dict(color=B)))
    return dict(data=series,layout=layout(query,LABELS),matched=total)

def log_scatter(log, query, start, end):
    labels={k:(k,"") for k in log.channels}; labels[TIME]=("Session time","s")
    validate(query,labels)
    if not np.isfinite([start,end]).all() or start>end: raise ValueError("Invalid time window.")
    if stamp(log.parquet)!=log.file_stamp: raise ValueError("The file changed. Reopen the log.")
    keys=list(dict.fromkeys([TIME,*channels(query)]))
    ids=np.empty(0,dtype=np.int64); data={k:np.empty(0) for k in keys}; total=0
    with pq.ParquetFile(log.parquet) as reader:
        offsets=np.r_[0,np.cumsum([reader.metadata.row_group(i).num_rows for i in range(reader.num_row_groups)])]
        for group,lo,hi in log.groups:
            if lo>end or hi<start: continue
            offset=offsets[group]
            for batch in reader.iter_batches(columns=keys,row_groups=[group],batch_size=BATCH):
                arrays={k:batch.column(k).to_numpy(zero_copy_only=False) for k in keys}
                ts=arrays[TIME]
                rows=np.flatnonzero(eligible(arrays,query)&(ts>=start)&(ts<=end))
                new_ids=offset+rows; offset+=len(ts); total+=len(rows)
                if not len(rows): continue
                both=np.r_[ids,new_ids]; pick=sample_positions(both)
                ids=both[pick]
                data={k:np.concatenate((data[k],arrays[k][rows]))[pick] for k in keys}
    source="log:"+hashlib.sha256(repr(log.file_stamp).encode()).hexdigest()[:24]
    points=trace(data,ids,np.arange(len(ids)),query,labels,source,log.source.name,A,TIME)
    return dict(data=[points],layout=layout(query,labels),matched=total)
