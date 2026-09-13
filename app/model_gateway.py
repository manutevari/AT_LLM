"""Provider-neutral model gateway planning.

Agents use this module's contract output and never call a model provider
directly. Provider adapters belong behind this boundary.
"""

from __future__ import annotations

from .contracts import (
    EdgeDecision,
    FallbackTier,
    ModelAttemptContract,
    ModelFallbackContract,
    PolicyContract,
)


def select_model_fallback(policy: PolicyContract) -> ModelFallbackContract:
    """Select the safe L0–L4 plan without invoking unconfigured providers."""

    if policy.verdict == EdgeDecision.escalate:
        return ModelFallbackContract(
            selected_tier=FallbackTier.l4_human,
            human_escalation_required=True,
            attempts=[
                ModelAttemptContract(
                    tier=FallbackTier.l4_human,
                    provider="human-in-the-loop",
                    model="human-review",
                    status="required",
                    reason="Policy requires clarification or human review.",
                )
            ],
        )

    return ModelFallbackContract(
        selected_tier=FallbackTier.l3_deterministic,
        attempts=[
            ModelAttemptContract(
                tier=FallbackTier.l0_primary,
                provider="openrouter",
                model="openrouter/auto",
                status="not_configured",
                reason="No configured OpenRouter credential or adapter.",
            ),
            ModelAttemptContract(
                tier=FallbackTier.l1_secondary,
                provider="secondary-provider",
                model="configured-provider",
                status="not_configured",
                reason="No secondary provider adapter is configured.",
            ),
            ModelAttemptContract(
                tier=FallbackTier.l2_local,
                provider="local-inference",
                model="ollama-or-vllm",
                status="not_configured",
                reason="No local inference adapter is configured.",
            ),
            ModelAttemptContract(
                tier=FallbackTier.l3_deterministic,
                provider="at_llm",
                model="deterministic-contract-engine",
                status="selected",
                reason="Safe local deterministic control-plane execution.",
            ),
        ],
    )
