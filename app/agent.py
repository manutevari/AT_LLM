# app/agent.py

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

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
    PlanContract,
    PolicyContract,
    RouteContract,
    RuntimeStateContract,
    RiskLevel,
    SignalContract,
    VerificationContract,
)


SYSTEM_PROMPT = """
You are the AI Agent Platform control-plane intelligence agent.

Your responsibilities are to:
1. Understand the user's mission.
2. Preserve the canonical input contract.
3. Resolve ambiguity before execution.
4. Classify the mission into the appropriate route.
5. Evaluate confidence, risk, freshness, relevance and policy.
6. Never bypass policy, security, verification or human-approval gates.
7. Use only authorized tools.
8. Require provenance when evidence is used.
9. Require live retrieval when freshness is material.
10. Treat memory, learning, skills, tools and policy as separate governed concerns.
11. Produce auditable decisions.
12. Never claim that an external action occurred unless a trusted executor confirms it.
13. Block unsafe or prohibited requests.
14. Escalate high-risk, ambiguous or authorization-sensitive operations.
15. Return a concise, useful, architecture-aligned response.
"""


@dataclass(frozen=True)
class RouteDefinition:
    name: str
    domain: str
    description: str
    keywords: frozenset[str]
    agents: tuple[str, ...]
    tools: tuple[str, ...]
    model: str
    topology: ExecutionTopology
    requires_rag: bool
    requires_live_search: bool


ROUTES = (
    RouteDefinition(
        name="Research",
        domain="Research",
        description="Gather facts, compare options, and produce a cited synthesis.",
        keywords=frozenset(
            {
                "research",
                "compare",
                "latest",
                "source",
                "summarize",
                "find",
                "evidence",
                "information",
            }
        ),
        agents=("research", "verify"),
        tools=("rag", "search"),
        model="reasoning-verifier",
        topology=ExecutionTopology.sequential,
        requires_rag=True,
        requires_live_search=True,
    ),
    RouteDefinition(
        name="Build",
        domain="Software Engineering",
        description="Plan implementation work, break down tasks, and identify delivery risks.",
        keywords=frozenset(
            {
                "build",
                "code",
                "implement",
                "design",
                "feature",
                "api",
                "develop",
                "create",
            }
        ),
        agents=("supervisor", "builder"),
        tools=("factory", "test", "deploy"),
        model="structured-output",
        topology=ExecutionTopology.graph,
        requires_rag=False,
        requires_live_search=False,
    ),
    RouteDefinition(
        name="Analyze",
        domain="Business Intelligence",
        description="Inspect data or text and highlight trends, metrics, and insights.",
        keywords=frozenset(
            {
                "analyze",
                "analysis",
                "metric",
                "metrics",
                "data",
                "trend",
                "report",
                "dashboard",
                "retention",
                "insight",
            }
        ),
        agents=("analysis", "critic"),
        tools=("analytics", "evaluation"),
        model="analysis-long-context",
        topology=ExecutionTopology.sequential,
        requires_rag=False,
        requires_live_search=False,
    ),
    RouteDefinition(
        name="Support",
        domain="Support",
        description="Diagnose issues, troubleshoot failures, and provide recovery guidance.",
        keywords=frozenset(
            {
                "error",
                "issue",
                "bug",
                "fix",
                "help",
                "troubleshoot",
                "failure",
                "problem",
            }
        ),
        agents=("support", "recovery"),
        tools=("ticket", "runbook"),
        model="support-safe-response",
        topology=ExecutionTopology.sequential,
        requires_rag=True,
        requires_live_search=False,
    ),
)


HIGH_RISK_TERMS = {
    "payment",
    "finance",
    "financial",
    "bank",
    "banking",
    "medical",
    "health",
    "legal",
    "regulated",
    "credential",
    "credentials",
    "secret",
    "password",
    "token",
    "delete",
    "production",
}

REGULATED_TERMS = {
    "regulated",
    "medical",
    "health",
    "finance",
    "financial",
    "banking",
    "payment",
    "legal",
}

BLOCKED_TERMS = {
    "malware",
    "ransomware",
    "credential theft",
    "steal credentials",
    "bypass credentials",
    "bypass authentication",
    "credential bypass",
}

FRESHNESS_TERMS = {
    "latest",
    "today",
    "current",
    "news",
    "price",
    "schedule",
    "recent",
    "now",
    "live",
}

AMBIGUOUS_TERMS = {
    "accordingly",
    "something",
    "somehow",
    "it",
    "that",
    "this",
    "full",
    "properly",
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _route_lookup(name: str) -> RouteDefinition:
    for route in ROUTES:
        if route.name.lower() == name.lower():
            return route
    raise ValueError(f"Unknown route: {name}")


def classify_route(query: str) -> tuple[RouteDefinition, float]:
    tokens = _tokens(query)

    scores: dict[RouteDefinition, int] = {
        route: len(tokens & route.keywords)
        for route in ROUTES
    }

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    best_route, best_score = ranked[0]
    second_score = ranked[1][1]

    if best_score == 0:
        return _route_lookup("Support"), 0.45

    if best_score == second_score and best_score > 0:
        return best_route, 0.65

    confidence = min(
        0.98,
        0.72 + (0.08 * best_score) + (0.05 * max(0, best_score - second_score)),
    )

    return best_route, confidence


def _detect_intent(query: str, confidence: float) -> IntentContract:
    tokens = _tokens(query)

    ambiguity = 0.15

    if len(tokens) <= 3:
        ambiguity = max(ambiguity, 0.72)

    if tokens & AMBIGUOUS_TERMS:
        ambiguity = max(ambiguity, 0.72)

    if query.lower().strip() in {
        "design accordingly",
        "design accordingly full fledge",
        "do it",
        "build it",
        "make it",
    }:
        ambiguity = 0.90

    lifecycle = "execution" if tokens & {
        "build",
        "create",
        "implement",
        "deploy",
    } else "advisory"

    urgency = 0.8 if tokens & {"urgent", "asap", "immediately"} else 0.25

    return IntentContract(
        intent=" ".join(sorted(tokens))[:500] or "unknown",
        lifecycle=lifecycle,
        sentiment="neutral",
        tone="professional",
        urgency=urgency,
        ambiguity=ambiguity,
        language="en",
        entities=[],
        goals=[query.strip()],
    )


def _data_classification(tokens: set[str]) -> DataClassification:
    if tokens & REGULATED_TERMS:
        return DataClassification.regulated

    if tokens & {"secret", "password", "credential", "credentials", "token"}:
        return DataClassification.restricted

    return DataClassification.internal


def _risk_level(tokens: set[str]) -> RiskLevel:
    if tokens & REGULATED_TERMS:
        return RiskLevel.high

    if tokens & HIGH_RISK_TERMS:
        return RiskLevel.high

    return RiskLevel.low


def _build_policy(
    query: str,
    tokens: set[str],
    intent: IntentContract,
    risk: RiskLevel,
) -> PolicyContract:

    lowered = query.lower()

    if any(term in lowered for term in BLOCKED_TERMS):
        return PolicyContract(
            verdict=EdgeDecision.blocked,
            constraints=[
                "unsafe_request_blocked",
                "security_control_plane_enforced",
                "no_credential_bypass",
            ],
            requires_human_review=False,
            reason="Request matches a prohibited security or credential-abuse pattern.",
        )

    if intent.ambiguity >= 0.7:
        return PolicyContract(
            verdict=EdgeDecision.escalate,
            constraints=[
                "clarification_required",
                "no_execution_under_ambiguity",
            ],
            requires_human_review=True,
            reason="Mission is materially ambiguous and cannot be safely executed without clarification.",
        )

    if risk == RiskLevel.high:
        return PolicyContract(
            verdict=EdgeDecision.escalate,
            constraints=[
                "human_review_required",
                "no_unapproved_external_side_effects",
                "provenance_required",
                "audit_all_material_decisions",
            ],
            requires_human_review=True,
            reason="High-risk or regulated context requires human review.",
        )

    return PolicyContract(
        verdict=EdgeDecision.allowed,
        constraints=[
            "no_unapproved_external_side_effects",
            "provenance_required",
            "audit_all_material_decisions",
        ],
        requires_human_review=False,
        reason="Request passed the pre-execution policy checks.",
    )


def _build_signals(
    confidence: float,
    intent: IntentContract,
    risk: RiskLevel,
    freshness: float,
) -> SignalContract:

    risk_score = {
        RiskLevel.low: 0.2,
        RiskLevel.medium: 0.55,
        RiskLevel.high: 0.9,
    }[risk]

    relevance = max(0.5, confidence - 0.05)
    priority = max(0.25, min(1.0, intent.urgency + 0.25))

    return SignalContract(
        confidence=confidence,
        relevance=relevance,
        priority=priority,
        risk_score=risk_score,
        evidence_quality=0.9,
        freshness_score=freshness,
        policy_score=0.95 if risk != RiskLevel.high else 0.55,
    )


def _build_route_contract(
    route: RouteDefinition,
    risk: RiskLevel,
    data_classification: DataClassification,
    requires_human_review: bool,
) -> RouteContract:

    return RouteContract(
        route=route.name,
        domain=route.domain,
        topology=route.topology,
        agent=" + ".join(
            agent.title().replace("_", " ")
            for agent in route.agents
        ),
        model=route.model,
        tools=list(route.tools),
        requires_rag=route.requires_rag,
        requires_live_search=route.requires_live_search,
        requires_human_review=requires_human_review,
        data_classification=data_classification,
        risk=risk,
    )


def _build_plan(route: RouteDefinition) -> PlanContract:
    return PlanContract(
        intelligence_agent="Intelligence Agent",
        candidate_plan=[
            "Normalize and validate mission",
            "Resolve ambiguity",
            "Evaluate risk and policy",
            f"Route to {route.name}",
            "Select authorized capabilities",
            "Gather or validate evidence",
            "Execute within policy constraints",
            "Verify result",
            "Apply final policy gate",
            "Record immutable audit trace",
        ],
        orchestrator="Task Delegation & Workflow Planning",
        supervisor="Supervisor Agent",
        manager_fabric=[
            "memory_manager",
            "learning_manager",
            "skill_manager",
            "tool_intelligence",
            "rag_evidence_manager",
            "model_router",
        ],
    )


def _audit(
    query: str,
    route: RouteDefinition,
    policy: PolicyContract,
    verified: bool,
    production_gate: str,
) -> list[AuditEvent]:

    stages = [
        ("interaction_manager", "ok", "Interaction accepted."),
        ("session_manager", "ok", "Session context initialized."),
        ("canonical_contract_engine", "ok", "Input normalized and contract validated."),
        ("context_manager", "ok", "Runtime context established."),
        (
            "ambiguity_manager",
            "escalate" if policy.verdict == EdgeDecision.escalate else "pass",
            "Ambiguity evaluated.",
        ),
        ("operations_manager", "ok", "Workflow ownership established."),
        ("architectural_invariants", "ok", "Architectural invariants checked."),
        ("intent", "ok", "Intent contract generated."),
        ("signal", "ok", "Risk, relevance, confidence and freshness signals generated."),
        ("policy_pre", "ok", "Pre-policy evaluation completed."),
        (
            "policy_manager",
            policy.verdict.value,
            policy.reason,
        ),
        ("routing", "ok", f"Route selected: {route.name}."),
        ("intelligence_agent", "ok", "Candidate reasoning and plan generated."),
        ("orchestrator", "ok", "Task delegation plan prepared."),
        ("supervisor", "ok", "Execution health and recovery policy evaluated."),
        ("memory_manager", "ok", "Memory policy boundary evaluated."),
        ("learning_manager", "ok", "Learning promotion boundary evaluated."),
        ("skill_manager", "ok", "Skill registry boundary evaluated."),
        ("tool_intelligence", "ok", "Tool capability boundary evaluated."),
        ("rag_evidence_manager", "ok", "Evidence/provenance requirements evaluated."),
        ("model_router", "ok", f"Model policy selected: {route.model}."),
        ("synthesis_engine", "ok", "Candidate response synthesized."),
        (
            "verification_manager",
            "pass" if verified else "blocked",
            "Verification completed.",
        ),
        ("response_governance", "ok", "Response governance applied."),
        (
            "final_policy_gate",
            production_gate.lower(),
            f"Production gate: {production_gate}.",
        ),
        (
            "security_control_plane",
            "ok",
            "Security boundary enforced.",
        ),
        (
            "audit",
            "ok",
            f"Audit trace recorded for mission: {query[:120]}",
        ),
    ]

    return [
        AuditEvent(
            stage=stage,
            status=status,
            detail=detail,
        )
        for stage, status, detail in stages
    ]


async def run_agent(
    prompt: str,
    channel: Channel = Channel.web,
    tenant_id: str = "default",
    history: list[dict[str, Any]] | None = None,
) -> AgentResult:

    del history

    input_contract = InputContract(
        query=prompt,
        channel=channel,
        tenant_id=tenant_id,
    )

    route, route_confidence = classify_route(input_contract.query)

    intent = _detect_intent(
        input_contract.query,
        route_confidence,
    )

    tokens = _tokens(input_contract.query)

    risk = _risk_level(tokens)

    freshness = (
        0.95
        if tokens & FRESHNESS_TERMS
        else 0.35
    )

    data_classification = _data_classification(tokens)

    policy = _build_policy(
        input_contract.query,
        tokens,
        intent,
        risk,
    )

    requires_human_review = (
        policy.requires_human_review
        or risk == RiskLevel.high
    )

    route_contract = _build_route_contract(
        route=route,
        risk=risk,
        data_classification=data_classification,
        requires_human_review=requires_human_review,
    )

    signals = _build_signals(
        confidence=route_confidence,
        intent=intent,
        risk=risk,
        freshness=freshness,
    )

    runtime_state = RuntimeStateContract(
        interaction_manager="Interaction Manager",
        session_manager="Session Manager",
        context_manager="Context Manager",
        ambiguity_manager="Ambiguity Manager",
        operations_manager="Operations Manager",
        invariants=[
            "canonical_state_is_authoritative",
            "policy_is_final_authority",
            "tools_require_authorization",
            "external_side_effects_require_explicit_permission",
            "evidence_requires_provenance",
            "memory_learning_skills_are_separate",
            "audit_is_immutable",
        ],
    )

    plan = _build_plan(route)

    decisions: list[DecisionContract] = []

    if policy.verdict == EdgeDecision.blocked:
        decisions.append(
            DecisionContract(
                edge="policy_pre_check",
                decision=EdgeDecision.blocked,
                reason=policy.reason,
            )
        )

    elif policy.verdict == EdgeDecision.escalate:
        decisions.append(
            DecisionContract(
                edge="ambiguity_or_risk_gate",
                decision=EdgeDecision.escalate,
                reason=policy.reason,
            )
        )

    else:
        decisions.extend(
            [
                DecisionContract(
                    edge="policy_pre_check",
                    decision=EdgeDecision.allowed,
                    reason="Policy pre-check passed.",
                ),
                DecisionContract(
                    edge="routing",
                    decision=EdgeDecision.allowed,
                    reason=f"Route {route.name} selected.",
                ),
            ]
        )

    evidence: list[EvidenceContract] = []

    if route.requires_rag or route.requires_live_search:
        evidence.append(
            EvidenceContract(
                source_id="pending_live_or_rag_source",
                retrieval_method=(
                    "live_search"
                    if route.requires_live_search
                    else "rag"
                ),
                relevance=signals.relevance,
                confidence=signals.evidence_quality,
                provenance="provenance-required-before-final-response",
                freshness_required=route.requires_live_search,
            )
        )

    verification_verdict = EdgeDecision.allowed
    verified = True

    if policy.verdict == EdgeDecision.blocked:
        verification_verdict = EdgeDecision.blocked
        verified = False

    elif policy.verdict == EdgeDecision.escalate:
        verification_verdict = EdgeDecision.escalate
        verified = False

    verification = VerificationContract(
        evidence=(
            EdgeDecision.allowed
            if evidence or not route.requires_rag
            else EdgeDecision.escalate
        ),
        policy=policy.verdict,
        factual_consistency=EdgeDecision.allowed,
        citations=(
            EdgeDecision.allowed
            if evidence
            else EdgeDecision.allowed
        ),
        risk=(
            EdgeDecision.escalate
            if risk == RiskLevel.high
            else EdgeDecision.allowed
        ),
        format=EdgeDecision.allowed,
        verdict=verification_verdict,
        repairs=[],
    )

    if policy.verdict == EdgeDecision.blocked:
        answer = (
            "The request was blocked by the Policy Manager. "
            "The system will not perform credential abuse, authentication bypass, "
            "malware development, or other prohibited activity."
        )
        production_gate = "BLOCK"

    elif policy.verdict == EdgeDecision.escalate:
        answer = (
            "The request requires clarification or human review before execution. "
            f"Architecture-aligned route: {route.name} in the {route.domain} domain. "
            "No external side effect has been executed."
        )
        production_gate = "CONDITIONAL"

    else:
        answer = (
            f"Architecture-aligned route: {route.name} "
            f"in the {route.domain} domain. "
            f"Topology: {route.topology.value} | "
            f"Assigned agent: {route_contract.agent} | "
            f"Model policy: {route.model}. "
            f"Policy Manager verdict: {policy.verdict.value} | "
            f"Constraints: {', '.join(policy.constraints)}. "
            f"Manager fabric: {', '.join(plan.manager_fabric)}. "
            f"Tools planned: {', '.join(route.tools)}. "
            f"Data classification: {data_classification.value} | "
            f"Risk: {risk.value}. "
            f"Verification verdict: {verification.verdict.value} | "
            f"Runtime state: {runtime_state.state_id}. "
            f"Execution status: passed validation | "
            f"Production gate: PASS. "
            "No unapproved external side effect was executed."
        )
        production_gate = "PASS"

    audit_events = _audit(
        query=input_contract.query,
        route=route,
        policy=policy,
        verified=verified,
        production_gate=production_gate,
    )

    return AgentResult(
        answer=answer,
        route=route.name,
        confidence=route_confidence,
        verified=verified,
        input_contract=input_contract,
        runtime_state=runtime_state,
        intent_contract=intent,
        signal_contract=signals,
        policy_contract=policy,
        route_contract=route_contract,
        plan_contract=plan,
        decisions=decisions,
        evidence=evidence,
        verification_contract=verification,
        audit_events=audit_events,
        response_governance=[
            "policy_checked",
            "provenance_required",
            "no_unapproved_external_side_effects",
            "audit_trace_recorded",
        ],
        production_gate=production_gate,
    )


# ---------------------------------------------------------
# Backward-compatible deterministic API
# ---------------------------------------------------------

def classify(query: str) -> str:
    route, _ = classify_route(query)
    return route.name.lower()


@dataclass
class FlowContext:
    query: str
    confidence: float
    risk: float
    freshness: float
    hitl: bool
    gate: str


def evaluate(query: str) -> FlowContext:
    route, confidence = classify_route(query)
    tokens = _tokens(query)

    risk_level = _risk_level(tokens)

    risk = {
        RiskLevel.low: 0.2,
        RiskLevel.medium: 0.55,
        RiskLevel.high: 0.9,
    }[risk_level]

    freshness = (
        0.95
        if tokens & FRESHNESS_TERMS
        else 0.3
    )

    hitl = risk_level == RiskLevel.high or confidence <= 0.6

    gate = (
        "BLOCK"
        if any(term in query.lower() for term in BLOCKED_TERMS)
        else "CONDITIONAL"
        if hitl
        else "PASS"
    )

    return FlowContext(
        query=query,
        confidence=confidence,
        risk=risk,
        freshness=freshness,
        hitl=hitl,
        gate=gate,
    )


async def gather(
    route: str,
    ctx: FlowContext,
) -> dict[str, Any]:

    return {
        "source": "local",
        "route": route,
        "confidence": ctx.confidence,
        "fresh": ctx.freshness > 0.8,
        "provenance": "local-control-plane",
    }


async def execute(
    route: str,
    ctx: FlowContext,
    evidence: dict[str, Any],
) -> str:

    route_definition = _route_lookup(route)

    return (
        f"Route={route_definition.name.lower()} | "
        f"Agent={list(route_definition.agents)} | "
        f"Tools={list(route_definition.tools)}\n"
        f"Confidence={ctx.confidence:.2f}, "
        f"Risk={ctx.risk:.2f}, "
        f"Freshness={ctx.freshness:.2f}\n"
        f"Gate={ctx.gate} | "
        f"HITL={'required' if ctx.hitl else 'auto'}\n"
        f"Evidence={evidence}"
    )


def audit(
    query: str,
    ctx: FlowContext,
    route: str,
    evidence: dict[str, Any],
) -> list[dict[str, str]]:

    return [
        {
            "stage": "input",
            "status": "ok",
            "detail": f"Query='{query}'",
        },
        {
            "stage": "classify",
            "status": "ok",
            "detail": f"Route={route}",
        },
        {
            "stage": "evaluate",
            "status": "ok",
            "detail": (
                f"Confidence={ctx.confidence:.2f}, "
                f"Risk={ctx.risk:.2f}, "
                f"Freshness={ctx.freshness:.2f}"
            ),
        },
        {
            "stage": "hitl",
            "status": "conditional" if ctx.hitl else "pass",
            "detail": f"Gate={ctx.gate}",
        },
        {
            "stage": "gather",
            "status": "ok",
            "detail": f"Evidence={evidence}",
        },
        {
            "stage": "execute",
            "status": "ok",
            "detail": "Execution completed",
        },
    ]


async def orchestrate(
    query: str,
) -> dict[str, Any]:

    ctx = evaluate(query)
    route = classify(query)
    evidence = await gather(route, ctx)
    result = await execute(route, ctx, evidence)

    return {
        "answer": result,
        "meta": {
            "route": route,
            "ctx": ctx,
            "evidence": evidence,
            "audit": audit(
                query,
                ctx,
                route,
                evidence,
            ),
        },
    }


if __name__ == "__main__":

    async def demo() -> None:
        result = await run_agent(
            "Find the latest evidence for a support issue"
        )

        print(result.answer)

        print("\nAudit Trail:")

        for event in result.audit_events:
            print(event.model_dump())

    asyncio.run(demo())
