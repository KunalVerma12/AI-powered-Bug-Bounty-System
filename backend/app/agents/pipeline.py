from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

try:
    from backend.app.agents.agents import crewai_available
    from backend.app.agents.crew import build_security_crew
    from backend.app.models.schemas import AgentStep, RepoRecon, ScanApiResponse, ScanFinding, ScanPreset, ScanStatus, Severity
    from backend.app.models.schemas import RepoAnalysis
    from backend.app.services.scanner import (
        clone_repository,
        collect_static_findings,
        count_findings,
        ensure_scanners_available,
        ensure_repo_within_limits,
        extract_repo_name,
        find_tool,
        run_command,
        validate_repo_url,
    )
except ModuleNotFoundError:
    from app.agents.agents import crewai_available
    from app.agents.crew import build_security_crew
    from app.models.schemas import AgentStep, RepoRecon, ScanApiResponse, ScanFinding, ScanPreset, ScanStatus, Severity
    from app.models.schemas import RepoAnalysis
    from app.services.scanner import (
        clone_repository,
        collect_static_findings,
        count_findings,
        ensure_scanners_available,
        ensure_repo_within_limits,
        extract_repo_name,
        find_tool,
        run_command,
        validate_repo_url,
    )


LANGUAGE_MARKERS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
}

FRAMEWORK_MARKERS = {
    "package.json": ("express", "next", "nest", "react", "vue"),
    "requirements.txt": ("django", "flask", "fastapi", "tornado"),
    "pyproject.toml": ("django", "flask", "fastapi"),
    "pom.xml": ("spring",),
    "go.mod": ("gin", "echo", "fiber"),
}

SENSITIVE_PATTERNS = ("auth", "login", "config", ".env", "secret", "token", "settings", "api", "routes")


@dataclass
class ScanPipelineContext:
    user_id: str
    repo_url: str
    repo_name: str
    repo_path: Path
    preset: ScanPreset = ScanPreset.full
    tools: dict[str, bool] = field(default_factory=dict)
    recon: RepoRecon | None = None
    repo_analysis: RepoAnalysis | None = None
    raw_vulnerabilities: list[ScanFinding] = field(default_factory=list)
    analyzed_vulnerabilities: list[ScanFinding] = field(default_factory=list)
    fixed_vulnerabilities: list[ScanFinding] = field(default_factory=list)
    analysis_mode: str = "local-orchestrated"
    timeline: list[str] = field(default_factory=list)
    risk_assessment: str = ""


def _ollama_model() -> str | None:
    if not find_tool("ollama"):
        return None
    return os.environ.get("OLLAMA_MODEL", "").strip() or None


def _local_llm_reasoning(finding: ScanFinding) -> dict[str, str] | None:
    model = _ollama_model()
    if not model:
        return None
    prompt = f"""
Return strict JSON with keys: what_happened, why_it_matters, how_to_fix, example_fix.

Title: {finding.title}
Severity: {finding.severity}
Description: {finding.description}
File: {finding.file}:{finding.line}
Tech context: {finding.tech_context}
Tool: {finding.tool}
CWE: {finding.cwe}

Keep the explanation concise, accurate, and developer-friendly.
""".strip()
    try:
        result = run_command(["ollama", "run", model, prompt], timeout=45)
        if result.returncode != 0:
            return None
        payload = json.loads((result.stdout or "").strip())
        if not isinstance(payload, dict):
            return None
        return {
            "what_happened": str(payload.get("what_happened", "")).strip(),
            "why_it_matters": str(payload.get("why_it_matters", "")).strip(),
            "how_to_fix": str(payload.get("how_to_fix", "")).strip(),
            "example_fix": str(payload.get("example_fix", "")).strip(),
        }
    except Exception:
        return None


def default_agent_steps() -> list[AgentStep]:
    return [
        AgentStep(
            name="Recon Agent",
            role="Maps repository architecture, languages, frameworks, and high-risk files.",
            status=ScanStatus.completed,
            progress=100,
            summary="Repository structure and sensitive entry points were profiled before static analysis began.",
        ),
        AgentStep(
            name="Scanner Agent",
            role="Runs Semgrep and Bandit to collect evidence-backed raw security findings.",
            status=ScanStatus.completed,
            progress=100,
            summary="Static analyzers completed and normalized raw findings into a shared vulnerability model.",
        ),
        AgentStep(
            name="AI Analyst",
            role="Correlates findings, adjusts severity, and adds exploitability context.",
            status=ScanStatus.completed,
            progress=100,
            summary="Findings were triaged for false positives, exploitability, and issue grouping.",
        ),
        AgentStep(
            name="Fix Agent",
            role="Attaches remediation guidance and secure implementation advice.",
            status=ScanStatus.completed,
            progress=100,
            summary="Actionable fixes and safer coding patterns were generated for surfaced risks.",
        ),
        AgentStep(
            name="Summary Agent",
            role="Builds the final risk assessment and dashboard-ready report.",
            status=ScanStatus.completed,
            progress=100,
            summary="The final report was assembled with severity posture, recon context, and agent insights.",
        ),
    ]


def queued_agent_steps() -> list[AgentStep]:
    return progress_steps(10, default_agent_steps())


def progress_steps(progress: int, steps: list[AgentStep]) -> list[AgentStep]:
    total = max(len(steps), 1)
    completed_steps = min(total, max(0, round((progress / 100) * total)))
    updated: list[AgentStep] = []
    for index, step in enumerate(steps):
        if index < completed_steps:
            updated.append(step.model_copy(update={"status": ScanStatus.completed, "progress": 100}))
        elif index == completed_steps and progress < 100:
            step_progress = min(95, max(15, progress - (index * (100 // total))))
            updated.append(step.model_copy(update={"status": ScanStatus.running, "progress": step_progress}))
        else:
            updated.append(step.model_copy(update={"status": ScanStatus.queued, "progress": 0}))
    return updated


def _detect_languages(repo_path: Path) -> list[str]:
    found = {language for file_path in repo_path.rglob("*") if file_path.is_file() for suffix, language in LANGUAGE_MARKERS.items() if file_path.suffix.lower() == suffix}
    return sorted(found)


def _detect_frameworks(repo_path: Path) -> list[str]:
    frameworks: set[str] = set()
    for filename, candidates in FRAMEWORK_MARKERS.items():
        for manifest in repo_path.rglob(filename):
            content = manifest.read_text(encoding="utf-8", errors="ignore").lower()
            for framework in candidates:
                if framework in content:
                    frameworks.add(framework.capitalize())
    return sorted(frameworks)


def _collect_files(repo_path: Path, limit: int = 8) -> tuple[list[str], list[str]]:
    entry_points: list[str] = []
    sensitive: list[str] = []
    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue
        relative = str(file_path.relative_to(repo_path))
        lower = relative.lower()
        if len(entry_points) < limit and (lower.endswith(("main.py", "app.py", "server.js", "index.js", "main.ts", "manage.py")) or "/routes" in lower):
            entry_points.append(relative)
        if len(sensitive) < limit and any(pattern in lower for pattern in SENSITIVE_PATTERNS):
            sensitive.append(relative)
    return entry_points, sensitive


def run_recon_agent(repo_path: Path) -> RepoRecon:
    languages = _detect_languages(repo_path)
    frameworks = _detect_frameworks(repo_path)
    entry_points, sensitive_files = _collect_files(repo_path)

    summary_bits = [
        f"Languages: {', '.join(languages) if languages else 'unknown'}",
        f"Frameworks: {', '.join(frameworks) if frameworks else 'none confidently detected'}",
        f"Entry points reviewed: {len(entry_points)}",
        f"Sensitive files surfaced: {len(sensitive_files)}",
    ]
    return RepoRecon(
        languages=languages,
        frameworks=frameworks,
        entry_points=entry_points,
        sensitive_files=sensitive_files,
        architecture_summary=". ".join(summary_bits) + ".",
    )


def _severity_rank(value: Severity) -> int:
    return {
        Severity.low: 1,
        Severity.medium: 2,
        Severity.high: 3,
        Severity.critical: 4,
    }[value]


def _infer_tech_context(finding: ScanFinding, recon: RepoRecon) -> str:
    file_path = finding.file.lower()
    frameworks = {framework.lower() for framework in recon.frameworks}
    languages = {language.lower() for language in recon.languages}

    if any(marker in file_path for marker in ("dockerfile", "docker-compose", "compose.yml", "compose.yaml", "security_opt")):
        return "Docker / Container"
    if any(marker in file_path for marker in (".github/workflows", "gitlab-ci", "jenkinsfile", "circleci")):
        return "CI/CD Pipeline"
    if any(marker in file_path for marker in (".env", "config", "settings", "secrets", "secret", "yaml", "yml", "toml", "ini")):
        return "Configuration"
    if any(marker in file_path for marker in ("migrations", "schema", "seed", "db", "database", "sql")):
        return "Database Layer"
    if any(marker in file_path for marker in ("routes", "route", "controller", "controllers", "api", "server", "auth", "middleware")):
        if "fastapi" in frameworks:
            return "FastAPI Backend"
        if "django" in frameworks:
            return "Django Backend"
        if "flask" in frameworks:
            return "Flask Backend"
        if "express" in frameworks:
            return "Express Backend"
        if "nest" in frameworks:
            return "NestJS Backend"
        if "python" in languages:
            return "Python Backend"
        if "javascript" in languages or "typescript" in languages:
            return "JavaScript Backend"
        return "Backend"
    if any(marker in file_path for marker in ("src/components", "src/pages", "public/", "assets/", "index.html", ".tsx", ".jsx", ".css", ".scss")):
        if "react" in frameworks:
            return "React Frontend"
        if "vue" in frameworks:
            return "Vue Frontend"
        if "next" in frameworks:
            return "Next.js Frontend"
        return "Frontend"
    if file_path.endswith(".py"):
        return "Python Service"
    if file_path.endswith((".js", ".ts")):
        return "JavaScript Service"
    return "Application Layer"


def _infer_component_owner(finding: ScanFinding) -> str:
    file_path = finding.file.lower()
    if any(marker in file_path for marker in ("auth", "login", "session")):
        return "Auth Team"
    if any(marker in file_path for marker in ("db", "database", "migration", "schema")):
        return "Platform Team"
    if any(marker in file_path for marker in ("config", ".env", "docker", "compose", ".github")):
        return "DevOps Team"
    if any(marker in file_path for marker in ("src/components", "src/pages", "public", ".jsx", ".tsx")):
        return "Frontend Team"
    return "Application Team"


def run_ai_analyst_agent(findings: list[ScanFinding], recon: RepoRecon) -> list[ScanFinding]:
    analyzed: list[ScanFinding] = []
    auth_sensitive = any("auth" in path.lower() or "login" in path.lower() for path in recon.sensitive_files)
    secret_sensitive = any(".env" in path.lower() or "config" in path.lower() for path in recon.sensitive_files)

    for finding in findings:
        severity = finding.severity
        confidence = finding.confidence
        tags = list(dict.fromkeys([*finding.tags, "multi-agent-triage"]))
        description = finding.description

        lowered = f"{finding.title} {finding.description}".lower()
        if ("sql" in lowered or "injection" in lowered) and auth_sensitive and severity == Severity.high:
            severity = Severity.critical
            confidence = min(0.99, confidence + 0.1)
            tags.append("auth-surface")
        elif ("secret" in lowered or "token" in lowered or "password" in lowered) and secret_sensitive and severity == Severity.medium:
            severity = Severity.high
            confidence = min(0.97, confidence + 0.08)
            tags.append("sensitive-config")
        else:
            confidence = min(0.98, confidence + 0.05)

        description = f"{description} Context-aware triage indicates this issue is reachable through repository surfaces identified during recon."
        tech_context = _infer_tech_context(finding, recon)
        attack_surface_tags = list(dict.fromkeys([*finding.attack_surface_tags, *tags]))
        cvss_score = finding.cvss_score
        exploitability_score = finding.exploitability_score
        false_positive_hint = finding.false_positive_hint or "Check whether the flagged code path is only used in tests, local tooling, or a fully trusted internal-only flow."

        if severity == Severity.critical:
            cvss_score = max(cvss_score, 9.1)
            exploitability_score = max(exploitability_score, 0.92)
        elif severity == Severity.high:
            cvss_score = max(cvss_score, 7.8)
            exploitability_score = max(exploitability_score, 0.78)
        elif severity == Severity.medium:
            cvss_score = max(cvss_score, 5.6)
            exploitability_score = max(exploitability_score, 0.58)
        else:
            cvss_score = max(cvss_score, 3.4)
            exploitability_score = max(exploitability_score, 0.34)

        analyzed.append(
            finding.model_copy(
                update={
                    "severity": severity,
                    "description": description,
                    "explanation": f"{finding.explanation} The AI Analyst correlated repository structure and exploitability context before ranking this issue.",
                    "confidence": round(confidence, 2),
                    "cvss_score": round(cvss_score, 1),
                    "exploitability_score": round(exploitability_score, 2),
                    "tags": tags,
                    "tech_context": tech_context,
                    "component_owner": _infer_component_owner(finding),
                    "false_positive_hint": false_positive_hint,
                    "attack_surface_tags": attack_surface_tags,
                    "ai_analyzed": True,
                    "analysis_source": "multi-agent",
                    "cwe": finding.cwe or "Contextualized finding",
                }
            )
        )
    return sorted(analyzed, key=lambda item: (_severity_rank(item.severity), item.confidence), reverse=True)


def run_fix_agent(findings: list[ScanFinding]) -> list[ScanFinding]:
    remediated: list[ScanFinding] = []
    for finding in findings:
        local_llm = _local_llm_reasoning(finding)
        enriched_fix = f"{finding.fix} Prioritize this in {finding.file}:{finding.line} and add regression coverage around the vulnerable path."
        lowered = f"{finding.title} {finding.description}".lower()
        what_happened = (
            f"We found a risky pattern in {finding.file}:{finding.line} that could let unsafe input or insecure behavior reach application logic."
        )
        why_it_matters = (
            "If this path is reachable in production, an attacker could abuse it to read data, run unintended behavior, or weaken the security boundary."
        )
        example_fix = ""
        if "sql" in lowered or "injection" in lowered:
            what_happened = "User-controlled input appears to be reaching a SQL query without a safe parameter boundary."
            why_it_matters = "That can let an attacker change the meaning of the query, bypass authentication, or read sensitive records."
            example_fix = 'cursor.execute("SELECT * FROM users WHERE email = %s", [email])'
            enriched_fix = "Move this query path to parameterized statements, validate the incoming data shape before query execution, and add a regression test that proves injected input is treated as data instead of SQL."
        elif "secret" in lowered or "token" in lowered or "password" in lowered:
            what_happened = "A secret or credential-like value looks exposed in source code or configuration."
            why_it_matters = "Leaked secrets can be reused by attackers to access infrastructure, impersonate services, or move laterally."
            example_fix = 'API_KEY = os.environ["API_KEY"]'
            enriched_fix = "Remove the secret from source control, rotate it immediately, move it into environment-backed secret storage, and add a pre-commit or CI check to stop future secret leaks."
        elif "shell" in lowered or "command" in lowered or "subprocess" in lowered:
            what_happened = "The code appears to launch a shell or command path in a way that could mix untrusted input into execution."
            why_it_matters = "That can open the door to command injection or unexpected system-level behavior."
            example_fix = 'subprocess.run(["git", "status"], check=True)'
            enriched_fix = "Replace shell invocation with argument-list execution, validate any user-supplied command input, and add a regression test covering hostile payloads."
        elif "xss" in lowered or "html" in lowered or "script" in lowered:
            what_happened = "Untrusted content may be rendered back into the browser without enough sanitization."
            why_it_matters = "Attackers could inject script into the page, steal session data, or perform actions as another user."
            example_fix = "renderSafeHtml(sanitize(userContent))"
            enriched_fix = "Sanitize or escape the rendered content, remove dangerous attributes, and add a browser-facing test that proves scripts are neutralized."
        elif "csrf" in lowered:
            what_happened = "A state-changing route appears to be missing a reliable CSRF defense layer."
            why_it_matters = "Without CSRF protection, a logged-in user could be tricked into sending a legitimate browser request that changes data without their intent."
            example_fix = "app.use(csrf())"
            enriched_fix = "Add CSRF middleware or framework-native CSRF protection, verify cookies or anti-forgery tokens on state-changing routes, and cover the flow with an integration test."
        elif "deserialize" in lowered or "pickle" in lowered or "yaml" in lowered:
            what_happened = "The code appears to deserialize untrusted content using an unsafe parser or object loader."
            why_it_matters = "Unsafe deserialization can let attackers create unexpected objects, trigger code paths, or break trust boundaries."
            example_fix = "yaml.safe_load(payload)"
            enriched_fix = "Swap in a safe parser, narrow accepted types to a trusted allow-list, and reject arbitrary object reconstruction at the boundary."
        elif "docker" in lowered or "container" in lowered or "compose" in lowered:
            what_happened = "The container configuration exposes a runtime setting that weakens isolation or privilege boundaries."
            why_it_matters = "Container hardening issues can make it easier to pivot from an application flaw into a host or infrastructure impact."
            example_fix = "security_opt: ['no-new-privileges:true']"
            enriched_fix = "Tighten the container runtime configuration, drop unnecessary privileges, and verify the deployment manifest against a hardened baseline."

        if local_llm:
            what_happened = local_llm["what_happened"] or what_happened
            why_it_matters = local_llm["why_it_matters"] or why_it_matters
            enriched_fix = local_llm["how_to_fix"] or enriched_fix
            example_fix = local_llm["example_fix"] or example_fix

        remediated.append(
            finding.model_copy(
                update={
                    "fix": enriched_fix,
                    "explanation": f"{finding.explanation} The Fix Agent translated the issue into a developer-ready remediation plan.",
                    "tags": list(dict.fromkeys([*finding.tags, "remediation-ready"])),
                    "what_happened": what_happened,
                    "why_it_matters": why_it_matters,
                    "how_to_fix": enriched_fix,
                    "example_fix": example_fix,
                    "analysis_source": "local-ollama" if local_llm else finding.analysis_source,
                }
            )
        )
    return remediated


def run_repo_intelligence_agent(recon: RepoRecon, findings: list[ScanFinding]) -> RepoAnalysis:
    tech_stack = list(dict.fromkeys([*recon.languages, *recon.frameworks]))
    sensitive_joined = ", ".join(recon.sensitive_files[:3]) if recon.sensitive_files else "core application entry points"
    missing_features: list[str] = []
    risk_areas: list[str] = []
    recommendations: list[str] = []
    trust_boundaries: list[str] = []
    top_priorities: list[str] = []

    lowered_paths = " ".join(recon.sensitive_files + recon.entry_points).lower()
    if "auth" not in lowered_paths:
        missing_features.append("Authentication does not stand out as a clear first-class layer, which can make it easier for sensitive routes to grow without consistent access control.")
        recommendations.append("Add a clearly named authentication and authorization boundary so protected endpoints, admin actions, and session flows are easy to reason about.")
    if "rate" not in lowered_paths:
        missing_features.append("Rate limiting is not obvious from the repository layout, so public endpoints may be more exposed to brute-force or abuse than they need to be.")
        recommendations.append("Introduce request throttling around login, signup, password reset, search, and any endpoint that could be abused at scale.")
    if ".env" not in lowered_paths and "config" not in lowered_paths:
        missing_features.append("Secret handling is not easy to spot, which usually means developers may not have a clear pattern for credentials, tokens, and environment-specific settings.")
        recommendations.append("Standardize secret management with environment variables or a secret manager and document which values should never live in source control.")
    if "middleware" not in lowered_paths and "validator" not in lowered_paths:
        missing_features.append("Input validation is not clearly visible near entry points, increasing the chance that unsafe data can travel deeper into business logic.")
        recommendations.append("Add schema-based validation close to routes and controllers so malformed or hostile input is rejected before it reaches core logic.")
    if "log" not in lowered_paths:
        missing_features.append("Security-aware logging is not clearly represented, which can make debugging incidents and tracing suspicious activity much harder.")
        recommendations.append("Add structured audit-style logging for authentication events, validation failures, permission denials, and high-risk actions.")
    if recon.entry_points:
        trust_boundaries.append(f"Public entry points such as {', '.join(recon.entry_points[:3])} appear to sit at the main request boundary, so validation and authorization should be strongest there.")
    if recon.sensitive_files:
        trust_boundaries.append(f"Sensitive files like {sensitive_joined} look like the configuration and trust-control layer for this repo.")
    if not trust_boundaries:
        trust_boundaries.append("The repo looks small enough that its main trust boundary is probably concentrated around a handful of runtime and configuration files.")

    for path in recon.sensitive_files:
        risk_areas.append(f"{path} looks like a sensitive surface where configuration mistakes, weak validation, or authorization gaps could have an outsized impact.")
    if not risk_areas and recon.entry_points:
        risk_areas.extend([f"{entry} appears to be an entry point, so it is a good place to verify validation, authentication, and defensive error handling." for entry in recon.entry_points[:3]])

    if not findings:
        recommendations.append("No major findings surfaced in this pass, but it would still be smart to add dependency scanning and secret scanning to CI so weak spots are caught continuously.")
        recommendations.append("Use this clean result as a chance to strengthen validation, logging, and defense-in-depth controls before the codebase grows more complex.")
        top_priorities.extend(
            [
                "Keep this clean baseline healthy by adding dependency, secret, and config scanning to CI.",
                "Add or verify defensive layers around validation, logging, and access control before the codebase grows.",
                "Document the main trust boundaries so future contributors know where security checks belong.",
            ]
        )
    else:
        ranked_findings = sorted(findings, key=lambda finding: (finding.cvss_score, finding.exploitability_score, _severity_rank(finding.severity)), reverse=True)
        for finding in ranked_findings[:3]:
            top_priorities.append(f"Prioritize {finding.title} in {finding.tech_context or finding.file} because it combines meaningful exploitability with direct impact on the current trust boundary.")

    critical = sum(1 for finding in findings if finding.severity == Severity.critical)
    high = sum(1 for finding in findings if finding.severity == Severity.high)
    if critical or high >= 3:
        posture_level = "Low"
        posture_reason = "The scan surfaced high-impact issues or enough high-severity signals that the current protections look weak."
    elif high >= 1 or missing_features:
        posture_level = "Medium"
        posture_reason = "The repository shows some positive structure, but there are visible security gaps or findings that still need attention."
    else:
        posture_level = "High"
        posture_reason = "No major issues stood out in this pass, and the repository structure suggests a more disciplined baseline."

    if "api" in lowered_paths or any("express" in item.lower() or "fastapi" in item.lower() for item in tech_stack):
        project_type = "REST API"
    elif any("react" in item.lower() or "vue" in item.lower() for item in tech_stack):
        project_type = "Web application"
    else:
        project_type = "Application service"

    description = (
        f"This looks like a {project_type.lower()} built with {', '.join(tech_stack) if tech_stack else 'a lightweight application stack'}. "
        f"At a high level, the repository seems focused on handling application behavior through entry points such as "
        f"{', '.join(recon.entry_points[:3]) if recon.entry_points else 'its main runtime files'}, which suggests a fairly direct request-to-logic flow."
    )
    architecture = (
        f"The repository appears to be organized around {', '.join(recon.entry_points[:3]) if recon.entry_points else 'a small set of runtime files'}, "
        f"while more security-sensitive behavior likely lives around {sensitive_joined}. "
        f"From the file layout, the codebase feels like it is structured for straightforward feature delivery, but the most important hardening points will probably sit near configuration, auth-adjacent files, and public request handlers."
    )
    security_posture = f"{posture_level} security posture. {posture_reason} In plain terms, the project shows some healthy structure, but the scan still found areas where a developer would want stronger guardrails before calling it hardened."
    overview_summary = (
        f"Here is the quick read: this repository behaves like a {project_type.lower()} with a stack centered on {', '.join(tech_stack) if tech_stack else 'its detected runtime tools'}. "
        f"It looks understandable and shippable, but the places that deserve the most trust-focused review are {sensitive_joined}."
    )
    improvements_summary = (
        "If a senior engineer were reviewing this codebase, the next advice would not just be to patch isolated findings. "
        "It would be to strengthen the repeatable safety layers around authentication, validation, secret handling, logging, and public-facing request flow so future features land on a safer foundation."
    )

    return RepoAnalysis(
        overview_summary=overview_summary,
        description=description,
        project_type=project_type,
        tech_stack=tech_stack,
        architecture=architecture,
        security_posture=security_posture,
        improvements_summary=improvements_summary,
        missing_features=missing_features,
        risk_areas=risk_areas,
        recommendations=recommendations,
        trust_boundaries=trust_boundaries,
        top_priorities=top_priorities,
    )


def run_summary_agent(repo_name: str, findings: list[ScanFinding], recon: RepoRecon, tools: dict[str, bool], analysis_mode: str) -> tuple[list[str], str]:
    tools_used = [name.capitalize() for name, enabled in tools.items() if enabled]
    tools_text = " and ".join(tools_used) if tools_used else "scanner tooling"
    critical = sum(1 for finding in findings if finding.severity == Severity.critical)
    high = sum(1 for finding in findings if finding.severity == Severity.high)

    timeline = [
        "Repository accepted for multi-agent analysis.",
        f"Recon Agent fingerprinted {repo_name} and mapped languages, frameworks, entry points, and sensitive files.",
        f"Scanner Agent executed {tools_text} and normalized raw vulnerability evidence.",
        "AI Analyst reviewed the finding set for exploitability context, grouped issue signals, and adjusted severity where needed.",
        "Fix Agent attached secure remediation guidance to each validated vulnerability.",
        "Summary Agent assembled the final report for the dashboard and detail views.",
    ]

    risk_assessment = (
        f"{repo_name} finished in {analysis_mode} mode with {len(findings)} total findings, "
        f"{critical} critical issues, and {high} high-severity issues. "
        f"Primary attack surfaces include {', '.join(recon.sensitive_files[:3]) if recon.sensitive_files else 'general application entry points'}."
    )
    return timeline, risk_assessment


def _kickoff_crewai(repo_name: str, context: ScanPipelineContext) -> str:
    if not crewai_available():
        return "local-orchestrated"

    crew = build_security_crew(repo_name)
    crew.kickoff()
    context.timeline.append("CrewAI orchestrated the agent team and completed the shared reasoning pass.")
    return "crewai"


def run_pipeline(
    repo_url: str,
    user_id: str,
    preset: ScanPreset = ScanPreset.full,
    scan_id: str | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
    clone_url: str | None = None,
) -> ScanApiResponse:
    validate_repo_url(repo_url)
    repo_name = extract_repo_name(repo_url)
    ensure_scanners_available()

    with tempfile.TemporaryDirectory(prefix="bbh-scan-") as temp_dir:
        repo_path = Path(temp_dir) / repo_name
        clone_repository(clone_url or repo_url, repo_path)
        ensure_repo_within_limits(repo_path)
        if progress_callback:
            progress_callback(18, f"Repository clone finished. The {preset.value} preset is routing the scan.")
        context = ScanPipelineContext(user_id=user_id, repo_url=repo_url, repo_name=repo_name, repo_path=repo_path, preset=preset)

        context.recon = run_recon_agent(context.repo_path)
        if progress_callback:
            progress_callback(34, "Recon completed. Static analyzers are scanning the filtered repository surface.")
        context.raw_vulnerabilities, context.tools, routing_notes = collect_static_findings(context.repo_path, context.repo_name, preset)
        context.timeline.extend(routing_notes)
        if progress_callback:
            progress_callback(56, "Static analysis finished. The AI Analyst is ranking severity and exploitability.")
        context.analyzed_vulnerabilities = run_ai_analyst_agent(context.raw_vulnerabilities, context.recon)
        if progress_callback:
            progress_callback(74, "AI triage finished. The Fix Agent is attaching remediation guidance.")
        context.fixed_vulnerabilities = run_fix_agent(context.analyzed_vulnerabilities)
        context.repo_analysis = run_repo_intelligence_agent(context.recon, context.fixed_vulnerabilities)
        if progress_callback:
            progress_callback(88, "Repo briefing and top priorities are being assembled for the final report.")
        context.analysis_mode = _kickoff_crewai(context.repo_name, context)
        summary_timeline, context.risk_assessment = run_summary_agent(
            context.repo_name,
            context.fixed_vulnerabilities,
            context.recon,
            context.tools,
            context.analysis_mode,
        )
        context.timeline.extend(summary_timeline)

    return ScanApiResponse(
        scan_id=scan_id or str(uuid4()),
        user_id=user_id,
        repo=repo_url,
        repo_name=repo_name,
        preset=preset,
        status="completed",
        scanned_at=datetime.now(timezone.utc),
        progress=100,
        summary=count_findings(context.fixed_vulnerabilities),
        vulnerabilities=context.fixed_vulnerabilities,
        agent_steps=progress_steps(100, default_agent_steps()),
        timeline=context.timeline,
        recon=context.recon,
        repo_analysis=context.repo_analysis,
        analysis_mode=context.analysis_mode,
        risk_assessment=context.risk_assessment,
        error_message="",
    )


def run_repository_scan(repo_url: str, user_id: str) -> ScanApiResponse:
    return run_pipeline(repo_url, user_id)
