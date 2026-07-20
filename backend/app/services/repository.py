from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from typing import Any

try:
    from backend.app.models.schemas import DashboardSummary, FindingReviewStatus, ScanApiResponse, ScanHistoryItem, ScanStatus, Vulnerability
    from backend.app.services.database import get_collection
except ModuleNotFoundError:
    from app.models.schemas import DashboardSummary, FindingReviewStatus, ScanApiResponse, ScanHistoryItem, ScanStatus, Vulnerability
    from app.services.database import get_collection


class ScanRepository:
    def __init__(self) -> None:
        self._scans: dict[str, ScanApiResponse] = {}
        self._lock = Lock()

    def _scans_collection(self):
        return get_collection("scans")

    def _activity_collection(self):
        return get_collection("activity_events")

    def _serialize_scan(self, scan: ScanApiResponse) -> dict[str, Any]:
        return scan.model_dump(mode="json")

    def _deserialize_scan(self, data: dict[str, Any]) -> ScanApiResponse:
        payload = dict(data)
        payload.pop("_id", None)
        return ScanApiResponse.model_validate(payload)

    def _log_activity(self, event_type: str, user_id: str, scan_id: str, metadata: dict[str, Any]) -> None:
        collection = self._activity_collection()
        if collection is None:
            return
        collection.insert_one(
            {
                "event_type": event_type,
                "user_id": user_id,
                "scan_id": scan_id,
                "metadata": metadata,
                "created_at": metadata.get("created_at") or datetime.now(timezone.utc).isoformat(),
            }
        )

    def save_scan(self, scan: ScanApiResponse) -> ScanApiResponse:
        existing = self._scans.get(scan.scan_id)
        with self._lock:
            self._scans[scan.scan_id] = scan
        collection = self._scans_collection()
        if collection is not None:
            collection.replace_one({"scan_id": scan.scan_id}, self._serialize_scan(scan), upsert=True)
        self._log_activity(
            "scan_completed" if scan.status.lower() == ScanStatus.completed.value.lower() else "scan_saved",
            scan.user_id,
            scan.scan_id,
            {"repo_name": scan.repo_name, "status": scan.status, "created_at": scan.scanned_at.isoformat()},
        )
        return scan

    def update_scan(self, scan_id: str, **updates) -> ScanApiResponse:
        with self._lock:
            scan = self._load_scan(scan_id)
            updated_scan = scan.model_copy(update=updates)
            self._scans[scan_id] = updated_scan
        collection = self._scans_collection()
        if collection is not None:
            collection.replace_one({"scan_id": scan_id}, self._serialize_scan(updated_scan), upsert=True)
        return updated_scan

    def list_scans(self, user_id: str) -> list[ScanHistoryItem]:
        collection = self._scans_collection()
        if collection is not None:
            values = [self._deserialize_scan(item) for item in collection.find({"user_id": user_id})]
        else:
            with self._lock:
                values = list(self._scans.values())
            values = [scan for scan in values if scan.user_id == user_id]
        scans = sorted(values, key=lambda item: item.scanned_at, reverse=True)
        return [
            ScanHistoryItem(
                scan_id=scan.scan_id,
                user_id=scan.user_id,
                repo=scan.repo,
                repo_name=scan.repo_name,
                preset=scan.preset,
                status=scan.status,
                scanned_at=scan.scanned_at,
                progress=scan.progress,
                summary=scan.summary,
                analysis_mode=scan.analysis_mode,
                error_message=scan.error_message,
            )
            for scan in scans
        ]

    def get_scan(self, scan_id: str, user_id: str) -> ScanApiResponse:
        scan = self._load_scan(scan_id)
        if scan.user_id != user_id:
            raise KeyError(scan_id)
        return scan

    def all_vulnerabilities(self, user_id: str) -> list[Vulnerability]:
        vulnerabilities: list[Vulnerability] = []
        for scan in self._all_scans_for_user(user_id):
            for finding in scan.vulnerabilities:
                vulnerabilities.append(
                    Vulnerability(
                        id=finding.id,
                        title=finding.title,
                        severity=finding.severity,
                        description=finding.description,
                        file_path=finding.file,
                        line=finding.line,
                        tool=finding.tool,
                        cwe=finding.cwe,
                        repo_name=scan.repo_name,
                        ai_analysis=finding.explanation,
                        fix_suggestion=finding.fix,
                        snippet=finding.snippet,
                        confidence=finding.confidence,
                        cvss_score=finding.cvss_score,
                        exploitability_score=finding.exploitability_score,
                        tags=finding.tags,
                        tech_context=finding.tech_context,
                        ai_analyzed=finding.ai_analyzed,
                        analysis_source=finding.analysis_source,
                        component_owner=finding.component_owner,
                        false_positive_hint=finding.false_positive_hint,
                        cwe_link=finding.cwe_link,
                        attack_surface_tags=finding.attack_surface_tags,
                        review_status=finding.review_status,
                        what_happened=finding.what_happened,
                        why_it_matters=finding.why_it_matters,
                        how_to_fix=finding.how_to_fix,
                        example_fix=finding.example_fix,
                    )
                )
        return vulnerabilities

    def update_finding_status(self, scan_id: str, user_id: str, finding_id: str, review_status: FindingReviewStatus) -> ScanApiResponse:
        with self._lock:
            scan = self._load_scan(scan_id)
            if scan.user_id != user_id:
                raise KeyError(scan_id)

            updated_findings = []
            found = False
            for finding in scan.vulnerabilities:
                if finding.id == finding_id:
                    updated_findings.append(finding.model_copy(update={"review_status": review_status}))
                    found = True
                else:
                    updated_findings.append(finding)

            if not found:
                raise KeyError(finding_id)

            updated_scan = scan.model_copy(update={"vulnerabilities": updated_findings})
            self._scans[scan_id] = updated_scan
        collection = self._scans_collection()
        if collection is not None:
            collection.replace_one({"scan_id": scan_id}, self._serialize_scan(updated_scan), upsert=True)
        self._log_activity(
            "finding_review_status_updated",
            user_id,
            scan_id,
            {"finding_id": finding_id, "review_status": review_status.value, "created_at": updated_scan.scanned_at.isoformat()},
        )
        return updated_scan

    def summary(self, user_id: str) -> DashboardSummary:
        scans = self._all_scans_for_user(user_id)
        findings = [finding for scan in scans for finding in scan.vulnerabilities]
        severity_counter = Counter(finding.severity.value for finding in findings)

        return DashboardSummary(
            total_scans=len(scans),
            running_scans=sum(1 for scan in scans if scan.status.lower() == ScanStatus.running.value.lower()),
            total_vulnerabilities=len(findings),
            critical_vulnerabilities=severity_counter.get("Critical", 0),
            average_confidence=round(sum(finding.confidence for finding in findings) / len(findings), 2) if findings else 0.0,
            severity_breakdown={
                severity: severity_counter.get(severity, 0)
                for severity in ["Low", "Medium", "High", "Critical"]
            },
        )

    def _all_scans_for_user(self, user_id: str) -> list[ScanApiResponse]:
        collection = self._scans_collection()
        if collection is not None:
            return [self._deserialize_scan(item) for item in collection.find({"user_id": user_id})]
        with self._lock:
            return [scan for scan in self._scans.values() if scan.user_id == user_id]

    def _load_scan(self, scan_id: str) -> ScanApiResponse:
        if scan_id in self._scans:
            return self._scans[scan_id]
        collection = self._scans_collection()
        if collection is not None:
            payload = collection.find_one({"scan_id": scan_id})
            if payload is None:
                raise KeyError(scan_id)
            scan = self._deserialize_scan(payload)
            self._scans[scan_id] = scan
            return scan
        raise KeyError(scan_id)

    def clear_for_tests(self) -> None:
        with self._lock:
            self._scans.clear()
        collection = self._scans_collection()
        if collection is not None:
            collection.delete_many({})
        activity = self._activity_collection()
        if activity is not None:
            activity.delete_many({})


scan_repository = ScanRepository()
