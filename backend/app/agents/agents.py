from __future__ import annotations

import os
from dataclasses import dataclass


try:
    from crewai import Agent
except Exception:  # pragma: no cover - runtime optional dependency
    Agent = None


@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    goal: str
    backstory: str


def agent_profiles() -> list[AgentProfile]:
    return [
        AgentProfile(
            name="Recon Agent",
            role="Repository Intelligence Analyst",
            goal="Understand repository structure, languages, frameworks, and sensitive files before any findings are interpreted.",
            backstory="An experienced application security architect who can quickly fingerprint source trees and identify risky entry points.",
        ),
        AgentProfile(
            name="Scanner Agent",
            role="Static Security Scanner",
            goal="Collect and normalize Semgrep and Bandit output without executing repository code.",
            backstory="A disciplined static-analysis specialist focused on high-signal evidence and reproducible scanner output.",
        ),
        AgentProfile(
            name="AI Analyst",
            role="Security Intelligence Analyst",
            goal="Correlate findings, reduce false positives, escalate severity when exploitability context is strong, and add clearer explanations.",
            backstory="A senior bug bounty triager who reasons about exploitability, reachability, and issue clustering across codebases.",
        ),
        AgentProfile(
            name="Fix Agent",
            role="Remediation Expert",
            goal="Translate findings into practical secure coding guidance and concrete fix recommendations.",
            backstory="A security-minded staff engineer who specializes in shipping safe fixes developers can apply quickly.",
        ),
        AgentProfile(
            name="Summary Agent",
            role="Report Generator",
            goal="Aggregate agent outputs into a concise risk story, severity breakdown, and frontend-ready final report.",
            backstory="A technical reporting lead who turns noisy security telemetry into portfolio-grade summaries for engineering teams.",
        ),
    ]


def crewai_available() -> bool:
    return Agent is not None and bool(os.environ.get("OPENAI_API_KEY"))


def build_crewai_agents() -> dict[str, Agent]:
    if not crewai_available():
        raise RuntimeError("CrewAI is unavailable or OPENAI_API_KEY is not configured.")

    agents: dict[str, Agent] = {}
    for profile in agent_profiles():
        agents[profile.name] = Agent(
            role=profile.role,
            goal=profile.goal,
            backstory=profile.backstory,
            allow_delegation=True,
            verbose=True,
        )
    return agents
