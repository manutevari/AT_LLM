# AI Agent Platform — Full-Fledged Control-Plane Demo

A polished FastAPI + Streamlit starter for deterministic AI-agent orchestration. The app now includes a local agent runtime, route classification, validation checks, auditable execution steps, a Streamlit console, and a deployable FastAPI entrypoint.

## What is included

- **Streamlit operator console** for launching agent runs, viewing route confidence, validation status, and audit events.
- **Deterministic agent runtime** with intent classification across Research, Build, Analyze, and Support workflows.
- **Stable response contract** shared by the UI and API.
- **FastAPI endpoint** for `/health` and `/agent` requests, compatible with the existing Vercel configuration.
- **Pytest coverage** for route classification and auditable result generation.

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
  -d '{"query":"Design and build an API feature"}'
```

## Notes

This repository is a runnable control-plane foundation. Production deployments should add persistent audit storage, authenticated users, provider-specific tool adapters, rate limiting, and environment-specific observability.
