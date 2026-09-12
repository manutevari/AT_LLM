import asyncio

import streamlit as st

from app.agent import ROUTES, run_agent
from app.contracts import Channel


st.set_page_config(
    page_title="AI Agent Platform",
    page_icon="🤖",
    layout="wide",
)


st.markdown(
    """
    <style>
      .hero {
          padding: 2rem;
          border-radius: 1.5rem;
          background: linear-gradient(
              135deg,
              #111827 0%,
              #2563eb 55%,
              #7c3aed 100%
          );
          color: white;
      }

      .hero h1 {
          font-size: 3rem;
          margin-bottom: .25rem;
      }

      .pill {
          display: inline-block;
          padding: .35rem .7rem;
          border-radius: 999px;
          margin: .15rem;
          background: #e0e7ff;
          color: #312e81;
          font-weight: 650;
      }

      .step {
          padding: .65rem .8rem;
          margin: .35rem 0;
          border-radius: .7rem;
          background: #eef2ff;
          color: #1e1b4b;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <section class="hero">
      <h1>AI Agent Platform</h1>
      <p>
        Contract-first orchestration for routing, validation, tools,
        models, RAG, governance, observability, and audit.
      </p>
      <p>
        Route, validate, execute, and audit agent work
        from a polished control-plane console.
      </p>
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

    channel = st.selectbox(
        "Channel",
        [item.value for item in Channel],
        index=0,
    )

    tenant_id = st.text_input(
        "Tenant",
        value="default",
    )

    st.divider()

    st.subheader("Route Catalog")

    for route in ROUTES:
        st.markdown(
            f"""
            <span class="pill">{route.name}</span>
            <strong>{route.domain}</strong>
            — {route.description}
            """,
            unsafe_allow_html=True,
        )


st.divider()

left, right = st.columns(
    [1.05, 0.95],
    gap="large",
)


with left:
    st.subheader("Agent Chat")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Describe the mission..."):

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner(
                "Session → contracts → signals → routing → governance → audit..."
            ):
                try:
                    result = asyncio.run(
                        run_agent(
                            prompt,
                            channel=Channel(channel),
                            tenant_id=tenant_id,
                            history=st.session_state.messages[:-1],
                        )
                    )

                    st.session_state.latest_result = result

                    st.write(result.answer)

                except Exception as exc:
                    st.session_state.latest_result = None

                    st.error(
                        f"Agent execution failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

        if st.session_state.latest_result is not None:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": st.session_state.latest_result.answer,
                }
            )

        st.rerun()


with right:
    st.subheader("Control Plane Observability")

    result = st.session_state.latest_result

    if result is not None:

        a, b, c, d, e = st.columns(5)

        a.metric(
            "Route",
            result.route,
        )

        b.metric(
            "Confidence",
            f"{result.confidence:.0%}",
        )

        c.metric(
            "Risk",
            result.route_contract.risk.value.title(),
        )

        d.metric(
            "Gate",
            result.production_gate,
        )

        e.metric(
            "Audit Events",
            len(result.audit_events),
        )

        tabs = st.tabs(
            [
                "Response",
                "Contracts",
                "Routing",
                "Evidence",
                "Audit",
            ]
        )

        with tabs[0]:
            st.write(result.answer)

            if result.response_governance:
                st.caption(
                    "Governance: "
                    + ", ".join(result.response_governance)
                )

        with tabs[1]:
            st.json(
                {
                    "input": result.input_contract.model_dump(
                        mode="json"
                    ),
                    "intent": result.intent_contract.model_dump(
                        mode="json"
                    ),
                    "signals": result.signal_contract.model_dump(
                        mode="json"
                    ),
                    "policy": result.policy_contract.model_dump(
                        mode="json"
                    ),
                    "plan": result.plan_contract.model_dump(
                        mode="json"
                    ),
                    "verification": result.verification_contract.model_dump(
                        mode="json"
                    ),
                }
            )

        with tabs[2]:
            st.json(
                result.route_contract.model_dump(
                    mode="json"
                )
            )

            st.write("Deterministic Edge Decisions")

            decisions = [
                decision.model_dump(mode="json")
                for decision in result.decisions
            ]

            if decisions:
                st.dataframe(
                    decisions,
                    use_container_width=True,
                )
            else:
                st.info("No routing decisions recorded.")

        with tabs[3]:
            evidence = [
                item.model_dump(mode="json")
                for item in result.evidence
            ]

            if evidence:
                st.dataframe(
                    evidence,
                    use_container_width=True,
                )
            else:
                st.info("No evidence recorded.")

        with tabs[4]:
            if result.audit_events:
                for event in result.audit_events:
                    st.markdown(
                        f"""
                        <div class="step">
                            <strong>{event.stage}</strong>
                            · {event.status}
                            <br/>
                            {event.detail}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No audit events recorded.")

    else:
        st.info(
            "Enter a mission to preview the full contract, "
            "routing, evidence, governance, and audit pipeline."
        )
