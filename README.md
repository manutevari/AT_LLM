# AI Agent Platform — Architecture-Aligned Control Plane

A full-fledged FastAPI + Streamlit starter for deterministic AI-agent orchestration. The app now maps the supplied enterprise flowchart into runnable local stages: session/input normalization, Pydantic contracts, human understanding, query intelligence, signal scoring, routing, deterministic edge decisions, topology planning, evidence provenance, response governance, and strict audit gating.

## What is included

- **Streamlit operator console** for launching agent runs and inspecting response, contracts, routing, evidence, and audit tabs.
- **Pydantic contract fabric** for input, intent, signal, route, edge decision, evidence, audit, and final response models.
- **Deterministic orchestration runtime** spanning Research, Build, Analyze, and Support workflows with domain, topology, agent, model, tool, RAG, freshness, risk, and human-review decisions.
- **FastAPI endpoint** for `/health` and `/agent` requests, compatible with the existing Vercel configuration.
- **Reference architecture documentation** in `docs/architecture.md` with the implemented Mermaid flow and extension points.
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

This repository is a runnable control-plane foundation. Production deployments should add persistent PostgreSQL + pgvector storage, object storage, authenticated tenants, provider-specific model/tool adapters, rate limiting, LangGraph/Ruflo execution adapters, Tableau governed views, and environment-specific observability.
