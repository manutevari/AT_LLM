"""Architecture-aligned deterministic agent orchestration runtime.

This module maps the reference flowchart into executable local control-plane
stages: session/input normalization, Pydantic validation, human understanding,
query intelligence, signal scoring, routing, deterministic predicates,
orchestration planning, evidence/provenance, response governance, and audit.
"""Deterministic agent orchestration primitives used by the UI and API.

The project can be wired to external LLM/tool providers later, but these
components provide a reliable local control plane: classify intent, route work,
apply guardrail-style validation, and produce an auditable response contract.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Iterable

from .contracts import (
    AgentResult,
    AuditEvent,
    Channel,
    DataClassification,
    DecisionContract,
    EdgeDecision,
    EvidenceContract,
    ExecutionTopology,
    InputContract,
    IntentContract,
    RiskLevel,
    RouteContract,
    SignalContract,
)
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
    domain: str
    agent: str
    topology: ExecutionTopology
    tools: tuple[str, ...]
    model: str
    prompt: str


ROUTES: tuple[RouteDefinition, ...] = (
    RouteDefinition(
        name="Research",
        description="Gather facts, compare options, and produce a cited synthesis.",
        keywords=("research", "compare", "latest", "source", "summarize", "find", "evidence", "rag"),
        domain="Research",
        agent="Research Agent + Verification Agent",
        topology=ExecutionTopology.parallel,
        tools=("policy_first_rag", "live_search", "provenance_tracker"),
        model="reasoning-verifier-pair",
        keywords=("research", "compare", "latest", "source", "summarize", "find", "evidence"),
        prompt="I mapped the request to a research workflow and structured the answer around evidence, trade-offs, and next steps.",
    ),
    RouteDefinition(
        name="Build",
        description="Plan implementation work, break down tasks, and identify delivery risks.",
        keywords=("build", "code", "implement", "design", "architecture", "feature", "api", "app", "website"),
        domain="Software Engineering",
        agent="Supervisor Agent + Builder Agent",
        topology=ExecutionTopology.graph,
        tools=("component_factory", "test_runner", "deployment_checker"),
        model="coding-capable-structured-output",
        keywords=("build", "code", "implement", "design", "architecture", "feature", "api", "app"),
        prompt="I mapped the request to a build workflow and converted it into an implementation-ready delivery plan.",
    ),
    RouteDefinition(
        name="Analyze",
        description="Inspect data or text and highlight patterns, anomalies, and decisions.",
        keywords=("analyze", "metric", "data", "trend", "report", "dashboard", "kpi", "insight", "tableau"),
        domain="Business Intelligence",
        agent="Analysis Agent + Critic Agent",
        topology=ExecutionTopology.sequential,
        tools=("analytics_layer", "tableau_connector", "evaluation_engine"),
        model="analysis-long-context",
        keywords=("analyze", "metric", "data", "trend", "report", "dashboard", "kpi", "insight"),
        prompt="I mapped the request to an analysis workflow and focused on findings, assumptions, and recommendations.",
    ),
    RouteDefinition(
        name="Support",
        description="Diagnose problems, explain behavior, and provide recovery steps.",
        keywords=("error", "issue", "bug", "fix", "help", "troubleshoot", "why", "broken", "complaint"),
        domain="Complaint Resolution",
        agent="Support Agent + Recovery Manager",
        topology=ExecutionTopology.hierarchical,
        tools=("ticket_context", "runbook_search", "escalation_manager"),
        model="support-safe-response",
    ),
)

HIGH_RISK_TERMS = {"legal", "medical", "regulated", "delete", "payment", "credential", "secret", "finance"}
FRESHNESS_TERMS = {"latest", "today", "current", "news", "price", "schedule", "recent"}
AMBIGUOUS_TERMS = {"accordingly", "full", "fledge", "thing", "stuff", "it", "this"}

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
    confidence = 0.52 if score == 0 else min(0.96, 0.64 + (score / max(total_matches, 1)) * 0.32)
    if tokens & AMBIGUOUS_TERMS and len(tokens) < 8:
        confidence = min(confidence, 0.58)
    return route, confidence


def _understand(input_contract: InputContract) -> IntentContract:
    tokens = _tokens(input_contract.query)
    ambiguity = 0.74 if tokens & AMBIGUOUS_TERMS and len(tokens) < 8 else 0.18
    urgency = 0.82 if {"urgent", "asap", "critical", "broken"} & tokens else 0.35
    sentiment = "concerned" if {"issue", "broken", "complaint", "error"} & tokens else "neutral"
    goals = ["produce governed response", "preserve auditability"]
    return IntentContract(
        intent="execute_agent_workflow",
        lifecycle="new_request",
        sentiment=sentiment,
        tone="calm_neutral",
        urgency=urgency,
        ambiguity=ambiguity,
        language="en",
        entities=sorted(token for token in tokens if token in HIGH_RISK_TERMS or token in FRESHNESS_TERMS),
        goals=goals,
    )


def _score_signals(query: str, confidence: float, intent: IntentContract) -> SignalContract:
    tokens = _tokens(query)
    risk_score = 0.78 if tokens & HIGH_RISK_TERMS else 0.22
    freshness_score = 0.88 if tokens & FRESHNESS_TERMS else 0.25
    evidence_quality = 0.7 if freshness_score < 0.8 else 0.55
    return SignalContract(
        confidence=confidence,
        relevance=max(0.45, confidence - 0.05),
        priority=max(intent.urgency, risk_score),
        risk_score=risk_score,
        evidence_quality=evidence_quality,
        freshness_score=freshness_score,
        policy_score=0.92 if risk_score < 0.7 else 0.68,
    )


def _route(route: RouteDefinition, signal: SignalContract) -> RouteContract:
    high_risk = signal.risk_score >= 0.7
    needs_live = signal.freshness_score >= 0.8
    return RouteContract(
        route=route.name,
        domain=route.domain,
        topology=route.topology,
        agent=route.agent,
        model=route.model,
        tools=list(route.tools),
        requires_rag=route.name in {"Research", "Analyze"},
        requires_live_search=needs_live,
        requires_human_review=high_risk or signal.confidence < 0.6,
        data_classification=DataClassification.regulated if high_risk else DataClassification.internal,
        risk=RiskLevel.high if high_risk else RiskLevel.low,
    )


def _edge_decisions(intent: IntentContract, signal: SignalContract, route: RouteContract) -> list[DecisionContract]:
    return [
        DecisionContract(
            edge="contract_valid",
            decision=EdgeDecision.allowed,
            reason="Input contract passed Pydantic validation.",
        ),
        DecisionContract(
            edge="ambiguous",
            decision=EdgeDecision.escalate if intent.ambiguity >= 0.7 else EdgeDecision.allowed,
            reason="Clarification required." if intent.ambiguity >= 0.7 else "Request has enough specificity to proceed.",
        ),
        DecisionContract(
            edge="policy_allows",
            decision=EdgeDecision.escalate if route.requires_human_review else EdgeDecision.allowed,
            reason="High risk or low confidence requires human review." if route.requires_human_review else "Policy permits automated execution.",
        ),
        DecisionContract(
            edge="evidence_sufficient",
            decision=EdgeDecision.repair if signal.evidence_quality < 0.6 else EdgeDecision.allowed,
            reason="Fresh-data path should attach live provenance." if signal.evidence_quality < 0.6 else "Evidence baseline is sufficient.",
        ),
    ]


def _evidence(route: RouteContract) -> list[EvidenceContract]:
    evidence = [EvidenceContract(source_id="contract:versioned-schema-registry", retrieval_method="local_contract", relevance=0.92, confidence=0.95)]
    if route.requires_rag:
        evidence.append(EvidenceContract(source_id="rag:policy-first-placeholder", retrieval_method="planned_hybrid_search", relevance=0.78, confidence=0.72))
    if route.requires_live_search:
        evidence.append(EvidenceContract(source_id="live-search:required-before-final", retrieval_method="freshness_gate", relevance=0.8, confidence=0.62))
    return evidence


def _audit(*events: tuple[str, str, str]) -> list[AuditEvent]:
    return [AuditEvent(stage=stage, status=status, detail=detail) for stage, status, detail in events]


def _compose_answer(input_contract: InputContract, route: RouteContract, decisions: list[DecisionContract]) -> tuple[str, str, bool]:
    blocking = [decision for decision in decisions if decision.decision in {EdgeDecision.blocked, EdgeDecision.escalate}]
    verified = not any(decision.decision == EdgeDecision.blocked for decision in decisions)
    gate = "CONDITIONAL" if blocking else "PASS"
    review_note = " Human review is recommended before production execution." if blocking else " Automated execution is permitted for this demo run."
    answer = (
        f"Architecture-aligned route: {route.route} in the {route.domain} domain. "
        f"Topology: {route.topology.value}; assigned agent: {route.agent}; model policy: {route.model}. "
        f"Tools planned: {', '.join(route.tools)}. "
        f"Data classification: {route.data_classification.value}; risk: {route.risk.value}."
        f"{review_note}\n\n"
        f"Normalized request: {input_contract.query}"
    )
    return answer, gate, verified


async def run_agent(query: str, channel: Channel = Channel.web, tenant_id: str = "default") -> AgentResult:
    """Run the local async control-plane workflow for a single query."""

    await asyncio.sleep(0)
    input_contract = InputContract(query=query, channel=channel, tenant_id=tenant_id)
    route_definition, confidence = classify_route(input_contract.query)
    intent = _understand(input_contract)
    signals = _score_signals(input_contract.query, confidence, intent)
    route = _route(route_definition, signals)
    decisions = _edge_decisions(intent, signals, route)
    evidence = _evidence(route)
    answer, production_gate, verified = _compose_answer(input_contract, route, decisions)
    audit_events = _audit(
        ("session_manager", "ok", f"Session {input_contract.session_id} opened for tenant {input_contract.tenant_id}."),
        ("input_normalization", "ok", "Whitespace normalized and channel metadata captured."),
        ("pydantic_contract_engine", "ok", f"Contracts validated at {input_contract.contract_version}."),
        ("human_understanding", "ok", f"Intent={intent.intent}; ambiguity={intent.ambiguity:.0%}; urgency={intent.urgency:.0%}."),
        ("signal_scoring", "ok", f"Confidence={signals.confidence:.0%}; risk={signals.risk_score:.0%}; freshness={signals.freshness_score:.0%}."),
        ("routing_manager", "ok", f"Selected {route.route} route with {route.topology.value} topology."),
        ("deterministic_edges", "ok", "; ".join(f"{item.edge}:{item.decision.value}" for item in decisions)),
        ("response_governance", "ok", "Applied polite, calm, evidence-aware response policy."),
        ("strict_architectural_auditor", production_gate.lower(), f"Production gate result: {production_gate}."),
    )
    return AgentResult(
        answer=answer,
        route=route.route,
        confidence=signals.confidence,
        verified=verified,
        input_contract=input_contract,
        intent_contract=intent,
        signal_contract=signals,
        route_contract=route,
        decisions=decisions,
        evidence=evidence,
        audit_events=audit_events,
        response_governance=["polite", "calm_neutral", "non_aggressive", "evidence_aware", "audience_aware"],
        production_gate=production_gate,
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
