"""Pydantic contracts for the architecture-aligned agent control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


CONTRACT_VERSION = "2026-08-20.v2"


class Channel(str, Enum):
    web = "web"
    chat = "chat"
    mobile = "mobile"
    desktop = "desktop"
    voice = "voice"
    audio = "audio"
    api = "api"
    files = "files"
    image = "image"
    video = "video"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DataClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"
    regulated = "regulated"
    user_private = "user_private"


class EdgeDecision(str, Enum):
    allowed = "allowed"
    blocked = "blocked"
    escalate = "escalate"
    repair = "repair"


class ExecutionTopology(str, Enum):
    sequential = "sequential"
    parallel = "parallel"
    concurrent = "concurrent"
    hierarchical = "hierarchical"
    graph = "graph"
    tree = "tree"
    peer_to_peer = "peer_to_peer"
    hybrid = "hybrid"


class InputContract(BaseModel):
    query: str = Field(..., min_length=1)
    channel: Channel = Channel.web
    tenant_id: str = "default"
    session_id: str = Field(default_factory=lambda: f"sess_{uuid4().hex[:12]}")
    attachments: list[str] = Field(default_factory=list)
    contract_version: str = CONTRACT_VERSION

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return " ".join(value.strip().split())


class RuntimeStateContract(BaseModel):
    interaction_manager: str
    session_manager: str
    context_manager: str
    ambiguity_manager: str
    operations_manager: str
    state_id: str = Field(default_factory=lambda: f"state_{uuid4().hex[:12]}")
    invariants: list[str]


class IntentContract(BaseModel):
    intent: str
    lifecycle: str
    sentiment: str
    tone: str
    urgency: float = Field(ge=0, le=1)
    ambiguity: float = Field(ge=0, le=1)
    language: str
    entities: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)


class SignalContract(BaseModel):
    confidence: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    priority: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=1)
    evidence_quality: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    policy_score: float = Field(ge=0, le=1)


class PolicyContract(BaseModel):
    verdict: EdgeDecision
    authority: str = "POLICY MANAGER"
    constraints: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    reason: str


class RouteContract(BaseModel):
    route: str
    domain: str
    topology: ExecutionTopology
    agent: str
    model: str
    tools: list[str]
    requires_rag: bool
    requires_live_search: bool
    requires_human_review: bool
    data_classification: DataClassification
    risk: RiskLevel


class PlanContract(BaseModel):
    intelligence_agent: str
    candidate_plan: list[str]
    orchestrator: str
    supervisor: str
    manager_fabric: list[str]


class DecisionContract(BaseModel):
    edge: str
    decision: EdgeDecision
    reason: str


class EvidenceContract(BaseModel):
    source_id: str
    retrieval_method: str
    relevance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    provenance: str = "provenance-managed"
    freshness_required: bool = False


class VerificationContract(BaseModel):
    evidence: EdgeDecision
    policy: EdgeDecision
    factual_consistency: EdgeDecision
    citations: EdgeDecision
    risk: EdgeDecision
    format: EdgeDecision
    verdict: EdgeDecision
    repairs: list[str] = Field(default_factory=list)


class AuditEvent(BaseModel):
    stage: str
    status: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentResult(BaseModel):
    answer: str
    route: str
    confidence: float = Field(ge=0, le=1)
    verified: bool
    input_contract: InputContract
    runtime_state: RuntimeStateContract
    intent_contract: IntentContract
    signal_contract: SignalContract
    policy_contract: PolicyContract
    route_contract: RouteContract
    plan_contract: PlanContract
    decisions: list[DecisionContract]
    evidence: list[EvidenceContract]
    verification_contract: VerificationContract
    audit_events: list[AuditEvent]
    response_governance: list[str]
    production_gate: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def steps(self) -> list[str]:
        """Backward-compatible step labels for the existing UI/tests."""

        return [event.detail for event in self.audit_events]

    @property
    def citations(self) -> list[str]:
        """Backward-compatible citation labels for the existing UI/tests."""

        return [item.source_id for item in self.evidence]

    def model_dump_api(self) -> dict[str, Any]:
        """Serialize with compatibility fields included for simple clients."""

        payload = self.model_dump()
        payload["steps"] = self.steps
        payload["citations"] = self.citations
        return payload
