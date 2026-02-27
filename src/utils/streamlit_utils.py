from datetime import datetime
from json import loads

import streamlit as st

from src.schema import CandidateProfile

def login_screen():
    st.button("Log in with Google", on_click=st.login)

def iso_formatter(option: datetime):
    """Makes an ISO string human readable"""
    try:
        dt = datetime.fromisoformat(option)
        return dt.strftime("%d %b %H:%M")
    except:
        return option
    
def display_profile(profile: dict):
    st.write(f"# {profile.get("full_name")}")
    st.write(profile.get("summary"))
    st.write("## Previous roles")
    st.write(f"- {"\n- ".join(loads(profile.get("job_titles")))}")
    st.write("## Key Skills")
    st.write(f"- {"\n- ".join(loads(profile.get('key_skills')))}")
    st.write("## Industries")
    st.write(f"- {"\n- ".join(loads(profile.get("industries")))}")
