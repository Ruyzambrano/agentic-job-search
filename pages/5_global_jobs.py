"""Global Job Library: Browse every job scraped by the system."""
from json import loads

import streamlit as st

from src.ui.components import jobs_filter_sidebar, display_raw_job_matches, add_sidebar_support
from src.ui.controllers import init_app
from src.ui.streamlit_cache import get_cached_global_jobs
from src.schema import RawJobMatch

def global_job_list():
    storage = st.session_state.storage_service

    st.title("🌐 Global Job Library")
    st.write("Browse the master list of all jobs currently indexed in the system.")

    with st.spinner("Loading global index..."):
        jobs = get_cached_global_jobs(storage, 100, st.session_state.last_updated)
        jobs = [RawJobMatch(**loads(j)) for j in jobs]

    sort_options = {"Posted Date": "posted_at", "Company": "company", "Role": "title"}
    sort_label = st.sidebar.selectbox("Sort by", options=list(sort_options.keys()))
    sort_key = sort_options[sort_label]

    if not jobs:
        st.info(
            "The global library is empty. Run a search on the Home page to populate it!"
        )
    else:
        filtered_jobs = jobs_filter_sidebar(jobs)

        if not filtered_jobs:
            st.warning("No jobs match your current filters.")
        else:
            display_raw_job_matches(filtered_jobs, sort_key)


if __name__ == "__main__":
    init_app()
    global_job_list()
    add_sidebar_support()
