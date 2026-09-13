"""The sole boundary for planning or authorizing tool capabilities.

This starter does not execute tools. A future executor must be added behind
this module rather than granting filesystem or external API access to agents.
"""

from __future__ import annotations

from collections.abc import Iterable

from .contracts import (
    EdgeDecision,
    PolicyContract,
    ToolExecutionBoundaryContract,
)


def authorize_tool_plan(
    requested_tools: Iterable[str],
    policy: PolicyContract,
) -> ToolExecutionBoundaryContract:
    """Return an explicit, no-side-effect authorization plan."""

    requested = tuple(requested_tools)
    authorized = requested if policy.verdict == EdgeDecision.allowed else ()

    return ToolExecutionBoundaryContract(
        requested_tools=requested,
        authorized_tools=authorized,
        executed_tools=(),
        sandbox_required=True,
        side_effects_permitted=False,
    )
