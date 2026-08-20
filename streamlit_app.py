import asyncio
import streamlit as st
from app.agent import run_agent

st.set_page_config(page_title="AI Agent Platform",layout="wide")
st.title("AI Agent Platform")
st.caption("Essential control-plane implementation")
query=st.text_area("Query")
if st.button("Run Agent",type="primary",disabled=not query.strip()):
    with st.spinner("Classifying → routing → validating → executing..."):
        result=asyncio.run(run_agent(query))
    st.subheader("Response")
    st.write(result.answer)
    a,b,c=st.columns(3)
    a.metric("Route",result.route)
    b.metric("Confidence",f"{result.confidence:.0%}")
    c.metric("Verified","Yes" if result.verified else "No")
