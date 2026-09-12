"""Core package for the AI Agent Platform demo."""

from .agent import ROUTES, RouteDefinition, classify_route, run_agent
from .contracts import (
    AgentResult,
    Channel,
    InputContract,
    RouteContract,
    SignalContract,
)

__all__ = [
    "AgentResult",
    "Channel",
    "InputContract",
    "ROUTES",
    "RouteContract",
    "RouteDefinition",
    "SignalContract",
    "classify_route",
    "run_agent",
]
