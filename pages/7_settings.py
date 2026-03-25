import streamlit as st

from src.ui.components import render_settings_page
from src.ui.controllers import init_app, show_success_toast

if __name__ == "__main__":
    with st.sidebar:
        st.write(" ")
    init_app()
    show_success_toast()
    render_settings_page() 
    

