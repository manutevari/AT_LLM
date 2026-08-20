import asyncio

import streamlit as st

from app.agent import ROUTES, run_agent
from app.contracts import Channel

st.set_page_config(page_title="AI Agent Platform", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
      .hero {padding: 2rem; border-radius: 1.5rem; background: linear-gradient(135deg, #111827 0%, #2563eb 55%, #7c3aed 100%); color: white;}
      .hero h1 {font-size: 3rem; margin-bottom: .25rem;}
      .pill {display: inline-block; padding: .35rem .7rem; border-radius: 999px; margin: .15rem; background: #e0e7ff; color: #312e81; font-weight: 650;}
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

if "messages" not in st.session_state:
    st.session_state.messages = []
if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

with st.sidebar:
    st.subheader("Session Settings")
    channel = st.selectbox("Channel", [item.value for item in Channel], index=0)
    tenant_id = st.text_input("Tenant", value="default")
    st.divider()
    st.subheader("Route catalog")
    for route in ROUTES:
        st.markdown(f"<span class='pill'>{route.name}</span> **{route.domain}** — {route.description}", unsafe_allow_html=True)

st.divider()
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("Agent Chat")
    
    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Describe the mission..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Session → contracts → signals → routing → governance → audit..."):
                result = asyncio.run(run_agent(prompt, channel=Channel(channel), tenant_id=tenant_id, history=st.session_state.messages[:-1]))
                st.session_state.latest_result = result
                st.write(result.answer)
        st.session_state.messages.append({"role": "assistant", "content": result.answer})
        st.rerun()

with right:
    st.subheader("Control Plane Observability")
    if result := st.session_state.latest_result:
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
