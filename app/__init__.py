# =========================================================
# app/__init__.py
# =========================================================

"""Core package for the AI Agent Platform."""

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
    "RouteContract",
    "SignalContract",
]
