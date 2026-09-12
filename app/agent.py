"""
Minimal, declarative, composable flows:
- classify → evaluate → gather → execute
- HITL triggers when risk/confidence thresholds are crossed
- Audit metadata is optional sidecar
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Dict, Any, List

# --- Core primitives ---

@dataclass
class FlowContext:
    query: str
    confidence: float
    risk: float
    freshness: float
    hitl: bool
    gate: str


ROUTES: Dict[str, Dict[str, Any]] = {
    "research": {
        "keywords": {"research", "compare", "latest", "source", "summarize", "find"},
        "agent": ["research", "verify"],
        "tools": ["rag", "search"],
        "model": "reasoning-verifier",
    },
    "build": {
        "keywords": {"build", "code", "implement", "design", "feature", "api"},
        "agent": ["supervisor", "builder"],
        "tools": ["factory", "test", "deploy"],
        "model": "structured-output",
    },
    "analyze": {
        "keywords": {"analyze", "metric", "data", "trend", "report", "dashboard"},
        "agent": ["analysis", "critic"],
        "tools": ["analytics", "evaluation"],
        "model": "analysis-long-context",
    },
    "support": {
        "keywords": {"error", "issue", "bug", "fix", "help", "troubleshoot"},
        "agent": ["support", "recovery"],
        "tools": ["ticket", "runbook"],
        "model": "support-safe-response",
    },
}

HIGH_RISK_TERMS = {"legal", "medical", "regulated", "delete", "payment", "credential", "secret", "finance"}
FRESHNESS_TERMS = {"latest", "today", "current", "news", "price", "schedule", "recent"}


# --- Helpers ---

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def classify(query: str) -> str:
    tokens = _tokens(query)
    scores = {name: len(tokens & route["keywords"]) for name, route in ROUTES.items()}
    return max(scores, key=scores.get)


def evaluate(query: str) -> FlowContext:
    tokens = _tokens(query)
    confidence = 0.9 if len(tokens) > 3 else 0.5
    risk = 0.8 if tokens & HIGH_RISK_TERMS else 0.2
    freshness = 0.85 if tokens & FRESHNESS_TERMS else 0.3
    hitl_required = risk >= 0.7 or confidence <= 0.6
    gate = "BLOCK" if "malware" in tokens else "CONDITIONAL" if hitl_required else "PASS"
    return FlowContext(query, confidence, risk, freshness, hitl_required, gate)


async def gather(route: str, ctx: FlowContext) -> Dict[str, Any]:
    # Minimal provenance
    evidence = {"source": "local", "confidence": 0.9}
    if ctx.freshness > 0.8:
        evidence["fresh"] = True
    return evidence


async def execute(route: str, ctx: FlowContext, evidence: Dict[str, Any]) -> str:
    agent = ROUTES[route]["agent"]
    tools = ROUTES[route]["tools"]
    return (
        f"Route={route} | Agent={agent} | Tools={tools}\n"
        f"Confidence={ctx.confidence:.2f}, Risk={ctx.risk:.2f}, Freshness={ctx.freshness:.2f}\n"
        f"Gate={ctx.gate} | HITL={'required' if ctx.hitl else 'auto'}"
    )


# --- Audit Sidecar ---

def audit(query: str, ctx: FlowContext, route: str, evidence: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {"stage": "input", "status": "ok", "detail": f"Query='{query}'"},
        {"stage": "classify", "status": "ok", "detail": f"Route={route}"},
        {"stage": "evaluate", "status": "ok", "detail": f"Confidence={ctx.confidence:.2f}, Risk={ctx.risk:.2f}, Freshness={ctx.freshness:.2f}"},
        {"stage": "hitl", "status": "conditional" if ctx.hitl else "pass", "detail": f"Gate={ctx.gate}"},
        {"stage": "gather", "status": "ok", "detail": f"Evidence={evidence}"},
        {"stage": "execute", "status": "ok", "detail": "Execution completed"},
    ]


# --- Orchestration entrypoint ---

async def orchestrate(query: str) -> Dict[str, Any]:
    ctx = evaluate(query)
    route = classify(query)
    evidence = await gather(route, ctx)
    result = await execute(route, ctx, evidence)
    return {
        "answer": result,
        "meta": {
            "route": route,
            "ctx": ctx,
            "evidence": evidence,
            "audit": audit(query, ctx, route, evidence),
        },
    }


# --- Demo run ---

if __name__ == "__main__":
    async def demo():
        q = "latest medical research on diabetes"
        output = await orchestrate(q)
        print(output["answer"])
        print("\nAudit Trail:")
        for event in output["meta"]["audit"]:
            print(event)

    asyncio.run(demo())
