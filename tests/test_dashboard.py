"""Exercise the public workspace routes, guide downloads and optional desktop action."""
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import viewer


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), viewer.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def request(self, path, method="GET", headers=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            conn.request(method, path, headers=headers or {})
            res = conn.getresponse()
            return res.status, res.getheader("Location"), res.read()
        finally:
            conn.close()

    def test_manual_and_workbook_routes(self):
        for path, file in [("/", "documentation/dashboard.html"),
                           ("/documentation/Data%20Viewer%20Manual.pdf", "documentation/Data Viewer Manual.pdf"),
                           ("/documentation/manual.md", "documentation/manual.md"),
                           ("/workbook", "web/index.html")]:
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertEqual(body, (viewer.ROOT / file).read_bytes())
        for old, new in [("/?view=scatter", "/workbook?view=scatter"), ("/architecture", "/#map")]:
            self.assertEqual(self.request(old)[:2], (302, new))

    def test_qt_action(self):
        path = "/api/qt-example"
        headers = {"X-Viewer-Token": viewer.TOKEN}
        self.assertEqual(self.request(path, "POST")[0], 403)
        with patch.object(viewer.importlib.util, "find_spec", return_value=None):
            self.assertEqual(self.request(path, "POST", headers)[0], 409)
        with (patch.object(viewer.importlib.util, "find_spec", return_value=True),
              patch.object(viewer, "QT_PROCESS", None), patch.object(viewer.subprocess, "Popen") as launch):
            launch.return_value.poll.return_value = None
            self.assertEqual(self.request(path, "POST", headers)[0], 202)
            status, _, body = self.request(path, "POST", headers)
            self.assertEqual(status, 200)
            self.assertIn("already open", json.loads(body)["message"])
            launch.assert_called_once()
