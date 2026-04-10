from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.jobs import store
from app.main import app
from app.schemas import GeneratedScripts, JobStatus


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_store():
    store._jobs.clear()
    yield
    store._jobs.clear()


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "email_delivery" in body


class TestGenerateEndpoint:
    def _make_payload(self) -> dict:
        return {
            "business_name": "Test Biz",
            "target_audience": "Everyone",
            "pain_points_solutions": [{"pain_point": "problem", "solution": "fix"}],
            "offer": "Free thing",
            "top_stats": ["one hundred customers served"],
            "contact_name": "Jane",
            "contact_email": "jane@example.com",
        }

    @patch("app.main.email_delivery.send_scripts", return_value=False)
    @patch("app.main.format_markdown", return_value="# Output")
    @patch("app.main.run_pipeline")
    def test_generate_queues_job_and_runs_to_completion(
        self, mock_pipeline, mock_format, mock_email, client
    ):
        mock_pipeline.return_value = GeneratedScripts(
            hooks=["h"], meats=["m"], ctas=["c"]
        )

        resp = client.post("/generate", json=self._make_payload())

        assert resp.status_code == 202
        body = resp.json()
        job_id = body["job_id"]
        assert body["business_name"] == "Test Biz"
        assert body["status"] in (JobStatus.PENDING, JobStatus.COMPLETED)
        assert "status_url" in body

        # TestClient runs background tasks synchronously after the response,
        # so the job should be completed by the time we poll.
        status_resp = client.get(f"/jobs/{job_id}")
        assert status_resp.status_code == 200
        status_body = status_resp.json()
        assert status_body["status"] == JobStatus.COMPLETED
        assert status_body["markdown"] == "# Output"
        assert status_body["business_name"] == "Test Biz"
        assert status_body["duration_seconds"] is not None
        mock_pipeline.assert_called_once()
        mock_email.assert_called_once()

    def test_generate_invalid_payload(self, client):
        resp = client.post("/generate", json={"business_name": "incomplete"})
        assert resp.status_code == 422

    @patch("app.main.run_pipeline")
    def test_pipeline_error_marks_job_failed(self, mock_pipeline, client):
        mock_pipeline.side_effect = RuntimeError("Gemini exploded")

        resp = client.post("/generate", json=self._make_payload())
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        status_resp = client.get(f"/jobs/{job_id}")
        assert status_resp.status_code == 200
        body = status_resp.json()
        assert body["status"] == JobStatus.FAILED
        assert "Gemini exploded" in body["error"]
        assert body["markdown"] is None

    def test_get_unknown_job_returns_404(self, client):
        resp = client.get("/jobs/does-not-exist")
        assert resp.status_code == 404
