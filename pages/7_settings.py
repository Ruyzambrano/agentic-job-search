import streamlit as st

from src.utils.streamlit_utils import render_settings_page, init_app

if __name__ == "__main__":
    with st.sidebar:
        st.write(" ")
    init_app()
    render_settings_page()
