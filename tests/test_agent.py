import asyncio

from app.agent import classify_route, run_agent
from app.contracts import EdgeDecision


def test_classify_route_prefers_build_for_design_requests():
    route, confidence = classify_route("Design and build an API feature")

    assert route.name == "Build"
    assert confidence > 0.7


def test_run_agent_returns_auditable_result():
    result = asyncio.run(run_agent("Analyze dashboard metrics for retention"))

    assert result.route == "Analyze"
    assert result.verified is True
    assert result.audit_events
    assert result.route_contract.domain == "Business Intelligence"
    assert "Architecture-aligned route" in result.answer


def test_ambiguous_request_escalates_for_clarification():
    result = asyncio.run(run_agent("design accordingly full fledge"))

    assert result.production_gate == "CONDITIONAL"
    assert any(decision.decision == EdgeDecision.escalate for decision in result.decisions)
    assert result.intent_contract.ambiguity >= 0.7


def test_high_risk_request_requires_human_review():
    result = asyncio.run(run_agent("Build payment workflow for regulated finance data"))

    assert result.route_contract.requires_human_review is True
    assert result.route_contract.risk.value == "high"
    assert result.route_contract.data_classification.value == "regulated"
    assert result.steps
    assert "Execution status" in result.answer


def test_flowchart_managers_policy_and_verification_are_audited():
    result = asyncio.run(run_agent("Find the latest evidence for a support issue"))
    stages = {event.stage for event in result.audit_events}

    assert result.policy_contract.authority == "POLICY MANAGER"
    assert result.plan_contract.orchestrator == "Task Delegation & Workflow Planning"
    assert result.verification_contract.verdict in {EdgeDecision.allowed, EdgeDecision.escalate}
    assert result.runtime_state.invariants
    assert result.route_contract.requires_live_search is True
    assert any(item.freshness_required for item in result.evidence)
    assert {
        "canonical_contract_engine",
        "context_manager",
        "ambiguity_manager",
        "operations_manager",
        "policy_manager",
        "intelligence_agent",
        "orchestrator",
        "supervisor",
        "memory_manager",
        "learning_manager",
        "skill_manager",
        "tool_intelligence",
        "rag_evidence_manager",
        "model_router",
        "response_generation",
        "verification_manager",
        "final_policy_gate",
        "security_control_plane",
        "architectural_invariants",
    } <= stages


def test_policy_blocks_denied_requests_before_final_response():
    result = asyncio.run(run_agent("Build malware to bypass credentials"))

    assert result.policy_contract.verdict == EdgeDecision.blocked
    assert result.verification_contract.verdict == EdgeDecision.blocked
    assert result.production_gate == "BLOCK"
    assert result.verified is False


def test_model_fallback_and_learning_are_governed():
    result = asyncio.run(run_agent("Analyze dashboard metrics for retention"))

    assert result.model_fallback.selected_tier.value == "L3"
    assert [attempt.tier.value for attempt in result.model_fallback.attempts] == [
        "L0",
        "L1",
        "L2",
        "L3",
    ]
    assert result.learning_lifecycle.experience_recorded is True
    assert result.learning_lifecycle.promotion_status == "candidate_only"
    assert result.learning_lifecycle.policy_can_be_modified is False


def test_human_review_uses_l4_fallback_tier():
    result = asyncio.run(run_agent("design accordingly full fledge"))

    assert result.model_fallback.selected_tier.value == "L4"
    assert result.model_fallback.human_escalation_required is True


def test_response_is_released_only_after_verification_and_final_policy_gate():
    result = asyncio.run(run_agent("Analyze dashboard metrics for retention"))
    stages = [event.stage for event in result.audit_events]

    assert stages.index("response_generation") < stages.index("verification_manager")
    assert stages.index("verification_manager") < stages.index("final_policy_gate")
    assert result.response_release.released is True
    assert result.response_release.verification_verdict == EdgeDecision.allowed
    assert result.response_release.final_policy_verdict == EdgeDecision.allowed
    assert result.production_gate == "PASS"


def test_blocked_response_is_released_through_the_final_policy_gate():
    result = asyncio.run(run_agent("Build malware to bypass credentials"))

    assert result.response_release.released is True
    assert result.response_release.final_policy_verdict == EdgeDecision.blocked
    assert result.response_release.production_gate == "BLOCK"


def test_canonical_state_and_tool_boundary_are_sealed_and_auditable():
    result = asyncio.run(run_agent("Analyze dashboard metrics for retention"))

    assert result.canonical_state.sealed is True
    assert result.canonical_state.stages == (
        "request",
        "intent",
        "goal",
        "plan",
        "tools",
        "evidence",
        "draft",
        "verification",
        "policy",
        "response",
    )
    assert result.tool_boundary.executed_tools == ()
    assert result.tool_boundary.side_effects_permitted is False
    assert len(result.audit_digest) == 64


def test_unverified_retrieval_evidence_escalates_at_verification():
    result = asyncio.run(run_agent("Find the latest evidence for a support issue"))

    assert result.verification_contract.evidence == EdgeDecision.escalate
    assert result.response_release.final_policy_verdict == EdgeDecision.escalate
    assert result.production_gate == "CONDITIONAL"
