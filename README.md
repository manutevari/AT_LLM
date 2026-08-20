# AI Agent Platform — Essential Coding Base

Includes FastAPI + Streamlit, Pydantic contracts, deterministic routing,
conditional edges, PostgreSQL + pgvector schema/repository, OpenRouter model
adapter, tool registry, audit events, Tableau-ready SQL views, and optional
Ruflo/LangGraph execution adapter boundaries.

Setup:
1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL`.
3. Optionally set `OPENROUTER_API_KEY`.
4. Run `psql "$DATABASE_URL" -f db/schema.sql`.
5. `pip install -r requirements.txt`
6. `uvicorn app.api:app --reload`
7. `streamlit run streamlit_app.py`
8. `pytest`

This is an essential implementation base, not production certification.
