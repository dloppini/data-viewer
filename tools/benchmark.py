"""Reproducible benchmark comparing the alternative loading engines."""
import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NAMES=["time_s","speed_kmh","throttle_pct","brake_pct","rpm","ay_g","ax_g",
       "damper_mm","temp_c","volts","load_pct","pressure_bar"]

def generate(path,rows):
    import numpy as np
    import pyarrow as pa
    import pyarrow.csv as csv
    rng=np.random.default_rng(27)
    with path.open("wb") as out:
        writer=None
        try:
            for i in range(0,rows,65536):
                t=np.arange(i,min(rows,i+65536))/100
                arrays=[t]+[np.round(50+j*3+25*np.sin(t/(j+1))+rng.normal(0,.3,len(t)),3) for j in range(1,len(NAMES))]
                table=pa.table(dict(zip(NAMES,arrays)))
                if writer is None: writer=csv.CSVWriter(out,table.schema)
                writer.write_table(table)
        finally:
            if writer: writer.close()

def worker(mode,folder):
    import psutil
    base=Path(folder)
    source=base/"session.csv"
    dest=base/(mode+".parquet")
    stats={}
    if mode=="arrow":
        import pyarrow as pa
        import pyarrow.csv as pcsv
        import pyarrow.parquet as pq
        schema=pa.schema([(k,pa.float64()) for k in NAMES])
        begin=time.perf_counter()
        with pcsv.open_csv(source,read_options=pcsv.ReadOptions(block_size=4*1024*1024),
                convert_options=pcsv.ConvertOptions(column_types=schema)) as reader, pq.ParquetWriter(
                dest,schema,compression="zstd",compression_level=1,use_dictionary=False) as writer:
            for batch in reader: writer.write_batch(batch,row_group_size=65536)
    elif mode=="polars":
        import polars as pl
        begin=time.perf_counter()
        pl.scan_csv(source,schema={k:pl.Float64 for k in NAMES}).sink_parquet(dest,
            compression="zstd",compression_level=1,row_group_size=65536)
    elif mode=="duckdb":
        import duckdb
        con=duckdb.connect()
        schema="{"+",".join("'"+k+"':'DOUBLE'" for k in NAMES)+"}"
        begin=time.perf_counter()
        con.execute("COPY (SELECT * FROM read_csv(?,columns="+schema+",header=true)) TO '"+dest.as_posix().replace("'","''")+"' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 65536)",[str(source)])
        con.close()
    else:
        from data_viewer.logstore import prepare
        begin=time.perf_counter()
        log=prepare(source,base/"cache")
        stats["first_s"]=time.perf_counter()-begin
        begin=time.perf_counter();log=prepare(source,base/"cache")
        stats["reopen_ms"]=(time.perf_counter()-begin)*1000
        for tag,a,b in [("all",log.start,log.end),("zoom",log.end/2,log.end/2+30)]:
            timings=[]
            for i in range(5):
                t=time.perf_counter();window=log.window("speed_kmh",a,b,800)
                timings.append((time.perf_counter()-t)*1000)
            stats[tag]=dict(median_ms=statistics.median(timings),first_ms=timings[0],rows=window["rows"],
                            groups=window["groups"],points=len(window["x"]),json_bytes=len(json.dumps(window).encode()))
        stats.update(groups=len(log.groups),rows=log.rows,cache_bytes=log.parquet.stat().st_size)
    if mode!="pipeline":
        stats.update(seconds=time.perf_counter()-begin,bytes=dest.stat().st_size)
        import pyarrow.parquet as pq
        stats["rows"]=pq.read_metadata(dest).num_rows
    mem=psutil.Process().memory_info()
    stats["peak_working_set_mib"]=round(getattr(mem,"peak_wset",mem.rss)/2**20,1)
    print(json.dumps(stats))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--rows",type=int,default=5_000_000)
    p.add_argument("--worker",choices=["arrow","polars","duckdb","pipeline"])
    p.add_argument("--folder")
    p.add_argument("--output",type=Path,default=ROOT / "documentation/research/benchmark.json")
    args=p.parse_args()
    if args.worker:
        worker(args.worker,args.folder);return
    import importlib.metadata as md
    import psutil
    result=dict(rows=args.rows,columns=len(NAMES),python=platform.python_version(),os=platform.platform(),
                cpu=os.getenv("PROCESSOR_IDENTIFIER"),threads=os.cpu_count(),ram_gib=round(psutil.virtual_memory().total/2**30,1),
                versions={k:md.version(k) for k in ("numpy","pyarrow","polars","duckdb","psutil")},measurements={})
    with tempfile.TemporaryDirectory(prefix="data-viewer-bench-") as folder:
        source=Path(folder)/"session.csv";generate(source,args.rows)
        result["csv_bytes"]=source.stat().st_size
        for mode in ["arrow","polars","duckdb","pipeline"]:
            data=subprocess.check_output([sys.executable,__file__,"--worker",mode,"--folder",folder],text=True)
            stats=json.loads(data);assert stats["rows"]==args.rows
            result["measurements"][mode]=stats
            print(mode,stats,flush=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
