# =========================================================
# streamlit_app.py
# ADD INSIDE THE SIDEBAR
# =========================================================

from app.api_keys import generate_api_key, fingerprint_api_key


# ---------------------------------------------------------
# API Key Generator
# ---------------------------------------------------------

st.divider()

st.subheader("API Key Generator")

if st.button(
    "🔐 Generate API Key",
    use_container_width=True,
):

    generated_key = generate_api_key()
    key_fingerprint = fingerprint_api_key(
        generated_key
    )

    st.session_state.generated_api_key = generated_key
    st.session_state.generated_api_key_fingerprint = (
        key_fingerprint
    )

if (
    "generated_api_key"
    in st.session_state
):

    st.success(
        "API key generated. Store it securely; "
        "it will not be written to the audit trail."
    )

    st.code(
        st.session_state.generated_api_key,
        language="text",
    )

    st.caption(
        "Fingerprint: "
        + st.session_state.generated_api_key_fingerprint
    )

    if st.button(
        "Clear Secret",
        use_container_width=True,
    ):

        del st.session_state.generated_api_key

        if (
            "generated_api_key_fingerprint"
            in st.session_state
        ):
            del st.session_state.generated_api_key_fingerprint

        st.rerun()
