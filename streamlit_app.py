import asyncio

import streamlit as st

from app.agent import ROUTES, run_agent
from app.contracts import Channel

st.set_page_config(page_title="AI Agent Platform", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
      .hero {padding: 2rem; border-radius: 1.5rem; background: linear-gradient(135deg, #020617 0%, #2563eb 50%, #7c3aed 100%); color: white;}
      .hero h1 {font-size: 3rem; margin-bottom: .25rem;}
      .pill {display: inline-block; padding: .35rem .7rem; border-radius: 999px; margin: .15rem; background: #e0e7ff; color: #312e81; font-weight: 650;}
      .hero {padding: 2rem; border-radius: 1.5rem; background: linear-gradient(135deg, #111827 0%, #2563eb 55%, #7c3aed 100%); color: white;}
      .hero h1 {font-size: 3rem; margin-bottom: .25rem;}
      .card {padding: 1.2rem; border: 1px solid rgba(148,163,184,.3); border-radius: 1rem; background: rgba(15,23,42,.03); min-height: 150px;}
      .step {padding: .65rem .8rem; margin: .35rem 0; border-radius: .7rem; background: #eef2ff; color: #1e1b4b;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="hero">
      <h1>AI Agent Platform</h1>
      <p>Contract-first orchestration for routing, validation, tools, models, RAG, governance, observability, and audit.</p>
      <p>Route, validate, execute, and audit agent work from a polished control-plane console.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.divider()
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("Launch an architecture-aligned run")
    query = st.text_area(
        "Describe the mission",
        placeholder="Example: Design a policy-first RAG workflow for regulated support tickets with Tableau audit dashboards.",
        height=180,
    )
    c1, c2 = st.columns(2)
    channel = c1.selectbox("Channel", [item.value for item in Channel], index=0)
    tenant_id = c2.text_input("Tenant", value="default")
    run_clicked = st.button("Run Control Plane", type="primary", use_container_width=True, disabled=not query.strip())

with right:
    st.subheader("Route catalog")
    for route in ROUTES:
        st.markdown(f"<span class='pill'>{route.name}</span> **{route.domain}** — {route.description}", unsafe_allow_html=True)

if run_clicked:
    with st.spinner("Session → contracts → signals → routing → governance → audit..."):
        result = asyncio.run(run_agent(query, channel=Channel(channel), tenant_id=tenant_id))

    st.success("Control-plane run completed")
    a, b, c, d, e = st.columns(5)
    a.metric("Route", result.route)
    b.metric("Confidence", f"{result.confidence:.0%}")
    c.metric("Risk", result.route_contract.risk.value.title())
    d.metric("Gate", result.production_gate)
    e.metric("Audit Events", len(result.audit_events))

    tabs = st.tabs(["Response", "Contracts", "Routing", "Evidence", "Audit"])
    with tabs[0]:
        st.write(result.answer)
        st.caption("Governance: " + ", ".join(result.response_governance))
    with tabs[1]:
        st.json(
            {
                "input": result.input_contract.model_dump(mode="json"),
                "intent": result.intent_contract.model_dump(mode="json"),
                "signals": result.signal_contract.model_dump(mode="json"),
            }
        )
    with tabs[2]:
        st.json(result.route_contract.model_dump(mode="json"))
        st.write("Deterministic edge decisions")
        st.dataframe([decision.model_dump(mode="json") for decision in result.decisions], use_container_width=True)
    with tabs[3]:
        st.dataframe([item.model_dump(mode="json") for item in result.evidence], use_container_width=True)
    with tabs[4]:
        for event in result.audit_events:
            st.markdown(f"<div class='step'><strong>{event.stage}</strong> · {event.status}<br/>{event.detail}</div>", unsafe_allow_html=True)
else:
    st.info("Enter a mission to preview the full contract, routing, evidence, governance, and audit pipeline.")
left, right = st.columns([1.15, 0.85], gap="large")

with left:
    st.subheader("Launch an agent run")
    query = st.text_area(
        "Describe the mission",
        placeholder="Example: Design and implement a customer support triage workflow with audit logging.",
        height=180,
    )
    run_clicked = st.button("Run Agent", type="primary", use_container_width=True, disabled=not query.strip())

with right:
    st.subheader("Control-plane routes")
    for route in ROUTES:
        st.markdown(f"**{route.name}** — {route.description}")

if run_clicked:
    with st.spinner("Classifying → routing → validating → executing..."):
        result = asyncio.run(run_agent(query))

    st.success("Agent run completed")
    a, b, c, d = st.columns(4)
    a.metric("Route", result.route)
    b.metric("Confidence", f"{result.confidence:.0%}")
    c.metric("Verified", "Yes" if result.verified else "No")
    d.metric("Audit Events", len(result.steps))

    response_col, audit_col = st.columns([1.3, 0.7], gap="large")
    with response_col:
        st.subheader("Response")
        st.write(result.answer)
    with audit_col:
        st.subheader("Audit trail")
        for step in result.steps:
            st.markdown(f"<div class='step'>{step}</div>", unsafe_allow_html=True)
        st.caption("Citations: " + ", ".join(result.citations))
else:
    st.info("Enter a mission to preview deterministic routing, confidence, validation, and audit output.")
