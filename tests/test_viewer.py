import tempfile
import unittest
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from data_viewer.charts import CATALOG, figure
from data_viewer.analysis_plots import frequency_response, interval_mean
from data_viewer.demo_data import demo_samples
from data_viewer.logstore import prepare
from data_viewer.telemetry import LAPS, LENGTH, split_times, spectrum
from viewer import html_arrays

class TelemetryTests(unittest.TestCase):
    def test_html_series_preserve_coordinates_and_colour_values(self):
        for key in ("scatter","steer-throttle","hist","history","colour","rainbow"):
            fig=figure(key,1,2,"d",0)["figure"]
            series=html_arrays(fig.to_plotly_json())["data"]
            for raw, exported in zip(fig.data,series,strict=True):
                np.testing.assert_array_equal(exported["x"],raw.x)
                np.testing.assert_array_equal(exported["y"],raw.y)
                if key=="colour":
                    np.testing.assert_array_equal(exported["z"],raw.z)
                if key=="rainbow":
                    np.testing.assert_array_equal(exported["marker"]["color"],raw.marker.color)

    def test_demo_samples_are_original_and_aligned(self):
        samples = demo_samples()
        self.assertEqual((samples["t"][0], samples["t"][-1]), (0, 20))
        np.testing.assert_allclose(np.diff(samples["t"]), 0.01)
        for name in ("speed", "brake"):
            np.testing.assert_array_equal(samples[name], LAPS[1][name][:len(samples["t"])])

    def test_finish_and_fft(self):
        for lap in LAPS:
            self.assertAlmostEqual(lap["d"][-1], LENGTH)
            self.assertAlmostEqual(split_times(lap).sum(),lap["t"][-1])
            hz,amp=spectrum(lap)
            self.assertAlmostEqual(hz[np.argmax(amp)],2.4,delta=.025)
        fig=figure("timing",1,2,"d",0)["figure"]
        self.assertAlmostEqual(fig.data[0].y[-1],LAPS[1]["t"][-1]-LAPS[2]["t"][-1])

    def test_all_worksheets(self):
        for key in CATALOG:
            with self.subTest(key=key):
                self.assertTrue({"figure","table","gauge"} & figure(key,1,2,"d",0).keys())

    def test_interval_average_includes_right_edge_and_leaves_empty_bin(self):
        x, mean = interval_mean([0,1,4,6], [1,3,10,20], np.array([0,2,4,6]))
        np.testing.assert_equal(x, [1,3,5])
        np.testing.assert_allclose(mean, [2,np.nan,15], equal_nan=True)

    def test_frequency_response_recovers_gain_and_phase(self):
        x = np.random.default_rng(21).normal(size=8192)
        hz, h = frequency_response(x, np.r_[0., 2*x[:-1]])
        # Finite Hann windows estimate the one-sample delay to within 1% of the gain.
        np.testing.assert_allclose(h, 2*np.exp(-2j*np.pi*hz/100), atol=.02, rtol=0)
        _, flat = frequency_response(x, x*2)
        np.testing.assert_allclose(flat, 2, atol=1e-12, rtol=0)
        _, undefined = frequency_response(x*0, x)
        self.assertTrue(np.isnan(undefined).all())

    def test_distributions_and_report_use_all_samples(self):
        for key in ("hist-colour", "susp-zones", "susp-four"):
            for trace in figure(key,1,2,"d",0)["figure"].data:
                self.assertAlmostEqual(sum(trace.y),100)
        sector_data = figure("sector-chart",1,2,"d",0)["figure"].data
        np.testing.assert_allclose(np.array([s.y for s in sector_data]).sum(axis=0),[lap["t"][-1] for lap in LAPS])
        density = figure("scatter-density",1,2,"d",0)["figure"].data[0]
        lap = LAPS[1]
        counts, xe, ye = np.histogram2d(lap["lat"][:-1], lap["long"][:-1], bins=48)
        index = (np.searchsorted(xe[1:-1], density.x, side="right"), np.searchsorted(ye[1:-1], density.y, side="right"))
        np.testing.assert_array_equal(density.marker.color, counts[index])

    def test_bits_reconstruct_original_word_and_maps_share_scale(self):
        lap = LAPS[1]
        data = figure("bits",1,2,"d",0)["figure"].data
        expected = [lap["brake"]>5, lap["throttle"]>=95, abs(lap["lat"])>.5]
        for trace, flags in zip(data,expected,strict=True):
            idx = np.searchsorted(trace.x,lap["t"],side="right")-1
            np.testing.assert_array_equal(trace.y[idx],flags)
        compare = figure("rainbow-compare",1,2,"d",800)["figure"]
        a, b = compare.data[0].marker, compare.data[2].marker
        self.assertEqual((a.cmin,a.cmax),(b.cmin,b.cmax))
        self.assertLess(compare.layout.xaxis.domain[1],compare.layout.xaxis2.domain[0])
        for key in ("telemetry-gps","telemetry-position"):
            start = figure(key,1,2,"d",0)["figure"].data[-1]
            moved = figure(key,1,2,"d",800)["figure"].data[-1]
            self.assertNotEqual((start.x[0],start.y[0]),(moved.x[0],moved.y[0]))

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cache=self.root/"cache"
        self.source=self.root/"input.csv"

    def test_cache_reuse_invalidation_and_atomic_failure(self):
        self.source.write_text("time_s,v\n0,1\n1,3\n",encoding="utf8")
        first=prepare(self.source,self.cache)
        again=prepare(self.source,self.cache)
        self.assertEqual(first.parquet,again.parquet)
        self.source.write_text("time_s,v\n0,1\n1,4\n2,5\n",encoding="utf8")
        current=prepare(self.source,self.cache)
        self.assertNotEqual(first.parquet,current.parquet)
        self.assertEqual(current.window("v",0,1)["y"],[1,4])
        self.source.write_text("time_s,v\n1,1\n0,3\n",encoding="utf8")
        with self.assertRaises(ValueError): prepare(self.source,self.cache)
        self.assertFalse(list(self.cache.glob("*.part")))
        self.assertEqual(len(list(self.cache.glob("*.parquet"))),2)

    def test_window_preserves_extrema_gaps_and_skips_groups(self):
        t=np.arange(2000,dtype=float);y=np.zeros(len(t));y[501]=111;y[1400]=-111;y[137]=np.nan
        path=self.root/"l.parquet";pq.write_table(pa.table({"time_s":t,"v":y}),path,row_group_size=100)
        log=prepare(path,self.cache)
        all_rows=log.window("v",0,1999,32)
        self.assertLessEqual(len(all_rows["x"]),4*32)
        for x,target in [(501,111),(1400,-111)]: self.assertIn((x,target),zip(all_rows["x"],all_rows["y"]))
        self.assertIn(None,all_rows["y"])
        zoom=log.window("v",499,502)
        self.assertEqual(zoom["groups"],2)
        self.assertEqual(zoom["y"],[0,0,111,0])
        self.assertEqual(log.window("v",500,500)["x"],[500])
        self.assertEqual(log.window("v",2001,2010)["x"],[])

    def test_parquet_without_statistics_and_unsorted_time(self):
        path=self.root/"p.parquet"
        pq.write_table(pa.table({"time_s":[3.,1.,2.],"v":[8.,9.,None]}),path,write_statistics=False)
        log=prepare(path,self.cache)
        self.assertEqual((log.start,log.end),(1,3))
        self.assertEqual(log.window("v",1,3)["y"],[9,None,8])

if __name__=="__main__": unittest.main()
