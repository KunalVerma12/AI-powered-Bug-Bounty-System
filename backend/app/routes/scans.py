from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

try:
    from backend.app.dependencies.auth import get_current_user
    from backend.app.models.schemas import DashboardSummary, FindingStatusUpdate, ScanApiResponse, ScanCreate, ScanHistoryItem, Vulnerability
    from backend.app.services.repository import scan_repository
    from backend.app.services.scanner import ScanError
    from backend.app.services.jobs import scan_job_service
    from backend.app.services.reports import build_json_report, build_markdown_report, build_pdf_report
    from backend.app.models.schemas import User
except ModuleNotFoundError:
    from app.dependencies.auth import get_current_user
    from app.models.schemas import DashboardSummary, FindingStatusUpdate, ScanApiResponse, ScanCreate, ScanHistoryItem, Vulnerability
    from app.services.repository import scan_repository
    from app.services.scanner import ScanError
    from app.services.jobs import scan_job_service
    from app.services.reports import build_json_report, build_markdown_report, build_pdf_report
    from app.models.schemas import User


router = APIRouter(tags=["scans"])
logger = logging.getLogger(__name__)


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/scan", response_model=ScanApiResponse)
def create_scan(payload: ScanCreate, current_user: User = Depends(get_current_user())) -> ScanApiResponse:
    try:
        return scan_job_service.submit_scan(str(payload.repo_url), current_user.user_id, payload.preset)
    except ScanError as exc:
        logger.warning("Repository scan failed for %s: %s", payload.repo_url, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected scanner failure for %s", payload.repo_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected failure while scanning the repository. Try another public GitHub repo or retry with a smaller codebase.",
        ) from exc


@router.get("/results", response_model=list[ScanHistoryItem])
@router.get("/scans", response_model=list[ScanHistoryItem], include_in_schema=False)
def list_results(current_user: User = Depends(get_current_user())) -> list[ScanHistoryItem]:
    return scan_repository.list_scans(current_user.user_id)


@router.get("/results/{scan_id}", response_model=ScanApiResponse)
@router.get("/scans/{scan_id}", response_model=ScanApiResponse, include_in_schema=False)
def get_result(scan_id: str, current_user: User = Depends(get_current_user())) -> ScanApiResponse:
    try:
        return scan_repository.get_scan(scan_id, current_user.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scan not found") from exc


@router.patch("/results/{scan_id}/findings/{finding_id}", response_model=ScanApiResponse)
def update_finding_status(scan_id: str, finding_id: str, payload: FindingStatusUpdate, current_user: User = Depends(get_current_user())) -> ScanApiResponse:
    try:
        return scan_repository.update_finding_status(scan_id, current_user.user_id, finding_id, payload.review_status)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scan or finding not found") from exc


@router.get("/results/{scan_id}/report")
def export_report(
    scan_id: str,
    format: str = Query(default="markdown", pattern="^(markdown|json|pdf)$"),
    current_user: User = Depends(get_current_user()),
) -> Response:
    try:
        scan = scan_repository.get_scan(scan_id, current_user.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scan not found") from exc

    filename_base = f"{scan.repo_name}-{scan.scan_id}"
    if format == "json":
        return Response(
            content=build_json_report(scan),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
        )
    if format == "pdf":
        return Response(
            content=build_pdf_report(scan),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )
    return Response(
        content=build_markdown_report(scan),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
    )


@router.get("/vulnerabilities", response_model=list[Vulnerability])
def list_vulnerabilities(current_user: User = Depends(get_current_user())) -> list[Vulnerability]:
    return scan_repository.all_vulnerabilities(current_user.user_id)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(current_user: User = Depends(get_current_user())) -> DashboardSummary:
    return scan_repository.summary(current_user.user_id)
