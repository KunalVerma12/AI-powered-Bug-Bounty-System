from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

try:
    from backend.app.models.schemas import ScanCounts, ScanFinding, ScanPreset, Severity
except ModuleNotFoundError:
    from app.models.schemas import ScanCounts, ScanFinding, ScanPreset, Severity


logger = logging.getLogger(__name__)

SCAN_TIMEOUT_SECONDS = 180
GIT_TIMEOUT_SECONDS = 60
BIN_DIR = Path(sys.executable).parent
MAX_REPO_FILE_COUNT = 4000
MAX_REPO_SIZE_BYTES = 75 * 1024 * 1024
IGNORED_DIRECTORIES = {".git", "node_modules", "dist", "build", "coverage", ".next", ".venv", "venv", "__pycache__"}
MONOREPO_ROOT_FILES = {"package.json", "pyproject.toml", "requirements.txt", "go.mod", "pom.xml", "Cargo.toml"}
CONFIG_MARKERS = ("config", "settings", ".env", "docker", "compose", ".github", "k8s", "helm", "terraform", ".tf", ".yaml", ".yml", ".toml", ".ini")
DEPENDENCY_FILES = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "requirements.txt", "poetry.lock", "pyproject.toml", "Pipfile", "Pipfile.lock", "go.mod", "go.sum", "pom.xml", "Cargo.toml", "Cargo.lock"}
SECRET_FILE_MARKERS = (".env", ".pem", ".key", ".p12", ".crt", ".npmrc", ".pypirc")
PRESET_LIMITS = {
    ScanPreset.quick: (1800, 45 * 1024 * 1024),
    ScanPreset.full: (6000, 120 * 1024 * 1024),
    ScanPreset.config_only: (2200, 35 * 1024 * 1024),
    ScanPreset.dependency_only: (1800, 30 * 1024 * 1024),
    ScanPreset.secrets_only: (2200, 35 * 1024 * 1024),
}


class ScanError(Exception):
    """Raised when a repository scan cannot be completed safely."""


@dataclass
class ScanPlan:
    preset: ScanPreset
    semgrep_targets: list[Path] = field(default_factory=list)
    bandit_targets: list[Path] = field(default_factory=list)
    monorepo_roots: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    limits: tuple[int, int] = (MAX_REPO_FILE_COUNT, MAX_REPO_SIZE_BYTES)


def extract_repo_name(repo_url: str) -> str:
    path = urlparse(repo_url).path.strip("/")
    if not path:
        return "unknown-repository"
    return path.split("/")[-1]


def validate_repo_url(repo_url: str) -> None:
    parsed = urlparse(repo_url)
    hostname = parsed.hostname or ""
    if parsed.scheme != "https" or hostname not in {"github.com", "www.github.com"}:
        raise ScanError("Only public GitHub HTTPS repository URLs are supported.")

    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) < 2:
        raise ScanError("Repository URL must look like https://github.com/owner/repository.")


def _scanner_env() -> dict[str, str]:
    return {**os.environ, "PATH": f"{BIN_DIR}:{os.environ.get('PATH', '')}"}


def run_command(command: list[str], cwd: Path | None = None, timeout: int = SCAN_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_scanner_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ScanError(f"Command timed out: {' '.join(command[:2])}") from exc
    except OSError as exc:
        raise ScanError(f"Failed to execute scanner command: {' '.join(command)}") from exc


def find_tool(tool_name: str) -> str | None:
    candidates = [BIN_DIR / tool_name, BIN_DIR / f"{tool_name}.exe"]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which(tool_name)


def available_tools() -> dict[str, bool]:
    return {
        "semgrep": find_tool("semgrep") is not None,
        "bandit": find_tool("bandit") is not None,
        "pip-audit": find_tool("pip-audit") is not None,
        "gitleaks": find_tool("gitleaks") is not None,
    }


def ensure_scanners_available() -> dict[str, bool]:
    tools = available_tools()
    if not any(tools.values()):
        raise ScanError("Semgrep and Bandit are not installed on the server.")
    return tools


def clone_repository(repo_url: str, destination: Path) -> None:
    result = run_command(
        ["git", "clone", "--depth", "1", repo_url, str(destination)],
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        safe_stderr = stderr.replace(repo_url, _redact_repo_url(repo_url))
        if "Repository not found" in stderr or "Authentication failed" in stderr:
            raise ScanError("Repository could not be cloned. It may be private, unavailable, or invalid.")
        raise ScanError(f"Git clone failed: {safe_stderr or 'unknown git error'}")


def _redact_repo_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.username or parsed.password:
        host = parsed.hostname or "github.com"
        return parsed._replace(netloc=host).geturl()
    return repo_url


def iter_repo_files(repo_path: Path, targets: list[Path] | None = None):
    roots = targets or [repo_path]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if any(part in IGNORED_DIRECTORIES for part in root.parts):
                continue
            if root not in seen:
                seen.add(root)
                yield root
            continue
        for file_path in root.rglob("*"):
            if file_path in seen:
                continue
            seen.add(file_path)
            if not file_path.is_file():
                continue
            if any(part in IGNORED_DIRECTORIES for part in file_path.parts):
                continue
            yield file_path


def repo_metrics(repo_path: Path, targets: list[Path] | None = None) -> dict[str, int]:
    file_count = 0
    total_bytes = 0
    for file_path in iter_repo_files(repo_path, targets):
        file_count += 1
        try:
            total_bytes += file_path.stat().st_size
        except OSError:
            continue
    return {"file_count": file_count, "total_bytes": total_bytes}


def ensure_repo_within_limits(
    repo_path: Path,
    targets: list[Path] | None = None,
    max_files: int = MAX_REPO_FILE_COUNT,
    max_bytes: int = MAX_REPO_SIZE_BYTES,
) -> dict[str, int]:
    metrics = repo_metrics(repo_path, targets)
    if metrics["file_count"] > max_files:
        raise ScanError(f"Repo too large for live scan: {metrics['file_count']} files exceeds the {max_files}-file limit.")
    if metrics["total_bytes"] > max_bytes:
        size_mb = round(metrics["total_bytes"] / (1024 * 1024), 1)
        limit_mb = round(max_bytes / (1024 * 1024), 1)
        raise ScanError(f"Repo too large for live scan: {size_mb} MB exceeds the {limit_mb} MB limit.")
    return metrics


def map_semgrep_severity(value: str | None) -> Severity:
    mapping = {
        "INFO": Severity.low,
        "WARNING": Severity.medium,
        "ERROR": Severity.high,
    }
    return mapping.get((value or "").upper(), Severity.medium)


def map_bandit_severity(value: str | None, confidence: str | None = None) -> Severity:
    normalized = (value or "").upper()
    if normalized == "HIGH" and (confidence or "").upper() == "HIGH":
        return Severity.critical
    mapping = {
        "LOW": Severity.low,
        "MEDIUM": Severity.medium,
        "HIGH": Severity.high,
    }
    return mapping.get(normalized, Severity.medium)


def suggest_fix(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if "sql" in text or "injection" in text:
        return "Use parameterized queries or prepared statements and validate untrusted request input before database access."
    if "secret" in text or "credential" in text or "token" in text:
        return "Remove the secret from source control, rotate it immediately, and load future credentials from a secure secret manager."
    if "xss" in text or "html" in text or "script" in text:
        return "Sanitize untrusted HTML, remove dangerous attributes, and prefer safe rendering primitives for user-controlled content."
    if "subprocess" in text or "shell" in text or "command" in text:
        return "Avoid shell invocation with untrusted data and pass arguments as structured lists instead of formatted strings."
    if "pickle" in text or "yaml" in text or "deserial" in text:
        return "Replace unsafe deserialization with safe parsers and allow-list trusted types instead of loading arbitrary objects."
    return "Review the flagged code path, validate untrusted input, and apply the safer library or framework pattern recommended by the scanner."


def relativize(path: str, repo_path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(repo_path.resolve()))
    except Exception:
        return path


def has_files_with_suffix(repo_path: Path, suffixes: tuple[str, ...], targets: list[Path] | None = None) -> bool:
    return any(file_path.suffix.lower() in suffixes for file_path in iter_repo_files(repo_path, targets))


def _is_config_path(file_path: Path, repo_path: Path) -> bool:
    relative = str(file_path.relative_to(repo_path)).lower()
    return any(marker in relative for marker in CONFIG_MARKERS)


def _is_dependency_manifest(file_path: Path) -> bool:
    return file_path.name in DEPENDENCY_FILES


def _is_secret_candidate(file_path: Path, repo_path: Path) -> bool:
    relative = str(file_path.relative_to(repo_path)).lower()
    return file_path.name in {"secrets.yml", "secrets.yaml"} or any(marker in relative for marker in SECRET_FILE_MARKERS) or "secret" in relative or "token" in relative


def discover_monorepo_roots(repo_path: Path) -> list[Path]:
    candidates: set[Path] = set()
    for file_path in iter_repo_files(repo_path):
        if file_path.name not in MONOREPO_ROOT_FILES:
            continue
        root = file_path.parent
        if root == repo_path:
            continue
        candidates.add(root)
    return sorted(candidates, key=lambda path: (len(path.relative_to(repo_path).parts), str(path)))


def build_scan_plan(repo_path: Path, preset: ScanPreset) -> ScanPlan:
    monorepo_roots = discover_monorepo_roots(repo_path)
    primary_roots = monorepo_roots[:4] or [repo_path]
    semgrep_targets: list[Path]
    bandit_targets: list[Path]
    notes: list[str] = []

    if monorepo_roots:
        notes.append(
            "Monorepo-aware routing focused the scan on: "
            + ", ".join(str(path.relative_to(repo_path)) for path in primary_roots)
            + "."
        )

    if preset == ScanPreset.quick:
        semgrep_targets = primary_roots[:3]
        bandit_targets = [path for path in semgrep_targets if has_files_with_suffix(repo_path, (".py",), [path])]
        notes.append("Quick preset uses focused app roots and lighter limits for faster turnaround.")
    elif preset == ScanPreset.config_only:
        semgrep_targets = [file_path for file_path in iter_repo_files(repo_path) if _is_config_path(file_path, repo_path)][:250]
        bandit_targets = []
        notes.append("Config-only preset narrowed the scan to infrastructure, deployment, and application settings surfaces.")
    elif preset == ScanPreset.dependency_only:
        semgrep_targets = [file_path for file_path in iter_repo_files(repo_path) if _is_dependency_manifest(file_path)][:250]
        bandit_targets = []
        notes.append("Dependency-only preset focused on manifests and lockfiles.")
    elif preset == ScanPreset.secrets_only:
        semgrep_targets = [file_path for file_path in iter_repo_files(repo_path) if _is_secret_candidate(file_path, repo_path)][:250]
        bandit_targets = []
        notes.append("Secrets-only preset focused on credential-like files and sensitive configuration paths.")
    else:
        semgrep_targets = primary_roots
        bandit_targets = [path for path in primary_roots if has_files_with_suffix(repo_path, (".py",), [path])]
        notes.append("Full preset scanned the routed repository surface with the broadest analyzer coverage available in this environment.")

    if not semgrep_targets:
        semgrep_targets = primary_roots[:1]
        notes.append("No preset-specific targets were found, so the scanner fell back to the primary application root.")

    return ScanPlan(
        preset=preset,
        semgrep_targets=semgrep_targets,
        bandit_targets=bandit_targets,
        monorepo_roots=monorepo_roots,
        notes=notes,
        limits=PRESET_LIMITS[preset],
    )


def parse_semgrep(repo_path: Path, repo_name: str, targets: list[Path] | None = None) -> list[ScanFinding]:
    semgrep_bin = find_tool("semgrep")
    if not semgrep_bin:
        return []

    semgrep_targets = [str(path) for path in (targets or [repo_path]) if path.exists()]
    command = [
        semgrep_bin,
        "--config=auto",
        "--json",
        "--exclude",
        "node_modules",
        "--exclude",
        ".git",
        "--exclude",
        "dist",
        "--exclude",
        "build",
        "--exclude",
        "coverage",
        *semgrep_targets,
    ]
    result = run_command(command, timeout=SCAN_TIMEOUT_SECONDS)
    if result.returncode not in {0, 1}:
        stderr = (result.stderr or result.stdout).strip()
        logger.warning("Semgrep failed: %s", stderr)
        return []

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        logger.warning("Semgrep returned non-JSON output for %s", repo_name)
        return []
    findings: list[ScanFinding] = []
    for entry in payload.get("results", []):
        check_id = entry.get("check_id", "semgrep-finding")
        extra = entry.get("extra", {})
        metadata = extra.get("metadata", {})
        message = extra.get("message") or check_id
        severity = map_semgrep_severity(extra.get("severity"))
        cwe = metadata.get("cwe")
        cwe_text = ", ".join(cwe) if isinstance(cwe, list) else str(cwe or "Semgrep finding")
        description = str(metadata.get("owasp") or metadata.get("shortlink") or cwe_text)
        start = entry.get("start", {})
        lines = entry.get("lines", "")

        findings.append(
            ScanFinding(
                id=f"semgrep-{uuid4()}",
                title=message,
                severity=severity,
                description=description,
                file=relativize(entry.get("path", ""), repo_path),
                line=int(start.get("line", 1)),
                tool="semgrep",
                fix=suggest_fix(message, description),
                explanation=f"Semgrep flagged `{check_id}` in {repo_name} and identified a potentially unsafe pattern that warrants code review.",
                snippet=lines.strip() or "Snippet unavailable from Semgrep output.",
                confidence=0.82 if severity in {Severity.high, Severity.critical} else 0.72,
                cvss_score=7.5 if severity in {Severity.high, Severity.critical} else 5.2 if severity == Severity.medium else 3.1,
                exploitability_score=0.87 if severity in {Severity.high, Severity.critical} else 0.61 if severity == Severity.medium else 0.38,
                cwe=cwe_text,
                cwe_link=_build_cwe_link(cwe_text),
                tags=["static-analysis", "semgrep"],
                false_positive_hint=f"Re-check whether the Semgrep rule `{check_id}` is hitting generated code, a defensive wrapper, or a test-only path.",
                attack_surface_tags=infer_attack_surface_tags(message, description, relativize(entry.get('path', ''), repo_path)),
                ai_analyzed=False,
                analysis_source="static-analysis",
            )
        )

    return findings


def parse_bandit(repo_path: Path, repo_name: str, targets: list[Path] | None = None) -> list[ScanFinding]:
    bandit_bin = find_tool("bandit")
    if not bandit_bin:
        return []
    bandit_targets = [path for path in (targets or [repo_path]) if path.exists()]
    if not has_files_with_suffix(repo_path, (".py",), bandit_targets):
        return []

    findings: list[ScanFinding] = []
    for target in bandit_targets:
        result = run_command([bandit_bin, "-r", str(target), "-f", "json"], timeout=SCAN_TIMEOUT_SECONDS)
        if result.returncode not in {0, 1}:
            stderr = (result.stderr or result.stdout).strip()
            logger.warning("Bandit failed: %s", stderr)
            continue

        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            logger.warning("Bandit returned non-JSON output for %s", repo_name)
            continue
        for entry in payload.get("results", []):
            issue_text = entry.get("issue_text", "Bandit finding")
            issue_confidence = (entry.get("issue_confidence") or "").upper()
            severity = map_bandit_severity(entry.get("issue_severity"), issue_confidence)
            code = (entry.get("code") or "").strip()
            confidence_value = {
                "LOW": 0.62,
                "MEDIUM": 0.79,
                "HIGH": 0.91,
            }.get(issue_confidence, 0.7)

            findings.append(
                ScanFinding(
                    id=f"bandit-{uuid4()}",
                    title=entry.get("test_name", "bandit-finding"),
                    severity=severity,
                    description=issue_text,
                    file=relativize(entry.get("filename", ""), repo_path),
                    line=int(entry.get("line_number", 1)),
                    tool="bandit",
                    fix=suggest_fix(entry.get("test_name", ""), issue_text),
                    explanation=f"Bandit reported {entry.get('test_id', 'a security rule')} while analyzing Python code in {repo_name}.",
                    snippet=code or "Snippet unavailable from Bandit output.",
                    confidence=confidence_value,
                    cvss_score=8.2 if severity == Severity.critical else 6.8 if severity == Severity.high else 4.7 if severity == Severity.medium else 2.9,
                    exploitability_score=0.92 if severity == Severity.critical else 0.76 if severity == Severity.high else 0.58 if severity == Severity.medium else 0.31,
                    cwe=entry.get("test_id", "Bandit rule"),
                    cwe_link="https://bandit.readthedocs.io/" if entry.get("test_id") else "",
                    tags=["static-analysis", "bandit"],
                    false_positive_hint=f"Confirm whether {entry.get('test_id', 'this Bandit rule')} applies to production code or a controlled internal-only path.",
                    attack_surface_tags=infer_attack_surface_tags(entry.get("test_name", ""), issue_text, relativize(entry.get("filename", ""), repo_path)),
                    ai_analyzed=False,
                    analysis_source="static-analysis",
                )
            )

    return findings


def collect_static_findings(repo_path: Path, repo_name: str, preset: ScanPreset) -> tuple[list[ScanFinding], dict[str, bool], list[str]]:
    tools = ensure_scanners_available()
    plan = build_scan_plan(repo_path, preset)
    ensure_repo_within_limits(repo_path, plan.semgrep_targets, max_files=plan.limits[0], max_bytes=plan.limits[1])
    executed_tools = {name: False for name in tools}
    findings: list[ScanFinding] = []
    if tools["semgrep"] and plan.semgrep_targets:
        executed_tools["semgrep"] = True
        findings.extend(parse_semgrep(repo_path, repo_name, plan.semgrep_targets))
    if tools["bandit"] and plan.bandit_targets and preset not in {ScanPreset.config_only, ScanPreset.dependency_only, ScanPreset.secrets_only}:
        executed_tools["bandit"] = True
        findings.extend(parse_bandit(repo_path, repo_name, plan.bandit_targets))
    if preset == ScanPreset.dependency_only and not any(executed_tools.values()):
        plan.notes.append("No supported local dependency scanner was available, so the preset performed a manifest-focused metadata pass only.")
    return findings, executed_tools, plan.notes


def _build_cwe_link(cwe_text: str) -> str:
    if "cwe-" not in cwe_text.lower():
        return ""
    lowered = cwe_text.lower()
    start = lowered.find("cwe-")
    digits = []
    for character in cwe_text[start + 4 :]:
        if character.isdigit():
            digits.append(character)
        elif digits:
            break
    if not digits:
        return ""
    return f"https://cwe.mitre.org/data/definitions/{''.join(digits)}.html"


def infer_attack_surface_tags(title: str, description: str, file_path: str) -> list[str]:
    lowered = f"{title} {description} {file_path}".lower()
    tags: list[str] = []
    if any(term in lowered for term in ("auth", "login", "csrf", "session", "cookie")):
        tags.append("auth")
    if any(term in lowered for term in ("sql", "db", "database", "migration")):
        tags.append("database")
    if any(term in lowered for term in ("config", ".env", "secret", "token", "credential")):
        tags.append("config")
    if any(term in lowered for term in ("xss", "html", "script", "jsx", "tsx", "frontend")):
        tags.append("frontend")
    if any(term in lowered for term in ("docker", "container", "compose", "k8s")):
        tags.append("container")
    if any(term in lowered for term in ("api", "route", "controller", "server", "middleware")):
        tags.append("backend")
    return tags or ["application"]


def count_findings(findings: list[ScanFinding]) -> ScanCounts:
    counter = Counter(finding.severity.value for finding in findings)
    return ScanCounts(
        total=len(findings),
        critical=counter.get("Critical", 0),
        high=counter.get("High", 0),
        medium=counter.get("Medium", 0),
        low=counter.get("Low", 0),
    )
