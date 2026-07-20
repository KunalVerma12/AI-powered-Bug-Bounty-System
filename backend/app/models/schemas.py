from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class Severity(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class ScanStatus(str, Enum):
    queued = "Queued"
    running = "Running"
    completed = "Completed"
    failed = "Failed"


class ScanPreset(str, Enum):
    quick = "quick"
    full = "full"
    config_only = "config-only"
    dependency_only = "dependency-only"
    secrets_only = "secrets-only"


class FindingReviewStatus(str, Enum):
    open = "Open"
    reviewed = "Reviewed"
    false_positive = "False Positive"


class AgentStep(BaseModel):
    name: str
    role: str
    status: ScanStatus
    progress: int = Field(ge=0, le=100)
    summary: str


class RepoRecon(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    sensitive_files: list[str] = Field(default_factory=list)
    architecture_summary: str = ""


class RepoAnalysis(BaseModel):
    overview_summary: str = ""
    description: str = ""
    project_type: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    architecture: str = ""
    security_posture: str = ""
    improvements_summary: str = ""
    missing_features: list[str] = Field(default_factory=list)
    risk_areas: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    trust_boundaries: list[str] = Field(default_factory=list)
    top_priorities: list[str] = Field(default_factory=list)


class Vulnerability(BaseModel):
    id: str
    title: str
    severity: Severity
    description: str
    file_path: str
    line: int
    tool: str
    cwe: str
    repo_name: str
    ai_analysis: str
    fix_suggestion: str
    snippet: str
    confidence: float = Field(ge=0, le=1)
    cvss_score: float = Field(default=0, ge=0, le=10)
    exploitability_score: float = Field(default=0, ge=0, le=1)
    tags: list[str]
    tech_context: str = ""
    component_owner: str = ""
    false_positive_hint: str = ""
    cwe_link: str = ""
    attack_surface_tags: list[str] = Field(default_factory=list)
    review_status: FindingReviewStatus = FindingReviewStatus.open
    ai_analyzed: bool = True
    analysis_source: str = "multi-agent"
    what_happened: str = ""
    why_it_matters: str = ""
    how_to_fix: str = ""
    example_fix: str = ""


class ScanCreate(BaseModel):
    repo_url: HttpUrl
    preset: ScanPreset = ScanPreset.full


class UserRegister(BaseModel):
    username: str = ""
    email: str
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class User(BaseModel):
    user_id: str
    username: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class ScanCounts(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ScanFinding(BaseModel):
    id: str
    title: str
    severity: Severity
    description: str
    file: str
    line: int
    tool: str
    fix: str
    explanation: str
    snippet: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    cvss_score: float = Field(default=0, ge=0, le=10)
    exploitability_score: float = Field(default=0, ge=0, le=1)
    cwe: str = "Unclassified"
    tags: list[str] = Field(default_factory=list)
    tech_context: str = ""
    component_owner: str = ""
    false_positive_hint: str = ""
    cwe_link: str = ""
    attack_surface_tags: list[str] = Field(default_factory=list)
    review_status: FindingReviewStatus = FindingReviewStatus.open
    ai_analyzed: bool = False
    analysis_source: str = "static-analysis"
    what_happened: str = ""
    why_it_matters: str = ""
    how_to_fix: str = ""
    example_fix: str = ""


class ScanApiResponse(BaseModel):
    scan_id: str
    user_id: str
    repo: str
    repo_name: str
    preset: ScanPreset = ScanPreset.full
    status: str
    scanned_at: datetime
    progress: int = 0
    summary: ScanCounts
    vulnerabilities: list[ScanFinding]
    agent_steps: list[AgentStep]
    timeline: list[str]
    recon: RepoRecon = Field(default_factory=RepoRecon)
    repo_analysis: RepoAnalysis = Field(default_factory=RepoAnalysis)
    analysis_mode: str = "local"
    risk_assessment: str = ""
    error_message: str = ""


class ScanHistoryItem(BaseModel):
    scan_id: str
    user_id: str
    repo: str
    repo_name: str
    preset: ScanPreset = ScanPreset.full
    status: str
    scanned_at: datetime
    progress: int = 0
    summary: ScanCounts
    analysis_mode: str = "local"
    error_message: str = ""


class FindingStatusUpdate(BaseModel):
    review_status: FindingReviewStatus


class DashboardSummary(BaseModel):
    total_scans: int
    running_scans: int
    total_vulnerabilities: int
    critical_vulnerabilities: int
    average_confidence: float
    severity_breakdown: dict[str, int]


class GitHubConnectionStatus(BaseModel):
    connected: bool
    configured: bool = True
    username: str = ""
    avatar_url: str = ""
    profile_url: str = ""
    connected_at: datetime | None = None


class GitHubAuthStart(BaseModel):
    auth_url: str
    state: str


class GitHubRepositoryProfile(BaseModel):
    architecture_summary: str = ""
    auth_quality: str = ""
    config_exposure_risk: str = ""
    api_complexity: str = ""
    dependency_risk: str = ""
    security_maturity: str = ""


class WorkspaceRepository(BaseModel):
    id: str
    github_id: int
    full_name: str
    name: str
    owner: str
    description: str = ""
    html_url: str
    clone_url: str
    private: bool = False
    visibility: str = "public"
    primary_language: str = ""
    stars: int = 0
    updated_at: datetime
    topics: list[str] = Field(default_factory=list)
    scan_count: int = 0
    findings_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    attack_surface_score: int = Field(default=0, ge=0, le=100)
    security_posture: int = Field(default=0, ge=0, le=100)
    latest_scan_id: str = ""
    latest_scan_status: str = ""
    ai_summary: str = ""
    profile: GitHubRepositoryProfile = Field(default_factory=GitHubRepositoryProfile)


class WorkspaceAnalytics(BaseModel):
    total_connected_repos: int = 0
    repos_scanned: int = 0
    risky_repos: int = 0
    average_posture: int = 0
    scan_coverage: int = 0
    most_vulnerable_repo: str = ""


class WorkspaceOverview(BaseModel):
    connection: GitHubConnectionStatus
    analytics: WorkspaceAnalytics
    repositories: list[WorkspaceRepository]


class WorkspaceScanRequest(BaseModel):
    preset: ScanPreset = ScanPreset.full
