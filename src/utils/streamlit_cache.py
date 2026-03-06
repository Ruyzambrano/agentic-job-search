import asyncio

import streamlit as st

from main import run_job_matcher
from src.utils.document_handler import save_findings_to_docx, upload_file
from src.utils.vector_handler import (
    get_user_analysis_store,
    get_global_jobs_store,
    find_all_roles_for_profile,
    find_all_roles_for_user,
)


@st.cache_data(show_spinner=False)
def get_job_analysis(cv_text, config, _models):
    return asyncio.run(run_job_matcher(cv_text, config, _models))


@st.cache_data(show_spinner=False)
def generate_docx(state):
    return save_findings_to_docx(state)


@st.cache_data(show_spinner=False)
def get_cv_text(uploaded_file):
    return upload_file(uploaded_file)


@st.cache_resource
def get_cached_user_store(_embeddings):
    return get_user_analysis_store(_embeddings)


@st.cache_resource
def get_cached_global_store(_embeddings):
    return get_global_jobs_store(_embeddings)


@st.cache_data(show_spinner="Fetching matched jobs...")
def get_cached_jobs_for_profile(_store, profile_id):
    return find_all_roles_for_profile(_store, profile_id)


@st.cache_data()
def cached_jobs_all_user_profiles(_store, user_id):
    return find_all_roles_for_user(_store, user_id)
