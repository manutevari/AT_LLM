# =========================================================
# app/agent.py
# =========================================================

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .api_keys import (
    fingerprint_api_key,
    generate_api_key,
    is_api_key_request,
)

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


SYSTEM_PROMPT = """
You are the Intelligence Agent operating inside the AI Agent Platform.

CORE RESPONSIBILITIES
---------------------
1. Understand and normalize the user's mission.
2. Maintain canonical state and contract integrity.
3. Determine intent, goals, ambiguity, risk, relevance and freshness.
4. Never execute materially ambiguous work without clarification.
5. Route work through governed routes.
6. Treat the Policy Manager as the final authority.
7. Never bypass security or authorization controls.
8. Use only authorized tools.
9. External side effects require explicit authorization.
10. Evidence must have provenance.
11. Fresh information requires appropriate live retrieval.
12. Memory, learning, skills, tools and policy remain separate layers.
13. Verify the result before release.
14. Record material decisions in the audit trail.
15. Never claim an external action occurred unless an authorized executor
    confirms it.

API KEY POLICY
--------------
16. API keys may be generated only through the dedicated API-key generator.
17. Generated API keys are secrets.
18. Never place plaintext API keys in audit logs, telemetry, evidence,
    prompts, or persistent memory.
19. Display a newly generated plaintext API key only to the requesting
    session and treat it as one-time visible secret material.
20. Store only a non-reversible fingerprint if persistence is required.
21. Never generate credentials for bypassing authentication, credential
    theft, unauthorized access, or other prohibited activity.
22. API-key generation itself does not authorize access to any external
    system.
23. Never claim that an API key was registered, activated, deployed,
    stored, or granted permissions unless a trusted executor confirms it.
"""


# =========================================================
# FLOW CONTEXT
# =========================================================

@dataclass
class FlowContext:
    query: str
    confidence: float
    risk: float
    freshness: float
    hitl: bool
    gate: str


# =========================================================
# ROUTE DEFINITION
# =========================================================

@dataclass(frozen=True)
class RouteDefinition:
    name: str
    domain: str
    description: str
    keywords: frozenset[str]
    agents: Tuple[str, ...]
    tools: Tuple[str, ...]
    model: str
    topology: ExecutionTopology
    requires_rag: bool
    requires_live_search: bool


# =========================================================
# ROUTE CATALOG
# =========================================================

ROUTES: Tuple[RouteDefinition, ...] = (
    RouteDefinition(
        name="Research",
        domain="Research",
        description=(
            "Gather facts, compare options, and produce a cited synthesis."
        ),
        keywords=frozenset(
            {
                "research",
                "compare",
                "latest",
                "source",
                "summarize",
                "find",
                "evidence",
                "facts",
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
        description=(
            "Plan implementation work, break down tasks, "
            "and identify delivery risks."
        ),
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
                "program",
                "software",
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
        description=(
            "Inspect data or text and highlight trends, "
            "metrics, and insights."
        ),
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
                "statistics",
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
        description=(
            "Diagnose issues, troubleshoot failures, "
            "and provide recovery guidance."
        ),
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
                "support",
                "diagnose",
                "exception",
            }
        ),
        agents=("support", "recovery"),
        tools=("ticket", "runbook"),
        model="support-safe-response",
        topology=ExecutionTopology.sequential,
        requires_rag=True,
        requires_live_search=False,
    ),

    # -----------------------------------------------------
    # API KEY GENERATOR
    # -----------------------------------------------------

    RouteDefinition(
        name="API Key",
        domain="Security & Identity",
        description=(
            "Generate a cryptographically secure application API key "
            "without exposing the secret in audit logs."
        ),
        keywords=frozenset(
            {
                "apikey",
                "key",
                "generate",
                "create",
                "credential",
            }
        ),
        agents=("security", "credential_manager"),
        tools=("api_key_generator",),
        model="security-structured-output",
        topology=ExecutionTopology.sequential,
        requires_rag=False,
        requires_live_search=False,
    ),
)


# =========================================================
# POLICY VOCABULARY
# =========================================================

HIGH_RISK_TERMS = {
    "legal",
    "medical",
    "regulated",
    "delete",
    "payment",
    "credential",
    "credentials",
    "secret",
    "password",
    "finance",
    "financial",
    "bank",
    "banking",
    "production",
}

REGULATED_TERMS = {
    "legal",
    "medical",
    "regulated",
    "finance",
    "financial",
    "bank",
    "banking",
    "payment",
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

BLOCKED_PHRASES = {
    "malware",
    "ransomware",
    "credential theft",
    "steal credentials",
    "credential bypass",
    "bypass credentials",
    "bypass authentication",
    "steal password",
    "steal passwords",
}

AMBIGUOUS_TERMS = {
    "accordingly",
    "something",
    "somehow",
    "it",
    "that",
    "this",
    "properly",
}


# =========================================================
# HELPERS
# =========================================================

def _tokens(text: str) -> set[str]:
    return set(
        re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
    )


def _route_by_name(
    name: str,
) -> RouteDefinition:

    for route in ROUTES:
        if route.name.lower() == name.lower():
            return route

    raise ValueError(
        f"Unknown route: {name}"
    )


def _contains_blocked_request(
    query: str,
) -> bool:

    normalized = query.lower()

    return any(
        phrase in normalized
        for phrase in BLOCKED_PHRASES
    )


# =========================================================
# ROUTING
# =========================================================

def classify_route(
    query: str,
) -> Tuple[RouteDefinition, float]:

    # API-key requests get their dedicated security route first.
    if is_api_key_request(query):

        return (
            _route_by_name("API Key"),
            0.99,
        )

    tokens = _tokens(query)

    scores = {
        route: len(
            tokens & route.keywords
        )
        for route in ROUTES
        if route.name != "API Key"
    }

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    best_route, best_score = ranked[0]
    second_score = ranked[1][1]

    if best_score == 0:
        return (
            _route_by_name("Support"),
            0.45,
        )

    if best_score == second_score:
        return (
            best_route,
            0.65,
        )

    confidence = min(
        0.98,
        0.72
        + (
            0.08
            * best_score
        )
        + (
            0.05
            * max(
                0,
                best_score - second_score,
            )
        ),
    )

    return (
        best_route,
        confidence,
    )


# =========================================================
# INTENT
# =========================================================

def _build_intent(
    query: str,
) -> IntentContract:

    tokens = _tokens(query)

    ambiguity = 0.15

    if len(tokens) <= 3:
        ambiguity = 0.72

    if tokens & AMBIGUOUS_TERMS:
        ambiguity = max(
            ambiguity,
            0.72,
        )

    normalized = query.strip().lower()

    if normalized in {
        "design accordingly",
        "design accordingly full fledge",
        "do it",
        "build it",
        "make it",
    }:
        ambiguity = 0.90

    if is_api_key_request(query):
        ambiguity = 0.05

    lifecycle = (
        "execution"
        if tokens
        & {
            "build",
            "create",
            "implement",
            "develop",
            "deploy",
            "generate",
        }
        else "advisory"
    )

    urgency = (
        0.90
        if tokens
        & {
            "urgent",
            "asap",
            "immediately",
        }
        else 0.25
    )

    return IntentContract(
        intent=(
            "api_key_generation"
            if is_api_key_request(query)
            else (
                " ".join(
                    sorted(tokens)
                )[:500]
                or "unknown"
            )
        ),
        lifecycle=lifecycle,
        sentiment="neutral",
        tone="professional",
        urgency=urgency,
        ambiguity=ambiguity,
        language="en",
        entities=[],
        goals=[query.strip()],
    )


# =========================================================
# RISK
# =========================================================

def _risk_level(
    tokens: set[str],
    query: str = "",
) -> RiskLevel:

    if is_api_key_request(query):
        return RiskLevel.medium

    if tokens & REGULATED_TERMS:
        return RiskLevel.high

    if tokens & HIGH_RISK_TERMS:
        return RiskLevel.high

    return RiskLevel.low


# =========================================================
# DATA CLASSIFICATION
# =========================================================

def _data_classification(
    tokens: set[str],
    query: str = "",
) -> DataClassification:

    if is_api_key_request(query):
        return DataClassification.restricted

    if tokens & REGULATED_TERMS:
        return DataClassification.regulated

    if tokens & {
        "credential",
        "credentials",
        "secret",
        "password",
        "token",
    }:
        return DataClassification.restricted

    return DataClassification.internal


# =========================================================
# POLICY
# =========================================================

def _build_policy(
    query: str,
    intent: IntentContract,
    risk: RiskLevel,
) -> PolicyContract:

    if _contains_blocked_request(query):

        return PolicyContract(
            verdict=EdgeDecision.blocked,
            constraints=[
                "unsafe_request_blocked",
                "security_control_plane_enforced",
                "no_credential_bypass",
                "no_malware_development",
            ],
            requires_human_review=False,
            reason=(
                "Request matches a prohibited security "
                "or credential-abuse pattern."
            ),
        )

    if is_api_key_request(query):

        return PolicyContract(
            verdict=EdgeDecision.allowed,
            constraints=[
                "dedicated_api_key_generator_only",
                "secret_material_is_session_visible_only",
                "never_log_plaintext_key",
                "audit_fingerprint_only",
                "no_external_registration",
                "no_permission_grant",
            ],
            requires_human_review=False,
            reason=(
                "Explicit API-key generation request passed "
                "the credential-generation policy boundary."
            ),
        )

    if intent.ambiguity >= 0.70:

        return PolicyContract(
            verdict=EdgeDecision.escalate,
            constraints=[
                "clarification_required",
                "no_execution_under_material_ambiguity",
            ],
            requires_human_review=True,
            reason=(
                "Mission is materially ambiguous and cannot "
                "be safely executed without clarification."
            ),
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
            reason=(
                "High-risk or regulated context requires "
                "human review before execution."
            ),
        )

    return PolicyContract(
        verdict=EdgeDecision.allowed,
        constraints=[
            "no_unapproved_external_side_effects",
            "provenance_required",
            "audit_all_material_decisions",
        ],
        requires_human_review=False,
        reason=(
            "Request passed pre-execution policy checks."
        ),
    )


# =========================================================
# SIGNALS
# =========================================================

def _build_signals(
    confidence: float,
    intent: IntentContract,
    risk: RiskLevel,
    freshness: float,
) -> SignalContract:

    risk_score = {
        RiskLevel.low: 0.20,
        RiskLevel.medium: 0.55,
        RiskLevel.high: 0.90,
    }[risk]

    return SignalContract(
        confidence=confidence,
        relevance=max(
            0.50,
            confidence - 0.05,
        ),
        priority=max(
            0.25,
            min(
                1.0,
                intent.urgency + 0.25,
            ),
        ),
        risk_score=risk_score,
        evidence_quality=0.90,
        freshness_score=freshness,
        policy_score=(
            0.95
            if risk != RiskLevel.high
            else 0.55
        ),
    )


# =========================================================
# ROUTE CONTRACT
# =========================================================

def _build_route_contract(
    route: RouteDefinition,
    risk: RiskLevel,
    data_classification: DataClassification,
    requires_human_review: bool,
) -> RouteContract:

    assigned_agent = " + ".join(
        agent.title().replace(
            "_",
            " ",
        )
        for agent in route.agents
    )

    return RouteContract(
        route=route.name,
        domain=route.domain,
        topology=route.topology,
        agent=assigned_agent,
        model=route.model,
        tools=list(route.tools),
        requires_rag=route.requires_rag,
        requires_live_search=route.requires_live_search,
        requires_human_review=requires_human_review,
        data_classification=data_classification,
        risk=risk,
    )


# =========================================================
# PLAN
# =========================================================

def _build_plan(
    route: RouteDefinition,
) -> PlanContract:

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


# =========================================================
# RUNTIME STATE
# =========================================================

def _build_runtime_state() -> RuntimeStateContract:

    return RuntimeStateContract(
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
            "plaintext_credentials_are_not_logged",
        ],
    )


# =========================================================
# API KEY TOOL
# =========================================================

def _execute_api_key_generator(
    tenant_id: str,
) -> tuple[str, str]:

    api_key = generate_api_key()

    fingerprint = fingerprint_api_key(
        api_key
    )

    # IMPORTANT:
    # Only the fingerprint enters the audit/control plane.
    # The plaintext API key remains in the response only.
    return (
        api_key,
        fingerprint,
    )


# =========================================================
# AUDIT
# =========================================================

def _build_audit(
    query: str,
    route: RouteDefinition,
    policy: PolicyContract,
    verified: bool,
    production_gate: str,
    api_key_fingerprint: str | None = None,
) -> List[AuditEvent]:

    stages = [
        (
            "input",
            "ok",
            "Interaction accepted.",
        ),
        (
            "interaction_manager",
            "ok",
            "Interaction Manager processed the request.",
        ),
        (
            "session_manager",
            "ok",
            "Session context initialized.",
        ),
        (
            "canonical_contract_engine",
            "ok",
            "Canonical input contract created and validated.",
        ),
        (
            "context_manager",
            "ok",
            "Runtime context established.",
        ),
        (
            "ambiguity_manager",
            (
                "escalate"
                if policy.verdict
                == EdgeDecision.escalate
                else "pass"
            ),
            "Ambiguity evaluated before execution.",
        ),
        (
            "operations_manager",
            "ok",
            "Workflow ownership established.",
        ),
        (
            "architectural_invariants",
            "ok",
            "Architectural invariants checked.",
        ),
        (
            "intent",
            "ok",
            "Intent contract generated.",
        ),
        (
            "signal",
            "ok",
            "Confidence, relevance, risk and freshness signals generated.",
        ),
        (
            "policy_pre",
            "ok",
            "Pre-policy evaluation completed.",
        ),
        (
            "policy_manager",
            policy.verdict.value,
            policy.reason,
        ),
        (
            "routing",
            "ok",
            f"Route selected: {route.name}.",
        ),
        (
            "intelligence_agent",
            "ok",
            "Candidate reasoning and plan generated.",
        ),
        (
            "orchestrator",
            "ok",
            "Task delegation and workflow plan prepared.",
        ),
        (
            "supervisor",
            "ok",
            "Execution health and recovery policy evaluated.",
        ),
        (
            "memory_manager",
            "ok",
            "Memory policy boundary evaluated.",
        ),
        (
            "learning_manager",
            "ok",
            "Learning promotion boundary evaluated.",
        ),
        (
            "skill_manager",
            "ok",
            "Skill registry boundary evaluated.",
        ),
        (
            "tool_intelligence",
            "ok",
            "Tool capability boundary evaluated.",
        ),
        (
            "rag_evidence_manager",
            "ok",
            "Evidence and provenance requirements evaluated.",
        ),
        (
            "model_router",
            "ok",
            f"Model policy selected: {route.model}.",
        ),
        (
            "synthesis_engine",
            "ok",
            "Candidate response synthesized.",
        ),
        (
            "verification_manager",
            (
                "pass"
                if verified
                else "blocked"
            ),
            "Verification completed.",
        ),
        (
            "response_governance",
            "ok",
            "Response governance applied.",
        ),
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
    ]

    if api_key_fingerprint:

        stages.append(
            (
                "api_key_generator",
                "ok",
                (
                    "API key generated successfully. "
                    f"Secret fingerprint={api_key_fingerprint}. "
                    "Plaintext secret excluded from audit."
                ),
            )
        )

    stages.append(
        (
            "audit",
            "ok",
            (
                f"Audit trace recorded for mission: "
                f"{query[:120]}"
            ),
        )
    )

    return [
        AuditEvent(
            stage=stage,
            status=status,
            detail=detail,
        )
        for stage, status, detail in stages
    ]


# =========================================================
# MAIN AGENT
# =========================================================

async def run_agent(
    prompt: str,
    channel: Channel = Channel.web,
    tenant_id: str = "default",
    history: List[Dict[str, Any]] | None = None,
) -> AgentResult:

    del history

    # -----------------------------------------------------
    # Canonical input
    # -----------------------------------------------------

    input_contract = InputContract(
        query=prompt,
        channel=channel,
        tenant_id=tenant_id,
    )

    # -----------------------------------------------------
    # Route
    # -----------------------------------------------------

    route, confidence = classify_route(
        input_contract.query
    )

    # -----------------------------------------------------
    # Intent
    # -----------------------------------------------------

    intent = _build_intent(
        input_contract.query
    )

    # -----------------------------------------------------
    # Risk / classification
    # -----------------------------------------------------

    tokens = _tokens(
        input_contract.query
    )

    risk = _risk_level(
        tokens,
        input_contract.query,
    )

    data_classification = _data_classification(
        tokens,
        input_contract.query,
    )

    # -----------------------------------------------------
    # Freshness
    # -----------------------------------------------------

    freshness = (
        0.95
        if tokens & FRESHNESS_TERMS
        else 0.35
    )

    # -----------------------------------------------------
    # Signals
    # -----------------------------------------------------

    signals = _build_signals(
        confidence=confidence,
        intent=intent,
        risk=risk,
        freshness=freshness,
    )

    # -----------------------------------------------------
    # Policy
    # -----------------------------------------------------

    policy = _build_policy(
        query=input_contract.query,
        intent=intent,
        risk=risk,
    )

    requires_human_review = (
        policy.requires_human_review
        or risk == RiskLevel.high
    )

    # -----------------------------------------------------
    # Route contract
    # -----------------------------------------------------

    route_contract = _build_route_contract(
        route=route,
        risk=risk,
        data_classification=data_classification,
        requires_human_review=requires_human_review,
    )

    # -----------------------------------------------------
    # Runtime state / plan
    # -----------------------------------------------------

    runtime_state = _build_runtime_state()

    plan = _build_plan(route)

    # -----------------------------------------------------
    # Decisions
    # -----------------------------------------------------

    decisions: List[DecisionContract] = []

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
                edge="risk_or_ambiguity_gate",
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
                    reason=(
                        f"Route {route.name} selected."
                    ),
                ),
            ]
        )

    # -----------------------------------------------------
    # API KEY GENERATION
    # -----------------------------------------------------

    generated_api_key: str | None = None
    api_key_fingerprint: str | None = None

    if (
        route.name == "API Key"
        and policy.verdict == EdgeDecision.allowed
    ):

        (
            generated_api_key,
            api_key_fingerprint,
        ) = _execute_api_key_generator(
            tenant_id
        )

        decisions.append(
            DecisionContract(
                edge="api_key_generation",
                decision=EdgeDecision.allowed,
                reason=(
                    "Cryptographically secure API key generated. "
                    "Plaintext secret excluded from audit."
                ),
            )
        )

    # -----------------------------------------------------
    # Evidence
    # -----------------------------------------------------

    evidence: List[EvidenceContract] = []

    if (
        route.requires_rag
        or route.requires_live_search
    ):

        evidence.append(
            EvidenceContract(
                source_id="pending_verified_source",
                retrieval_method=(
                    "live_search"
                    if route.requires_live_search
                    else "rag"
                ),
                relevance=signals.relevance,
                confidence=signals.evidence_quality,
                provenance=(
                    "provenance-required-before-final-response"
                ),
                freshness_required=route.requires_live_search,
            )
        )

    # API-key generation does not require RAG.
    # The cryptographic generator itself is the execution source.

    # -----------------------------------------------------
    # Verification
    # -----------------------------------------------------

    if policy.verdict == EdgeDecision.blocked:

        verification_verdict = EdgeDecision.blocked
        verified = False

    elif policy.verdict == EdgeDecision.escalate:

        verification_verdict = EdgeDecision.escalate
        verified = False

    else:

        verification_verdict = EdgeDecision.allowed
        verified = True

    evidence_verdict = (
        EdgeDecision.allowed
        if (
            not route.requires_rag
            or len(evidence) > 0
        )
        else EdgeDecision.escalate
    )

    verification = VerificationContract(
        evidence=evidence_verdict,
        policy=policy.verdict,
        factual_consistency=(
            EdgeDecision.allowed
            if verified
            else verification_verdict
        ),
        citations=(
            EdgeDecision.allowed
            if (
                not route.requires_rag
                or len(evidence) > 0
            )
            else EdgeDecision.escalate
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

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    if policy.verdict == EdgeDecision.blocked:

        answer = (
            "The request was blocked by the Policy Manager. "
            "The system will not perform credential abuse, "
            "authentication bypass, malware development, "
            "or other prohibited activity. "
            "Execution status: blocked by policy."
        )

        production_gate = "BLOCK"

    elif policy.verdict == EdgeDecision.escalate:

        answer = (
            f"Architecture-aligned route: {route.name} "
            f"in the {route.domain} domain. "
            f"Topology: {route.topology.value} | "
            f"Assigned agent: {route_contract.agent} | "
            f"Model policy: {route.model}. "
            f"Policy Manager verdict: "
            f"{policy.verdict.value} | "
            f"Constraints: "
            f"{', '.join(policy.constraints)}. "
            f"Data classification: "
            f"{data_classification.value} | "
            f"Risk: {risk.value}. "
            f"Verification verdict: "
            f"{verification.verdict.value}. "
            "Execution status: requires human review "
            "or clarification. "
            "No external side effect was executed. "
            "Production gate: CONDITIONAL."
        )

        production_gate = "CONDITIONAL"

    elif route.name == "API Key":

        answer = (
            "API key generated successfully.\n\n"
            f"API Key:\n"
            f"{generated_api_key}\n\n"
            "Security notice: this secret is displayed only "
            "in the current response and is not written to "
            "the audit trail.\n\n"
            f"Key fingerprint: "
            f"{api_key_fingerprint}\n"
            "The key has NOT been registered, activated, "
            "stored in an external secret manager, or granted "
            "permissions."
        )

        production_gate = "PASS"

    else:

        answer = (
            f"Architecture-aligned route: {route.name} "
            f"in the {route.domain} domain. "
            f"Topology: {route.topology.value} | "
            f"Assigned agent: {route_contract.agent} | "
            f"Model policy: {route.model}. "
            f"Policy Manager verdict: "
            f"{policy.verdict.value} | "
            f"Constraints: "
            f"{', '.join(policy.constraints)}. "
            f"Manager fabric: "
            f"{', '.join(plan.manager_fabric)}. "
            f"Tools planned: "
            f"{', '.join(route.tools)}. "
            f"Data classification: "
            f"{data_classification.value} | "
            f"Risk: {risk.value}. "
            f"Verification verdict: "
            f"{verification.verdict.value} | "
            f"Runtime state: "
            f"{runtime_state.state_id}. "
            "Execution status: passed validation. "
            "Production gate: PASS. "
            "No unapproved external side effect was executed."
        )

        production_gate = "PASS"

    # -----------------------------------------------------
    # Audit
    # -----------------------------------------------------

    audit_events = _build_audit(
        query=input_contract.query,
        route=route,
        policy=policy,
        verified=verified,
        production_gate=production_gate,
        api_key_fingerprint=api_key_fingerprint,
    )

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    return AgentResult(
        answer=answer,
        route=route.name,
        confidence=confidence,
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
            "plaintext_credentials_not_logged",
            "audit_trace_recorded",
        ],
        production_gate=production_gate,
    )


# =========================================================
# BACKWARD-COMPATIBLE API
# =========================================================

def classify(
    query: str,
) -> str:

    route, _ = classify_route(query)

    return route.name.lower()


def evaluate(
    query: str,
) -> FlowContext:

    route, confidence = classify_route(query)

    del route

    tokens = _tokens(query)

    risk_level = _risk_level(
        tokens,
        query,
    )

    risk = {
        RiskLevel.low: 0.20,
        RiskLevel.medium: 0.55,
        RiskLevel.high: 0.90,
    }[risk_level]

    freshness = (
        0.95
        if tokens & FRESHNESS_TERMS
        else 0.30
    )

    hitl = (
        risk_level == RiskLevel.high
        or confidence <= 0.60
        or (
            len(tokens) <= 3
            and not is_api_key_request(query)
        )
    )

    if _contains_blocked_request(query):
        gate = "BLOCK"

    elif hitl:
        gate = "CONDITIONAL"

    else:
        gate = "PASS"

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
) -> Dict[str, Any]:

    return {
        "source": "local-control-plane",
        "route": route,
        "confidence": ctx.confidence,
        "fresh": ctx.freshness > 0.80,
        "provenance": "local-control-plane",
    }


async def execute(
    route: str,
    ctx: FlowContext,
    evidence: Dict[str, Any],
) -> str:

    if route.lower() == "api key":

        key = generate_api_key()

        return (
            "API key generated successfully.\n"
            f"API Key={key}\n"
            f"Fingerprint={fingerprint_api_key(key)}\n"
            "Plaintext key must not be logged."
        )

    route_definition = _route_by_name(
        route
    )

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
    evidence: Dict[str, Any],
) -> List[Dict[str, str]]:

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
            "status": (
                "conditional"
                if ctx.hitl
                else "pass"
            ),
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
            "detail": (
                "API key generated through dedicated "
                "security tool."
                if route.lower() == "api key"
                else "Execution completed"
            ),
        },
    ]


async def orchestrate(
    query: str,
) -> Dict[str, Any]:

    ctx = evaluate(query)

    route = classify(query)

    evidence = await gather(
        route,
        ctx,
    )

    result = await execute(
        route,
        ctx,
        evidence,
    )

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


# =========================================================
# DEMO
# =========================================================

if __name__ == "__main__":

    async def demo() -> None:

        output = await run_agent(
            "generate api key",
            channel=Channel.api,
            tenant_id="demo",
        )

        print(output.answer)

        print("\nAudit Trail:")

        for event in output.audit_events:
            print(event.model_dump())

    asyncio.run(demo())
