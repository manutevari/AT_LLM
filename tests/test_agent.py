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
