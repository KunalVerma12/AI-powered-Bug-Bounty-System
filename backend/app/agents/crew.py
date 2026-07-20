from __future__ import annotations


try:
    from crewai import Crew
except Exception:  # pragma: no cover - runtime optional dependency
    Crew = None

try:
    from backend.app.agents.agents import build_crewai_agents
    from backend.app.agents.tasks import build_crewai_tasks
except ModuleNotFoundError:
    from app.agents.agents import build_crewai_agents
    from app.agents.tasks import build_crewai_tasks


def build_security_crew(repo_name: str) -> Crew:
    if Crew is None:
        raise RuntimeError("CrewAI is unavailable in this environment.")

    agents = build_crewai_agents()
    tasks = build_crewai_tasks(agents, repo_name)
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,
    )
