"""Streaming CSV conversion, atomic Parquet caching and windowed column reads."""
import csv
import hashlib
import os
import tempfile
from pathlib import Path

import numpy as np
import pyarrow as pa
import polars as pl
import pyarrow.parquet as pq

CACHE = Path(__file__).resolve().parents[1] / ".cache"
TIME = "time_s"
BATCH = 65_536


def stamp(path):
    s = path.stat()
    return (str(path), s.st_size, s.st_mtime_ns)


def csv_to_parquet(source, target, progress=lambda _: None):
    with source.open(encoding="utf-8-sig", newline="") as f:
        names = next(csv.reader(f), [])
    if TIME not in names or len(names) < 2 or len(set(names)) != len(names) or not all(names):
        raise ValueError("Use distinct numeric columns including time_s and at least one channel.")
    frame = pl.scan_csv(source,schema={name:pl.Float64 for name in names},glob=False,
                        null_values=["NA","null","NULL"],low_memory=True)
    frame.sink_parquet(target,compression="zstd",compression_level=1,
                       row_group_size=BATCH,maintain_order=True,engine="streaming")
    # Validate only time, not all the newly written columns; never publish a partial cache.
    last=-np.inf
    with pq.ParquetFile(target) as reader:
        total=reader.metadata.num_rows
        done=0
        for batch in reader.iter_batches(columns=[TIME],batch_size=BATCH):
            t=batch.column(0).to_numpy(zero_copy_only=False)
            if not len(t): continue
            if not np.isfinite(t).all() or t[0]<last or np.any(t[1:]<t[:-1]):
                raise ValueError("Use finite, non-decreasing session times in the time_s column.")
            last=t[-1]
            done+=len(t)
            progress(done/total)
    if last==-np.inf: raise ValueError("The CSV file contains no samples.")


def prepare(path, cache=CACHE, progress=lambda _: None):
    path = Path(path).expanduser().resolve(strict=True)
    before = stamp(path)
    if path.suffix.lower() == ".parquet":
        return Log(path, path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Choose a CSV or Parquet file.")
    cache.mkdir(exist_ok=True, parents=True)
    key = hashlib.sha256(repr(("float64-polars-v1",before)).encode()).hexdigest()
    final = cache / (key+".parquet")
    if not final.exists():
        fd, tmp = tempfile.mkstemp(suffix=".part", dir=cache)
        os.close(fd)
        try:
            csv_to_parquet(path,tmp,progress)
            if stamp(path) != before:
                raise ValueError("The file changed while it was being read. Try again.")
            os.replace(tmp,final)
        finally:
            Path(tmp).unlink(missing_ok=True)
    return Log(path,final)


class Log:
    def __init__(self, source, parquet):
        self.source, self.parquet = source, parquet
        self.file_stamp = stamp(parquet)
        with pq.ParquetFile(parquet) as reader:
            schema = reader.schema_arrow
            numeric = [f.name for f in schema if pa.types.is_floating(f.type) or pa.types.is_integer(f.type)]
            if TIME not in numeric or len(numeric)<2 or len(set(schema.names))!=len(schema.names):
                raise ValueError("The log needs a numeric time_s column and at least one other numeric channel.")
            self.channels = [c for c in numeric if c!=TIME]
            meta = reader.metadata
            self.rows = meta.num_rows
            self.groups = []
            time_col = next(i for i in range(meta.num_columns) if meta.schema.column(i).path==TIME)
            for i in range(meta.num_row_groups):
                rg = meta.row_group(i)
                if not rg.num_rows:
                    continue
                stats = rg.column(time_col).statistics
                if stats and stats.has_min_max and np.isfinite([stats.min,stats.max]).all():
                    lo, hi = float(stats.min), float(stats.max)
                else:
                    lo, hi = np.inf,-np.inf
                    for b in reader.iter_batches(row_groups=[i],columns=[TIME],batch_size=BATCH):
                        t = b.column(0).to_numpy(zero_copy_only=False)
                        t = t[np.isfinite(t)]
                        if len(t): lo,hi = min(lo,float(t.min())),max(hi,float(t.max()))
                if np.isfinite(lo):
                    self.groups.append((i,lo,hi))
            if not self.groups:
                raise ValueError("No samples have a finite time_s value.")
            self.start = min(g[1] for g in self.groups)
            self.end = max(g[2] for g in self.groups)

    def info(self):
        return dict(name=self.source.name,rows=self.rows,channels=self.channels,start=self.start,end=self.end)

    def window(self, channel, start, end, bins=800):
        if stamp(self.parquet) != self.file_stamp:
            raise ValueError("The Parquet file has changed. Reopen the log to continue.")
        if channel not in self.channels or not np.isfinite([start,end]).all() or start>end:
            raise ValueError("Invalid channel or time range.")
        bins = max(16,min(2048,int(bins)))
        selected = [i for i,lo,hi in self.groups if lo<=end and hi>=start]
        low = np.full(bins,np.inf); high = np.full(bins,-np.inf)
        at_low = np.zeros(bins); at_high = np.zeros(bins)
        gaps = np.zeros(bins,dtype=bool)
        raw_t,raw_y = [],[]
        rows = 0
        with pq.ParquetFile(self.parquet) as reader:
            for b in reader.iter_batches(row_groups=selected,columns=[TIME,channel],batch_size=BATCH):
                times,values = (col.to_numpy(zero_copy_only=False) for col in b.columns)
                keep = (times>=start)&(times<=end)
                t,y = times[keep],values[keep]
                rows += len(t)
                if rows<=2*bins:
                    raw_t.extend(t.tolist()); raw_y.extend(y.tolist())
                if not len(t): continue
                bucket = np.clip(((t-start)/(end-start if end>start else 1)*bins).astype(int),0,bins-1)
                valid = np.isfinite(y)
                gaps[bucket[~valid]] = True
                bucket,t,y = bucket[valid],t[valid],y[valid]
                if not len(t): continue
                if np.any(bucket[1:]<bucket[:-1]):
                    order = np.argsort(bucket,kind="stable")
                    bucket,t,y = bucket[order],t[order],y[order]
                # Contiguous runs: at most one merge per touched screen column per batch.
                offsets = np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1,len(t)]
                for a,z in zip(offsets[:-1],offsets[1:]):
                    k = bucket[a]; segment=y[a:z]
                    m=a+segment.argmin(); n=a+segment.argmax()
                    if y[m]<low[k]: low[k],at_low[k]=y[m],t[m]
                    if y[n]>high[k]: high[k],at_high[k]=y[n],t[n]
        if rows<=2*bins:
            order=np.argsort(raw_t,kind="stable")
            x=[raw_t[i] for i in order]
            y=[raw_y[i] if np.isfinite(raw_y[i]) else None for i in order]
        else:
            x,y=[],[]
            for k in range(bins):
                if gaps[k]:
                    # A mixed pixel cannot represent the ordering of every dropout. Break the line.
                    x.append(start+(end-start)*k/bins); y.append(None)
                if low[k]<=high[k]:
                    for t,v in sorted(((at_low[k],low[k]),(at_high[k],high[k]))):
                        x.append(t);y.append(v)
                if gaps[k]:
                    x.append(start+(end-start)*(k+1)/bins);y.append(None)
        return dict(x=x,y=y,rows=rows,groups=len(selected),reduced=rows>2*bins)
