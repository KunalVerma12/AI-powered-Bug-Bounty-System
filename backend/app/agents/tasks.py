from __future__ import annotations

from dataclasses import dataclass


try:
    from crewai import Task
except Exception:  # pragma: no cover - runtime optional dependency
    Task = None


@dataclass(frozen=True)
class TaskBlueprint:
    name: str
    agent_name: str
    description: str
    expected_output: str


def task_blueprints(repo_name: str) -> list[TaskBlueprint]:
    return [
        TaskBlueprint(
            name="recon",
            agent_name="Recon Agent",
            description=f"Analyze the repository structure for {repo_name}, infer languages/frameworks, identify entry points, and highlight sensitive files.",
            expected_output="JSON object with languages, frameworks, entry_points, sensitive_files, and architecture_summary.",
        ),
        TaskBlueprint(
            name="scan",
            agent_name="Scanner Agent",
            description=f"Collect and normalize Semgrep and Bandit findings for {repo_name} without executing repository code.",
            expected_output="JSON object with raw_vulnerabilities.",
        ),
        TaskBlueprint(
            name="analyze",
            agent_name="AI Analyst",
            description=f"Review normalized findings for {repo_name}, reduce false positives, escalate severity when context supports it, and improve descriptions.",
            expected_output="JSON object with analyzed_vulnerabilities.",
        ),
        TaskBlueprint(
            name="fix",
            agent_name="Fix Agent",
            description=f"Generate secure coding fixes and remediation explanations for each analyzed vulnerability in {repo_name}.",
            expected_output="JSON object with fixed_vulnerabilities.",
        ),
        TaskBlueprint(
            name="summary",
            agent_name="Summary Agent",
            description=f"Aggregate recon, findings, fixes, and severity posture for {repo_name} into a final risk assessment.",
            expected_output="JSON object with summary statistics, risk_assessment, and frontend-ready scan output.",
        ),
    ]


def build_crewai_tasks(agents: dict[str, object], repo_name: str) -> list[Task]:
    if Task is None:
        raise RuntimeError("CrewAI Task is unavailable.")

    tasks: list[Task] = []
    for blueprint in task_blueprints(repo_name):
        tasks.append(
            Task(
                description=blueprint.description,
                expected_output=blueprint.expected_output,
                agent=agents[blueprint.agent_name],
            )
        )
    return tasks
