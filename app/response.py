"""Draft generation and governed response release.

This module intentionally separates candidate-response construction from the
verification and final-policy decision made by the orchestration layer.
"""

from __future__ import annotations

from .contracts import (
    EdgeDecision,
    PlanContract,
    PolicyContract,
    ResponseDraftContract,
    ResponseReleaseContract,
    RouteContract,
    VerificationContract,
)


def build_response_draft(
    *,
    route: RouteContract,
    plan: PlanContract,
    policy: PolicyContract,
    verification: VerificationContract | None = None,
    generated_api_key: str | None = None,
    api_key_fingerprint: str | None = None,
) -> ResponseDraftContract:
    """Create a candidate response; it is not a user-facing release."""

    if policy.verdict == EdgeDecision.blocked:
        content = (
            "The request was blocked by the Policy Manager. The system will "
            "not perform credential abuse, authentication bypass, malware "
            "development, or other prohibited activity."
        )
    elif policy.verdict == EdgeDecision.escalate:
        content = (
            f"Route {route.route} requires human review or clarification. "
            f"Constraints: {', '.join(policy.constraints)}. "
            "No external side effect was executed."
        )
    elif route.route == "API Key":
        content = (
            "API key generated successfully.\n\n"
            f"API Key:\n{generated_api_key}\n\n"
            "Security notice: this secret is displayed only in the current "
            "response and is not written to the audit trail.\n\n"
            f"Key fingerprint: {api_key_fingerprint}\n"
            "The key has NOT been registered, activated, stored in an "
            "external secret manager, or granted permissions."
        )
    else:
        verification_text = (
            verification.verdict.value if verification else "pending"
        )
        content = (
            f"Architecture-aligned route: {route.route} in the "
            f"{route.domain} domain. Topology: {route.topology.value} | "
            f"Assigned agent: {route.agent} | Model policy: {route.model}. "
            f"Constraints: {', '.join(policy.constraints)}. Manager fabric: "
            f"{', '.join(plan.manager_fabric)}. Tools planned: "
            f"{', '.join(route.tools)}. Data classification: "
            f"{route.data_classification.value} | Risk: {route.risk.value}. "
            f"Verification verdict: {verification_text}. "
            "No unapproved external side effect was executed."
        )

    return ResponseDraftContract(
        content=content,
        generator="response_generation_module",
        contains_secret=generated_api_key is not None,
    )


def release_final_response(
    *,
    draft: ResponseDraftContract,
    policy: PolicyContract,
    verification: VerificationContract,
) -> tuple[str, ResponseReleaseContract]:
    """Release only a policy- and verification-governed final response."""

    if policy.verdict == EdgeDecision.blocked:
        return (
            f"{draft.content} Execution status: blocked by policy.",
            ResponseReleaseContract(
                verification_verdict=verification.verdict,
                final_policy_verdict=EdgeDecision.blocked,
                released=True,
                production_gate="BLOCK",
            ),
        )

    if (
        policy.verdict == EdgeDecision.escalate
        or verification.verdict != EdgeDecision.allowed
    ):
        return (
            f"{draft.content} Execution status: requires human review or "
            "clarification. Production gate: CONDITIONAL.",
            ResponseReleaseContract(
                verification_verdict=verification.verdict,
                final_policy_verdict=EdgeDecision.escalate,
                released=True,
                production_gate="CONDITIONAL",
            ),
        )

    return (
        f"{draft.content} Execution status: passed validation. "
        "Production gate: PASS.",
        ResponseReleaseContract(
            verification_verdict=verification.verdict,
            final_policy_verdict=EdgeDecision.allowed,
            released=True,
            production_gate="PASS",
        ),
    )
