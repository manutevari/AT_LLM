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
        "synthesis_engine",
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
