from __future__ import annotations

from datetime import datetime, timezone
from threading import Thread
from uuid import uuid4

try:
    from backend.app.agents.pipeline import default_agent_steps, progress_steps, queued_agent_steps, run_pipeline
    from backend.app.models.schemas import AgentStep, RepoAnalysis, RepoRecon, ScanApiResponse, ScanCounts, ScanPreset, ScanStatus
    from backend.app.services.repository import scan_repository
    from backend.app.services.scanner import ScanError, extract_repo_name, validate_repo_url
except ModuleNotFoundError:
    from app.agents.pipeline import default_agent_steps, progress_steps, queued_agent_steps, run_pipeline
    from app.models.schemas import AgentStep, RepoAnalysis, RepoRecon, ScanApiResponse, ScanCounts, ScanPreset, ScanStatus
    from app.services.repository import scan_repository
    from app.services.scanner import ScanError, extract_repo_name, validate_repo_url


class ScanJobService:
    def __init__(self) -> None:
        self._threads: dict[str, Thread] = {}

    def submit_scan(self, repo_url: str, user_id: str, preset: ScanPreset, clone_url: str | None = None) -> ScanApiResponse:
        validate_repo_url(repo_url)
        scan_id = str(uuid4())
        repo_name = extract_repo_name(repo_url)
        placeholder = ScanApiResponse(
            scan_id=scan_id,
            user_id=user_id,
            repo=repo_url,
            repo_name=repo_name,
            preset=preset,
            status=ScanStatus.queued.value,
            scanned_at=datetime.now(timezone.utc),
            progress=0,
            summary=ScanCounts(),
            vulnerabilities=[],
            agent_steps=queued_agent_steps(),
            timeline=[f"Scan queued with the {preset.value} preset and waiting for a worker slot."],
            recon=RepoRecon(),
            repo_analysis=RepoAnalysis(),
            analysis_mode="background-worker",
            risk_assessment=f"Scan queued with the {preset.value} preset. The worker will clone the repository and start analysis shortly.",
            error_message="",
        )
        scan_repository.save_scan(placeholder)

        thread = Thread(target=self._run_job, args=(scan_id, repo_url, user_id, preset, clone_url), daemon=True)
        self._threads[scan_id] = thread
        thread.start()
        return placeholder

    def _run_job(self, scan_id: str, repo_url: str, user_id: str, preset: ScanPreset, clone_url: str | None = None) -> None:
        try:
            self._update_progress(
                scan_id,
                progress=12,
                summary=f"Repository clone started in the background worker using the {preset.value} preset.",
                timeline_entry=f"Background worker started cloning the repository with the {preset.value} preset.",
            )
            result = run_pipeline(
                repo_url,
                user_id,
                preset=preset,
                scan_id=scan_id,
                progress_callback=lambda progress, message: self._update_progress(scan_id, progress, message, message),
                clone_url=clone_url,
            )
            scan_repository.save_scan(result)
        except ScanError as exc:
            self._mark_failed(scan_id, str(exc))
        except Exception:
            self._mark_failed(scan_id, "The scan worker hit an unexpected error while analyzing the repository.")
        finally:
            self._threads.pop(scan_id, None)

    def _update_progress(self, scan_id: str, progress: int, summary: str, timeline_entry: str | None = None) -> None:
        current_scan = scan_repository.update_scan(
            scan_id,
            status=ScanStatus.running.value,
            progress=progress,
            agent_steps=progress_steps(progress, default_agent_steps()),
            risk_assessment=summary,
            analysis_mode="background-worker",
        )
        if timeline_entry and timeline_entry not in current_scan.timeline:
            scan_repository.update_scan(scan_id, timeline=[*current_scan.timeline, timeline_entry])

    def _mark_failed(self, scan_id: str, message: str) -> None:
        current = scan_repository.update_scan(
            scan_id,
            status=ScanStatus.failed.value,
            progress=100,
            error_message=message,
            risk_assessment=message,
            agent_steps=[step.model_copy(update={"status": ScanStatus.failed, "summary": message, "progress": step.progress if step.progress else 0}) for step in progress_steps(20, default_agent_steps())],
        )
        scan_repository.save_scan(current)
        if message not in current.timeline:
            scan_repository.update_scan(scan_id, timeline=[*current.timeline, message])


scan_job_service = ScanJobService()
