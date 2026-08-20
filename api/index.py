"""FastAPI entrypoint for Vercel and local API use."""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent import run_agent
from app.contracts import AgentResult, Channel

api = FastAPI(title="AI Agent Platform", version="0.4.0")
from app.agent import AgentResult, run_agent

api = FastAPI(title="AI Agent Platform", version="0.3.0")
app = api


class AgentRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User request to route through the agent control plane")
    channel: Channel = Field(default=Channel.api, description="Interaction channel that originated the request")
    tenant_id: str = Field(default="default", min_length=1, description="Tenant or organization boundary")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "contracts": "ready"}
    return {"status": "ok"}


@api.post("/agent", response_model=AgentResult)
async def agent(request: AgentRequest) -> AgentResult:
    return await run_agent(request.query, channel=request.channel, tenant_id=request.tenant_id)
    return await run_agent(request.query)
