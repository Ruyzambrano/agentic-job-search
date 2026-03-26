"""Streamlit Cache: Performance optimization layer for the UI."""
from json import dumps
import asyncio

import streamlit as st
import pandas as pd

from main import run_job_matcher
from src.utils.model_functions import get_all_gemini_models
from src.services.document_service import DocumentService
from src.services.storage_service import StorageService
from src.ui.altair_handler import create_salary_chart


@st.cache_resource(show_spinner=False)
def get_job_analysis(cv_text, _config, _models):
    """
    Wraps the main LangGraph entry point.
    """
    final_state = asyncio.run(run_job_matcher(cv_text, _config, _models))

    serializable_output = {
        "messages": [str(m.content) for m in final_state.get("messages", [])],
        "active_profile_id": final_state.get("active_profile_id"),
        "active_profile": final_state.get("cv_data").model_dump()
    }

    return dumps(serializable_output)


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


@st.cache_resource(show_spinner=False)
def get_storage_service(_embeddings):
    """Use cache_resource for the Service Instance."""
    return StorageService(
        index_name=st.secrets["PINECONE_NAME"], embeddings=_embeddings
    )


@st.cache_data(show_spinner=False)
def get_model_cache(api_key: str, free_tier: bool = False):
    return get_all_gemini_models(api_key, free_tier)


@st.cache_data(show_spinner=False, ttl=600) 
def get_cached_profile_matches(_storage: StorageService, profile_id: str):
    """SOP: Cache the expensive Pinecone query for profile matches."""
    matches = _storage.find_job_matches_for_profile(profile_id)
    return [m.model_dump_json() for m in matches]

@st.cache_data(show_spinner=False, ttl=3600)
def get_cached_user_profiles(_storage: StorageService, user_id: str):
    """SOP: Cache the list of profiles for the selector."""
    return _storage.find_all_candidate_profiles(user_id)

@st.cache_data(show_spinner=False, ttl=3600)
def get_cached_all_jobs_for_user(_storage: StorageService, user_id: str):
    """Cache all jobs for a singler user"""
    matches = _storage.find_all_jobs_for_user(user_id)
    return [m.model_dump_json() for m in matches]

@st.cache_data(show_spinner=False, ttl=3600)
def get_cached_raw_job(_storage: StorageService, job_url: str):
    """Cache the heavy raw job details to prevent re-fetching over the network."""
    raw_job = _storage.find_raw_job_by_url(job_url)
    
    if raw_job is None:
        return None
        
    return raw_job.model_dump_json()

@st.cache_data(show_spinner=False, ttl=3600)
def get_cached_global_jobs(_storage: StorageService, limit=100):
    results = _storage.get_all_global_jobs(limit)
    return [j.model_dump_json() for j in results]

@st.cache_data(show_spinner=False, ttl=3600)
def get_cached_market_data(_storage: StorageService):
    return _storage.get_market_data()

@st.cache_data(show_spinner=False)
def get_market_dfs(_jobs, _profiles):
    """SOP: Convert Pydantic models to DataFrames once and cache them."""
    df_j = pd.DataFrame([j for j in _jobs])
    df_p = pd.DataFrame([p for p in _profiles])
    return df_j, df_p

@st.cache_resource(show_spinner=False, ttl=3600)
def get_cached_salary_chart(df):
    return create_salary_chart(df)

@st.cache_data(show_spinner=False)
def get_cached_stats(_storage: StorageService):
    return _storage.get_index_metrics()