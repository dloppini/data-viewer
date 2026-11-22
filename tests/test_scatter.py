import tempfile
import unittest
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from data_viewer.logstore import prepare
from data_viewer.scatter import LIMIT, defaults, demo_scatter, log_scatter
from data_viewer.telemetry import LAPS


class ScatterTests(unittest.TestCase):
    def test_row_ids_survive_projection_row_groups_and_invalid_values(self):
        ids=np.arange(48317)
        ts=(ids%71)[::-1].astype(float)
        x=(ids%97).astype(float)
        y=ids%79
        x[::99]=np.nan
        query=dict(x="x",y="y",colour="signal",size="y",gates=[
            dict(channel="signal",op=">=",value=9),dict(channel="y",op="<",value=70)])
        signal=ids%31
        keep=np.flatnonzero(np.isfinite(x)&(ts>=3)&(ts<=61)&(signal>=9)&(y<70))
        table=pa.table(dict(time_s=ts,x=x,y=y,signal=signal))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"r.parquet"
            outputs=[]
            for group_size in (1801,8000):
                pq.write_table(table,path,row_group_size=group_size)
                result=log_scatter(prepare(path),query,3,61)
                self.assertEqual(result["matched"],len(keep))
                trace=result["data"][0]
                selected=np.array(trace["ids"])
                self.assertEqual(len(selected),LIMIT)
                self.assertTrue(np.isin(selected,keep).all())
                np.testing.assert_array_equal(trace["x"],x[selected])
                np.testing.assert_array_equal(trace["meta"]["time"],ts[selected])
                np.testing.assert_array_equal(trace["marker"]["color"],signal[selected])
                np.testing.assert_array_equal(trace["customdata"],y[selected])
                outputs.append(selected)
            np.testing.assert_array_equal(*outputs)
            for bad in ({"op":"?"},{"value":float("nan")},{"channel":"missing"}):
                with self.assertRaises(ValueError):
                    log_scatter(prepare(path),dict(query,gates=[dict(query["gates"][0],**bad)]),0,50)
            empty=log_scatter(prepare(path),dict(query,gates=[dict(channel="x",op=">",value=1000)]),0,61)
            self.assertEqual((empty["matched"],empty["data"][0]["ids"]),(0,[]))

    def test_demo_picks_refer_to_original_lap_and_gate(self):
        q=defaults("scatter")
        q.update(x="speed",y="throttle",gates=[dict(channel="brake",op=">",value=25)])
        fig=demo_scatter("scatter",q,1,2)
        self.assertEqual(fig["matched"],sum((LAPS[i]["brake"]>25).sum() for i in (1,2)))
        for t in fig["data"]:
            lap=LAPS[int(t["meta"]["source"].split(":")[1])]
            ids=t["ids"]
            np.testing.assert_array_equal(t["x"],lap["speed"][ids])
            np.testing.assert_array_equal(t["meta"]["distance"],lap["d"][ids])
            self.assertTrue((lap["brake"][ids]>25).all())
