import streamlit as st

from src.utils.streamlit_utils import (
    jobs_filter_sidebar,
    display_raw_job_matches,
    init_app,
)
from src.utils.streamlit_cache import get_cached_global_store
from src.utils.embeddings_handler import get_embeddings
from src.schema import RawJobMatch


def global_job_list():
    init_app()
    embeddings = get_embeddings(st.session_state.pipeline_settings.api_settings)
    global_store = get_cached_global_store(embeddings)

    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Posted Date", "Company", "Role"]
    )

    jobs = [RawJobMatch(**job) for job in global_store.get().get("metadatas")]

    jobs = jobs_filter_sidebar(jobs)

    display_raw_job_matches(jobs, sort_by)


if __name__ == "__main__":
    global_job_list()
