from __future__ import annotations

import streamlit as st

from app.agent import ROUTES, run_agent
from app.api_keys import generate_api_key, fingerprint_api_key
from app.contracts import Channel


st.set_page_config(
    page_title="AT LLM — AI Agent Platform",
    page_icon="🤖",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

if "generated_api_key" not in st.session_state:
    st.session_state.generated_api_key = None

if "generated_api_key_fingerprint" not in st.session_state:
    st.session_state.generated_api_key_fingerprint = None


# =========================================================
# HEADER
# =========================================================

st.title("🤖 AT LLM — AI Agent Platform")
st.caption(
    "Architecture-aligned deterministic agent orchestration "
    "with policy, verification, evidence and audit controls."
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.header("⚙️ Agent Configuration")

    channel = st.selectbox(
        "Channel",
        options=[c.value for c in Channel],
        index=0,
    )

    st.divider()

    st.subheader("🔐 API Key Generator")

    if st.button(
        "Generate API Key",
        use_container_width=True,
        type="primary",
    ):
        key = generate_api_key()

        st.session_state.generated_api_key = key
        st.session_state.generated_api_key_fingerprint = (
            fingerprint_api_key(key)
        )

    if st.session_state.generated_api_key:
        st.success("API key generated.")

        st.code(
            st.session_state.generated_api_key,
            language="text",
        )

        st.caption(
            "Store this key securely. The plaintext key should "
            "not be logged or persisted by the application."
        )

        st.write(
            "Fingerprint:",
            st.session_state.generated_api_key_fingerprint,
        )

        if st.button(
            "Clear Secret",
            use_container_width=True,
        ):
            st.session_state.generated_api_key = None
            st.session_state.generated_api_key_fingerprint = None
            st.rerun()

    st.divider()

    st.subheader("Available Routes")

    for route in ROUTES:
        st.markdown(
            f"**{route.name}**  \n"
            f"{route.domain}  \n"
            f"{route.description}"
        )


# =========================================================
# MAIN INPUT
# =========================================================

st.subheader("Agent Request")

query = st.text_area(
    "Enter your request",
    placeholder=(
        "Example: Analyze dashboard metrics for retention"
    ),
    height=140,
)


# =========================================================
# EXECUTION
# =========================================================

if st.button(
    "🚀 Run Agent",
    type="primary",
    use_container_width=True,
):
    if not query.strip():
        st.warning("Please enter a request.")
        st.stop()

    try:
        result = run_agent(
            query=query,
            channel=channel,
        )

        st.divider()

        # -------------------------------------------------
        # RESULT
        # -------------------------------------------------

        st.subheader("Answer")

        st.write(result.answer)

        # -------------------------------------------------
        # ROUTE
        # -------------------------------------------------

        st.subheader("Route")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Route",
                result.route.name,
            )

        with col2:
            st.metric(
                "Domain",
                result.route.domain,
            )

        with col3:
            st.metric(
                "Verified",
                "YES" if result.verified else "NO",
            )

        # -------------------------------------------------
        # DECISION
        # -------------------------------------------------

        st.subheader("Decision")

        decision = result.decision

        st.json(
            decision.model_dump(mode="json")
            if hasattr(decision, "model_dump")
            else decision
        )

        # -------------------------------------------------
        # EVIDENCE
        # -------------------------------------------------

        if result.evidence:
            st.subheader("Evidence")

            for evidence in result.evidence:
                if hasattr(evidence, "model_dump"):
                    st.json(
                        evidence.model_dump(mode="json")
                    )
                else:
                    st.write(evidence)

        # -------------------------------------------------
        # AUDIT
        # -------------------------------------------------

        st.subheader("Audit Trail")

        if result.steps:
            for step in result.steps:
                st.markdown(f"- {step}")
        else:
            st.info("No audit events available.")

    except Exception as exc:
        st.error("Agent execution failed.")

        with st.expander("Technical Error"):
            st.exception(exc)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AT LLM • Policy-controlled routing • Verification • "
    "Evidence • Audit • Security Control Plane"
)
