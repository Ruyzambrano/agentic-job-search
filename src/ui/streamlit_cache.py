"""Streamlit Cache: Performance optimization layer for the UI."""

import asyncio
import streamlit as st

from main import run_job_matcher
from src.utils.model_functions import get_all_gemini_models
from src.services.document_service import DocumentService
from src.services.storage_service import StorageService


@st.cache_data(show_spinner=False)
def get_job_analysis(cv_text, config, _models):
    """
    Wraps the main LangGraph entry point.
    Note: Ensure run_job_matcher returns a serializable dict.
    """
    return asyncio.run(run_job_matcher(cv_text, config, _models))


@st.cache_data(show_spinner="Processing Document...")
def get_cv_text(uploaded_file):
    """Uses DocumentService to extract text from bytes."""
    service = DocumentService()
    file_bytes = uploaded_file.getvalue()
    return service.convert_to_text(file_bytes, uploaded_file.name)


@st.cache_data(show_spinner="Generating Report...")
def generate_docx(state):
    """Uses DocumentService to create the download buffer."""
    service = DocumentService()
    return service.generate_research_report(state)


@st.cache_resource
def get_storage_service(_embeddings):
    """Use cache_resource for the Service Instance."""
    return StorageService(
        index_name=st.secrets["PINECONE_NAME"], embeddings=_embeddings
    )


@st.cache_data(show_spinner="Fetching matched jobs...")
def get_cached_jobs_for_profile(
    _storage: StorageService, profile_id: str, last_updated: float = 0.0
):
    """Fetches audited jobs from the user namespace."""
    return _storage.find_all_roles_for_profile(profile_id)


@st.cache_data()
def cached_jobs_all_user_profiles(
    _storage: StorageService, user_id: str, last_updated: float = 0.0
):
    """Fetches history for the entire user."""
    return _storage.find_all_roles_for_user(user_id)


@st.cache_data
def get_model_cache(api_key: str, free_tier: bool = False):
    return get_all_gemini_models(api_key, free_tier)

@st.cache_data
def get_raw_job_data(_store, job_url):
    """Compatibility wrapper for fetching raw job data from the service."""
    return _store.fetch_raw_job_data(job_url)