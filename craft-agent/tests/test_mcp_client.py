"""Tests for tests/mcp_client.py against tests/fake_mcp_server.py."""
import os
import sys
import unittest

from helpers import HERE, CraftHome
from mcp_client import McpClient


class McpClientTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()
        self.c = McpClient([sys.executable, os.path.join(HERE, "fake_mcp_server.py")],
                           env=self.h.env(), timeout=10)

    def tearDown(self):
        self.c.close()
        self.h.cleanup()

    def test_initialize_list_call(self):
        info = self.c.initialize()
        self.assertEqual(info["serverInfo"]["name"], "fake-craft")
        tools = self.c.list_tools()
        self.assertEqual([t["name"] for t in tools], ["touch_path"])
        result = self.c.call("touch_path", {"path": "x.txt"})
        self.assertEqual(result["content"][0]["text"], "touched x.txt")
        with open(os.path.join(self.h.home, "logs", "probe-called")) as f:
            self.assertEqual(f.read(), "x.txt\n")


class MinPdfTest(unittest.TestCase):
    def test_min_pdf_structure(self):
        import tempfile
        from smoke import write_min_pdf
        path = os.path.join(tempfile.mkdtemp(), "t.pdf")
        write_min_pdf(path, 2)
        with open(path, "rb") as f:
            data = f.read()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn(b"/Count 2", data)
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        xref = int(data.rsplit(b"startxref\n", 1)[1].split(b"\n")[0])
        self.assertTrue(data[xref:].startswith(b"xref"))


if __name__ == "__main__":
    unittest.main()
