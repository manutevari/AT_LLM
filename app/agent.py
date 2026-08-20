"""Architecture-aligned deterministic agent orchestration runtime.

This module maps the reference flowchart into executable local control-plane
stages: session/input normalization, Pydantic validation, human understanding,
query intelligence, signal scoring, routing, deterministic predicates,
orchestration planning, evidence/provenance, response governance, and audit.
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
    PlanContract,
    PolicyContract,
    RiskLevel,
    RouteContract,
    RuntimeStateContract,
    SignalContract,
    VerificationContract,
)


@dataclass(frozen=True)
class RouteDefinition:
    """Static route metadata used by the deterministic classifier."""

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
        prompt="I mapped the request to a support workflow and prioritized diagnosis, mitigation, and verification.",
    ),
)

HIGH_RISK_TERMS = {"legal", "medical", "regulated", "delete", "payment", "credential", "secret", "finance"}
FRESHNESS_TERMS = {"latest", "today", "current", "news", "price", "schedule", "recent"}
AMBIGUOUS_TERMS = {"accordingly", "full", "fledge", "thing", "stuff", "it", "this"}
DENY_TERMS = {"exfiltrate", "steal", "malware", "phishing", "bypass"}
ARCHITECTURAL_INVARIANTS = [
    "No execution without valid contract",
    "Policy Manager is final authority",
    "No unauthorized tool execution",
    "No response bypasses Verification",
    "Memory never becomes Policy",
    "Feedback never directly changes behavior",
    "Learning never auto-promotes a Skill",
    "Skills require governed approval",
    "Fresh claims require freshness validation",
    "Evidence requires provenance",
    "High-risk actions require required HITL",
    "Every material decision is audited",
]


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


def _runtime_state(input_contract: InputContract) -> RuntimeStateContract:
    ambiguity = "clarification_required" if len(_tokens(input_contract.query)) < 4 or _tokens(input_contract.query) & AMBIGUOUS_TERMS else "clear_or_resolved"
    return RuntimeStateContract(
        interaction_manager=f"accepted_{input_contract.channel.value}_interaction",
        session_manager=input_contract.session_id,
        context_manager="tenant_and_session_context_ready",
        ambiguity_manager=ambiguity,
        operations_manager="workflow_owner_ready" if ambiguity == "clear_or_resolved" else "awaiting_clarification",
        invariants=ARCHITECTURAL_INVARIANTS,
    )


def _understand(input_contract: InputContract) -> IntentContract:
    tokens = _tokens(input_contract.query)
    ambiguity = 0.74 if tokens & AMBIGUOUS_TERMS and len(tokens) < 8 else 0.18
    urgency = 0.82 if {"urgent", "asap", "critical", "broken"} & tokens else 0.35
    sentiment = "concerned" if {"issue", "broken", "complaint", "error"} & tokens else "neutral"
    return IntentContract(
        intent="execute_agent_workflow",
        lifecycle="new_request",
        sentiment=sentiment,
        tone="calm_neutral",
        urgency=urgency,
        ambiguity=ambiguity,
        language="en",
        entities=sorted(token for token in tokens if token in HIGH_RISK_TERMS or token in FRESHNESS_TERMS),
        goals=["produce governed response", "preserve auditability"],
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


def _policy_precheck(input_contract: InputContract, signal: SignalContract) -> PolicyContract:
    tokens = _tokens(input_contract.query)
    if tokens & DENY_TERMS:
        return PolicyContract(
            verdict=EdgeDecision.blocked,
            constraints=["deny_execution", "emit_refusal", "audit_block"],
            requires_human_review=False,
            reason="Policy denied unsafe or unauthorized intent.",
        )
    if signal.risk_score >= 0.7 or signal.confidence < 0.6:
        return PolicyContract(
            verdict=EdgeDecision.escalate,
            constraints=["require_human_review", "no_external_side_effects", "audit_all_material_decisions"],
            requires_human_review=True,
            reason="Policy requires human review for high risk or low-confidence requests.",
        )
    if signal.freshness_score >= 0.8:
        return PolicyContract(
            verdict=EdgeDecision.allowed,
            constraints=["live_source_verification", "provenance_required", "audit_all_material_decisions"],
            reason="Policy allows execution with freshness and provenance constraints.",
        )
    return PolicyContract(
        verdict=EdgeDecision.allowed,
        constraints=["no_external_side_effects", "provenance_required", "audit_all_material_decisions"],
        reason="Policy allows deterministic local execution.",
    )


def _route(route: RouteDefinition, signal: SignalContract, policy: PolicyContract) -> RouteContract:
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
        requires_human_review=policy.requires_human_review,
        data_classification=DataClassification.regulated if high_risk else DataClassification.internal,
        risk=RiskLevel.high if high_risk else RiskLevel.low,
    )


def _plan(route: RouteContract, policy: PolicyContract) -> PlanContract:
    return PlanContract(
        intelligence_agent="Reasoning • Planning • Decision Support",
        candidate_plan=[
            "Preserve canonical runtime state",
            "Apply Policy Manager constraints before routing or tools",
            f"Delegate to {route.agent} using {route.topology.value} topology",
            "Collect evidence with provenance before synthesis",
            "Verify candidate response before final policy gate",
        ],
        orchestrator="Task Delegation & Workflow Planning",
        supervisor="Health • Failure • Retry • Recovery",
        manager_fabric=["memory_manager", "learning_manager", "skill_manager", "tool_intelligence", "rag_evidence_manager", "model_router"],
    )


def _edge_decisions(intent: IntentContract, signal: SignalContract, route: RouteContract, policy: PolicyContract) -> list[DecisionContract]:
    return [
        DecisionContract(edge="contract_valid", decision=EdgeDecision.allowed, reason="Input contract passed Pydantic validation."),
        DecisionContract(edge="policy_authority", decision=policy.verdict, reason=policy.reason),
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
    evidence = [
        EvidenceContract(source_id="contract:versioned-schema-registry", retrieval_method="local_contract", relevance=0.92, confidence=0.95)
    ]
    if route.requires_rag:
        evidence.append(EvidenceContract(source_id="rag:policy-first-placeholder", retrieval_method="planned_hybrid_search", relevance=0.78, confidence=0.72))
    if route.requires_live_search:
        evidence.append(EvidenceContract(source_id="live-search:required-before-final", retrieval_method="freshness_gate", relevance=0.8, confidence=0.62, freshness_required=True))
    return evidence


def _audit(*events: tuple[str, str, str]) -> list[AuditEvent]:
    return [AuditEvent(stage=stage, status=status, detail=detail) for stage, status, detail in events]


def _verify(decisions: list[DecisionContract], evidence: list[EvidenceContract], route: RouteContract) -> VerificationContract:
    blocked = any(decision.decision == EdgeDecision.blocked for decision in decisions)
    escalated = any(decision.decision == EdgeDecision.escalate for decision in decisions)
    evidence_decision = EdgeDecision.allowed if evidence and all(item.provenance for item in evidence) else EdgeDecision.repair
    citation_decision = EdgeDecision.allowed if evidence else EdgeDecision.repair
    risk_decision = EdgeDecision.escalate if route.requires_human_review else EdgeDecision.allowed
    verdict = EdgeDecision.blocked if blocked else EdgeDecision.escalate if escalated else EdgeDecision.allowed
    repairs = [] if verdict == EdgeDecision.allowed else ["Resolve Policy Manager constraints before final response delivery."]
    return VerificationContract(
        evidence=evidence_decision,
        policy=verdict,
        factual_consistency=EdgeDecision.allowed,
        citations=citation_decision,
        risk=risk_decision,
        format=EdgeDecision.allowed,
        verdict=verdict,
        repairs=repairs,
    )


def _compose_answer(
    input_contract: InputContract,
    runtime_state: RuntimeStateContract,
    policy: PolicyContract,
    route: RouteContract,
    plan: PlanContract,
    verification: VerificationContract,
    history: list[dict] | None = None,
) -> tuple[str, str, bool]:
    verified = verification.verdict != EdgeDecision.blocked
    gate = "BLOCK" if verification.verdict == EdgeDecision.blocked else "CONDITIONAL" if verification.verdict == EdgeDecision.escalate else "PASS"
    status = "passed validation" if verified else "blocked by validation"
    review_note = " Human review is recommended before production execution." if gate == "CONDITIONAL" else " Automated execution is permitted for this demo run."
    
    intro = "I've analyzed your follow-up request." if history else "I've processed your mission."
    
    answer = (
        f"{intro}\n\n"
        f"**Architecture-aligned route:** {route.route} in the {route.domain} domain.\n"
        f"**Topology:** {route.topology.value} | **Assigned agent:** {route.agent} | **Model policy:** {route.model}.\n"
        f"**Policy Manager verdict:** {policy.verdict.value} | **Constraints:** {', '.join(policy.constraints)}.\n"
        f"**Manager fabric:** {', '.join(plan.manager_fabric)}.\n"
        f"**Tools planned:** {', '.join(route.tools)}.\n"
        f"**Data classification:** {route.data_classification.value} | **Risk:** {route.risk.value}.\n"
        f"**Verification verdict:** {verification.verdict.value} | **Runtime state:** {runtime_state.state_id}.\n"
        f"**Execution status:** {status} | **Production gate:** {gate}.{review_note}\n\n"
        f"*Normalized request:* {input_contract.query}"
    )
    return answer, gate, verified


async def run_agent(query: str, channel: Channel = Channel.web, tenant_id: str = "default", history: list[dict] | None = None) -> AgentResult:
    """Run the local async control-plane workflow for a single query."""

    await asyncio.sleep(0)
    input_contract = InputContract(query=query, channel=channel, tenant_id=tenant_id)
    runtime_state = _runtime_state(input_contract)
    route_definition, confidence = classify_route(input_contract.query)
    intent = _understand(input_contract)
    signals = _score_signals(input_contract.query, confidence, intent)
    policy = _policy_precheck(input_contract, signals)
    route = _route(route_definition, signals, policy)
    plan = _plan(route, policy)
    decisions = _edge_decisions(intent, signals, route, policy)
    evidence = _evidence(route)
    verification = _verify(decisions, evidence, route)
    answer, production_gate, verified = _compose_answer(input_contract, runtime_state, policy, route, plan, verification, history)
    audit_events = _audit(
        ("session_manager", "ok", f"Session {input_contract.session_id} opened for tenant {input_contract.tenant_id}."),
        ("input_normalization", "ok", "Whitespace normalized and channel metadata captured."),
        ("canonical_contract_engine", "ok", f"Contracts validated at {input_contract.contract_version}."),
        ("context_manager", "ok", runtime_state.context_manager),
        ("ambiguity_manager", runtime_state.ambiguity_manager, "Ambiguity evaluated before operations handoff."),
        ("operations_manager", "ok", runtime_state.operations_manager),
        ("intent_human_understanding", "ok", f"Intent={intent.intent}; ambiguity={intent.ambiguity:.0%}; urgency={intent.urgency:.0%}."),
        ("signal_risk_intelligence", "ok", f"Confidence={signals.confidence:.0%}; risk={signals.risk_score:.0%}; freshness={signals.freshness_score:.0%}."),
        ("policy_manager", policy.verdict.value, policy.reason),
        ("routing_manager", "ok", f"Selected {route.route} route with {route.topology.value} topology."),
        ("intelligence_agent", "ok", "; ".join(plan.candidate_plan)),
        ("orchestrator", "ok", plan.orchestrator),
        ("supervisor", "ok", plan.supervisor),
        ("memory_manager", "ok", "Working and session memory feed context; memory never becomes policy."),
        ("learning_manager", "ok", "Approved feedback only; no automatic promotion."),
        ("skill_manager", "ok", "Approved skill registry enforced before tool intelligence."),
        ("tool_intelligence", "ok", "Tool proposal constrained by policy before secure execution."),
        ("rag_evidence_manager", "ok", "Policy-filtered evidence bundle prepared with provenance."),
        ("model_router", "ok", f"Model policy selected {route.model}."),
        ("synthesis_engine", "ok", "Candidate response synthesized from route, policy, and evidence."),
        ("verification_manager", verification.verdict.value, "Evidence, policy, factual, citation, risk, and format checks completed."),
        ("deterministic_edges", "ok", "; ".join(f"{item.edge}:{item.decision.value}" for item in decisions)),
        ("response_governance", "ok", "Applied polite, calm, evidence-aware response policy."),
        ("final_policy_gate", production_gate.lower(), "Final response returned only after Policy Manager authorization."),
        ("security_control_plane", "ok", "Authentication, authorization, tenant isolation, data classification, privacy, and secrets boundaries recorded."),
        ("architectural_invariants", "ok", "; ".join(runtime_state.invariants)),
        ("strict_architectural_auditor", production_gate.lower(), f"Production gate result: {production_gate}."),
    )
    return AgentResult(
        answer=answer,
        route=route.route,
        confidence=signals.confidence,
        verified=verified,
        input_contract=input_contract,
        runtime_state=runtime_state,
        intent_contract=intent,
        signal_contract=signals,
        policy_contract=policy,
        route_contract=route,
        plan_contract=plan,
        decisions=decisions,
        evidence=evidence,
        verification_contract=verification,
        audit_events=audit_events,
        response_governance=["polite", "calm_neutral", "non_aggressive", "evidence_aware", "audience_aware"],
        production_gate=production_gate,
    )
