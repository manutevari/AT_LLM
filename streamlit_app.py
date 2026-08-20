import asyncio

import streamlit as st

from app.agent import ROUTES, run_agent

st.set_page_config(page_title="AI Agent Platform", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
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
      <p>Route, validate, execute, and audit agent work from a polished control-plane console.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.divider()
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
