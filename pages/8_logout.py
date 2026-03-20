"""Logs the user out"""

import streamlit as st

if __name__ == "__main__":
    st.session_state.clear()
    st.query_params.clear()
    st.logout()
    st.rerun()
