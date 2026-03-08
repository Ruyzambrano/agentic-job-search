from time import time

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
        
    embeddings = get_embeddings()
    global_store = get_cached_global_store(embeddings)

    index = global_store.get_pinecone_index('agent-pipeline')
    ns = global_store._namespace
    
    zero_vector = [0.0] * 3072 

    results = index.query(
        vector=zero_vector,
        top_k=100,
        namespace=ns,
        include_metadata=True
    )

    jobs = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        jobs.append(RawJobMatch(**meta))

    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Posted Date", "Company", "Role"]
    )
    
    jobs = jobs_filter_sidebar(jobs)
    display_raw_job_matches(jobs, sort_by)


if __name__ == "__main__":
    global_job_list()
