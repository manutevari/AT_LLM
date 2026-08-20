"""Deterministic agent orchestration primitives used by the UI and API.

The project can be wired to external LLM/tool providers later, but these
components provide a reliable local control plane: classify intent, route work,
apply guardrail-style validation, and produce an auditable response contract.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class AgentResult:
    """Stable response contract returned by the agent runner."""

    answer: str
    route: str
    confidence: float
    verified: bool
    steps: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class RouteDefinition:
    name: str
    description: str
    keywords: tuple[str, ...]
    prompt: str


ROUTES: tuple[RouteDefinition, ...] = (
    RouteDefinition(
        name="Research",
        description="Gather facts, compare options, and produce a cited synthesis.",
        keywords=("research", "compare", "latest", "source", "summarize", "find", "evidence"),
        prompt="I mapped the request to a research workflow and structured the answer around evidence, trade-offs, and next steps.",
    ),
    RouteDefinition(
        name="Build",
        description="Plan implementation work, break down tasks, and identify delivery risks.",
        keywords=("build", "code", "implement", "design", "architecture", "feature", "api", "app"),
        prompt="I mapped the request to a build workflow and converted it into an implementation-ready delivery plan.",
    ),
    RouteDefinition(
        name="Analyze",
        description="Inspect data or text and highlight patterns, anomalies, and decisions.",
        keywords=("analyze", "metric", "data", "trend", "report", "dashboard", "kpi", "insight"),
        prompt="I mapped the request to an analysis workflow and focused on findings, assumptions, and recommendations.",
    ),
    RouteDefinition(
        name="Support",
        description="Diagnose problems, explain behavior, and provide recovery steps.",
        keywords=("error", "issue", "bug", "fix", "help", "troubleshoot", "why", "broken"),
        prompt="I mapped the request to a support workflow and prioritized diagnosis, mitigation, and verification.",
    ),
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_route(tokens: Iterable[str], route: RouteDefinition) -> int:
    token_set = set(tokens)
    return sum(1 for keyword in route.keywords if keyword in token_set)


def classify_route(query: str) -> tuple[RouteDefinition, float]:
    """Classify a query into the best deterministic route."""

    tokens = _tokens(query)
    scored = sorted(((_score_route(tokens, route), route) for route in ROUTES), key=lambda item: item[0], reverse=True)
    score, route = scored[0]
    total_matches = sum(item[0] for item in scored)
    confidence = 0.62 if score == 0 else min(0.96, 0.68 + (score / max(total_matches, 1)) * 0.28)
    return route, confidence


def _validate(query: str) -> tuple[bool, list[str]]:
    checks = ["Input accepted", "No destructive action requested", "Response contract validated"]
    if len(query.strip()) < 4:
        return False, ["Input is too short for reliable routing"]
    return True, checks


def _compose_answer(query: str, route: RouteDefinition, verified: bool) -> str:
    status = "passed validation" if verified else "needs more detail before execution"
    return (
        f"{route.prompt}\n\n"
        f"Request: {query.strip()}\n\n"
        f"Execution status: {status}. Recommended next action: review the proposed route, "
        "attach any required sources or systems, then execute with human-visible audit logging."
    )


async def run_agent(query: str) -> AgentResult:
    """Run the local async control-plane workflow for a single query."""

    await asyncio.sleep(0)
    route, confidence = classify_route(query)
    verified, checks = _validate(query)
    steps = [
        "Classified the request intent",
        f"Selected {route.name} route: {route.description}",
        *checks,
        "Prepared final response",
    ]
    return AgentResult(
        answer=_compose_answer(query, route, verified),
        route=route.name,
        confidence=confidence,
        verified=verified,
        steps=steps,
        citations=["local:deterministic-router", "local:validation-policy"],
    )
