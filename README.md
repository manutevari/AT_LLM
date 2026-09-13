# AT_LLM — Governed AGI-Oriented Control Plane

A FastAPI + Streamlit foundation for governed agent orchestration and an
AGI-oriented target architecture. The current runtime maps the supplied
control-plane flowchart into deterministic stages: session/input
normalization, contracts, understanding, signals, routing, policy, evidence,
verification, audit, L0–L4 fallback planning, and candidate-only learning.
It does not claim to be human-level AGI.

The final response is generated as an internal draft and is released to the
user only after the verification engine and final policy gate approve the
outcome.

## What is included

- **Streamlit operator console** for launching agent runs and inspecting response, contracts, routing, evidence, and audit tabs.
- **Pydantic contract fabric** for input, intent, signal, route, edge decision, evidence, audit, and final response models.
- **Deterministic orchestration runtime** spanning Research, Build, Analyze, and Support workflows with domain, topology, agent, model, tool, RAG, freshness, risk, and human-review decisions.
- **FastAPI endpoint** for `/health` and `/agent` requests, compatible with the existing Vercel configuration.
- **Reference architecture documentation** in `docs/architecture.md` and the
  [AGI-oriented master blueprint](docs/agi_master_blueprint.md), including a
  current-vs-target comparison, safety boundaries, and delivery roadmap.
- **Pytest coverage** for route classification, auditable result behavior, ambiguity escalation, and high-risk governance.
## Setup

1. Copy `.env.example` to `.env` if you plan to add external providers later.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the API:
   ```bash
   uvicorn api.index:app --reload
   ```
4. Run the Streamlit console:
   ```bash
   streamlit run streamlit_app.py
   ```
5. Run tests:
   ```bash
   pytest
   ```

## API usage

```bash
curl -X POST http://127.0.0.1:8000/agent \
  -H 'Content-Type: application/json' \
  -d '{"query":"Design a policy-first RAG workflow","channel":"api","tenant_id":"demo"}'
```

## Production notes

This repository is a runnable control-plane foundation. Production deployments should add persistent PostgreSQL + pgvector storage, object storage, authenticated tenants, provider-specific model/tool adapters, rate limiting, bounded workflow execution, governed version registries, and environment-specific observability. See the [master blueprint](docs/agi_master_blueprint.md) for phased acceptance criteria.
