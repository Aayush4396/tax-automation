# -*- coding: utf-8 -*-
"""test_api.py.

FastAPI TestClient integration tests for REST API endpoints:
- Root & Health probes
- Entities router (list, get, validation)
- Pipeline router (validation errors)
- Files router (list, ext validation)
- Diagnostics router
"""

import unittest
from fastapi.testclient import TestClient

from tax_automation.api.main import app


class TestFastAPIEndpoints(unittest.TestCase):
    """Test suite for Tax Automation REST API."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_and_health(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "healthy")

        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_list_entities(self):
        r = self.client.get("/entities")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertIn("aayush", data)

    def test_get_entity_found(self):
        r = self.client.get("/entities/aayush")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["entity_id"], "aayush")
        self.assertIn("display_name", data)
        self.assertIn("accounts", data)

    def test_get_entity_not_found(self):
        r = self.client.get("/entities/nonexistent_xyz")
        self.assertEqual(r.status_code, 404)

    def test_list_files(self):
        r = self.client.get("/files/aayush/FY26/list")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["entity_id"], "aayush")
        self.assertIn("files", data)

    def test_file_upload_unsupported_ext(self):
        files = {
            "file": (
                "test.exe",
                b"malicious binary content",
                "application/octet-stream",
            )
        }
        r = self.client.post("/files/aayush/FY26/upload", files=files)
        self.assertEqual(r.status_code, 415)

    def test_pipeline_validation_error(self):
        # Invalid FY format (must start with FY)
        r = self.client.post("/pipeline/aayush/2026/consolidate")
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
