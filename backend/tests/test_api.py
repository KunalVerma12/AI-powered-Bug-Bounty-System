import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.app.models.schemas import ScanApiResponse, ScanCounts, ScanFinding
from backend.app.services.auth import user_repository
from backend.app.services.repository import scan_repository


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        scan_repository.clear_for_tests()
        user_repository.clear_for_tests()

    def test_healthcheck(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_scan_flow(self) -> None:
        register_response = self.client.post(
            "/auth/register",
            json={"username": "tester", "email": "tester@example.com", "password": "hunter123"},
        )
        self.assertEqual(register_response.status_code, 200)
        auth_payload = register_response.json()
        token = auth_payload["access_token"]
        user_id = auth_payload["user"]["user_id"]

        fake_scan = ScanApiResponse(
            scan_id="scan-123",
            user_id=user_id,
            repo="https://github.com/example/bug-demo",
            repo_name="bug-demo",
            status="completed",
            scanned_at=datetime.now(timezone.utc),
            progress=100,
            summary=ScanCounts(total=1, critical=0, high=1, medium=0, low=0),
            vulnerabilities=[
                ScanFinding(
                    id="finding-1",
                    title="subprocess-shell-true",
                    severity="High",
                    description="Unsafe subprocess shell usage",
                    file="app.py",
                    line=23,
                    tool="bandit",
                    fix="Avoid shell=True",
                    explanation="Bandit flagged subprocess with shell=True.",
                    snippet="subprocess.run(cmd, shell=True)",
                    tech_context="Python Backend",
                    what_happened="A shell command is built in a risky way.",
                    why_it_matters="An attacker may be able to inject extra commands.",
                    how_to_fix="Pass arguments as a list and remove shell=True.",
                    example_fix='subprocess.run(["git", "status"], check=True)',
                )
            ],
            agent_steps=[],
            timeline=["Repository queued."],
        )

        scan_repository.save_scan(fake_scan)
        with patch("backend.app.routes.scans.scan_job_service.submit_scan", return_value=fake_scan):
            create_response = self.client.post(
                "/scan",
                json={"repo_url": "https://github.com/example/bug-demo"},
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(create_response.status_code, 200)
            scan = create_response.json()
            self.assertEqual(scan["repo_name"], "bug-demo")
            self.assertEqual(scan["status"], "completed")
            self.assertGreaterEqual(scan["summary"]["total"], 1)

            results_response = self.client.get("/results", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(results_response.status_code, 200)
            self.assertGreaterEqual(len(results_response.json()), 1)

            detail_response = self.client.get(f"/results/{scan['scan_id']}", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(detail_response.status_code, 200)
            self.assertGreaterEqual(len(detail_response.json()["vulnerabilities"]), 1)

            update_response = self.client.patch(
                f"/results/{scan['scan_id']}/findings/finding-1",
                json={"review_status": "Reviewed"},
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(update_response.status_code, 200)
            self.assertEqual(update_response.json()["vulnerabilities"][0]["review_status"], "Reviewed")

            report_response = self.client.get(
                f"/results/{scan['scan_id']}/report?format=markdown",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(report_response.status_code, 200)
            self.assertIn("Scan Report", report_response.text)

            pdf_report_response = self.client.get(
                f"/results/{scan['scan_id']}/report?format=pdf",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(pdf_report_response.status_code, 200)
            self.assertEqual(pdf_report_response.headers["content-type"], "application/pdf")
            self.assertTrue(pdf_report_response.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
