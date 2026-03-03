import streamlit as st

from src.utils.streamlit_utils import jobs_filter_sidebar, display_raw_job_matches
from src.utils.vector_handler import get_global_jobs_store
from src.schema import RawJobMatch


def global_job_list():
    global_store = get_global_jobs_store()

    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Posted Date", "Company", "Role"]
    )

    jobs = [RawJobMatch(**job) for job in global_store.get().get("metadatas")]

    jobs = jobs_filter_sidebar(jobs)

    display_raw_job_matches(jobs, sort_by)


if __name__ == "__main__":
    global_job_list()
