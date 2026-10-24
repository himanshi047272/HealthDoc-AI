"""API tests. They need fastapi + httpx; they are skipped (and reported as skipped) when those are not installed."""
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    HAVE = True
except Exception:  # pragma: no cover
    HAVE = False

from app.core.config import FIXTURES, load_settings
from app.tests.helpers import make_pdf


@unittest.skipUnless(HAVE, "fastapi/httpx not installed")
class TestApi(unittest.TestCase):
    def setUp(self):
        from app.main import create_app
        self.tmp = tempfile.TemporaryDirectory()
        self.c = TestClient(create_app(load_settings(data_dir=Path(self.tmp.name), relevance_threshold=0.0)))

    def tearDown(self):
        self.tmp.cleanup()

    def up(self, name="a.pdf", data=None, ctype="application/pdf"):
        return self.c.post("/api/documents", files={"file": (name, data or make_pdf(["The copay is $20 per visit."]), ctype)})

    def wait(self, doc_id):
        import time
        for _ in range(100):
            s = self.c.get(f"/api/documents/{doc_id}/status").json()
            if s["status"] in ("ready", "failed"):
                return s
            time.sleep(0.1)
        self.fail("processing did not finish")

    def test_health_ready_and_system(self):
        self.assertEqual(self.c.get("/api/health").json(), {"status": "ok"})
        self.assertTrue(self.c.get("/api/ready").json()["ready"])
        body = self.c.get("/api/system/status").json()
        self.assertNotIn("api_key", str(body).lower())

    def test_upload_flow_and_delete(self):
        r = self.up(); self.assertEqual(r.status_code, 202)
        did = r.json()["document"]["id"]
        self.assertEqual(self.wait(did)["status"], "ready")
        self.assertEqual(self.c.get(f"/api/documents/{did}/text").json()["pages"][0]["page_no"], 1)
        self.assertEqual(self.c.delete(f"/api/documents/{did}").status_code, 204)
        self.assertEqual(self.c.get(f"/api/documents/{did}").status_code, 404)

    def test_validation_errors_use_consistent_shape(self):
        r = self.up("x.exe", b"MZ", "application/octet-stream")
        self.assertEqual(r.status_code, 415); self.assertIn("message", r.json()["error"])
        self.assertEqual(self.c.post("/api/chat", json={"question": ""}).status_code, 422)
        self.assertEqual(self.c.get("/api/documents?page=0").status_code, 422)

    def test_chat_and_search_with_citation(self):
        did = self.up().json()["document"]["id"]; self.wait(did)
        a = self.c.post("/api/chat", json={"question": "What is the copay per visit?"}).json()
        self.assertFalse(a["abstained"]); self.assertTrue(a["citations"][0]["valid"])
        s = self.c.post("/api/search", json={"query": "copay", "mode": "keyword", "document_ids": [did]}).json()
        self.assertEqual(s["results"][0]["page_no"], 1)

    def test_demo_load_and_eval(self):
        self.assertEqual(self.c.post("/api/demo/load").status_code, 202)
        self.assertGreater(self.c.get("/api/analytics").json()["chunks_indexed"], 0)
        self.assertIsNotNone(self.c.post("/api/evaluation/run").json()["metrics"])
