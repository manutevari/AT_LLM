import asyncio

from app.agent import classify_route, run_agent


def test_classify_route_prefers_build_for_design_requests():
    route, confidence = classify_route("Design and build an API feature")

    assert route.name == "Build"
    assert confidence > 0.7


def test_run_agent_returns_auditable_result():
    result = asyncio.run(run_agent("Analyze dashboard metrics for retention"))

    assert result.route == "Analyze"
    assert result.verified is True
    assert result.steps
    assert "Execution status" in result.answer
