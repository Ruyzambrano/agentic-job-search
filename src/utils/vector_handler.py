from os import environ as ENV
from datetime import datetime
from json import loads, dumps

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.schema import CandidateProfile, AnalysedJobMatch, RawJobMatch
from src.utils.func import log_message

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model=ENV.get("EMBEDDING_MODEL"))

def get_global_jobs_store():
    """Collection for raw, deduplicated jobs across all users."""
    return Chroma(
        collection_name="global_raw_jobs",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db",
    )

def get_user_analysis_store():
    """Collection for personalized user-specific match analysis."""
    return Chroma(
        collection_name="user_job_analyses",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db",
    )


def save_candidate_profile(store, user_id: str, profile: CandidateProfile):
    timestamp_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_id = f"profile_{user_id}_{timestamp_id}"
    
    document_content = (
        f"{profile.summary} "
        f"Skills: {', '.join(profile.key_skills)}. "
        f"Roles: {', '.join(profile.job_titles)}"
    )
    metadata = profile.model_dump()

    for key, value in metadata.items():
        if isinstance(value, list):
            metadata[key] = dumps(value)
    
    metadata["user_id"] = user_id
    metadata["created_at"] = datetime.now().isoformat()

    store.add_texts(
        texts=[document_content],
        metadatas=[metadata],
        ids=[profile_id]
    )
    return profile_id

def fetch_candidate_profile(profile_id: str, user_store) -> CandidateProfile:
    record = user_store.get(ids=[profile_id])
    if not record["metadatas"]:
        raise ValueError(f"Profile {profile_id} not found.")
    
    meta = record["metadatas"][0]
    for field in ["job_titles", "key_skills", "industries"]:
        if isinstance(meta.get(field), str):
            meta[field] = loads(meta[field])
    return CandidateProfile(**meta)

def check_analysis_cache(store, jobs: list[RawJobMatch], profile_id: str):
    """Checks the store for cached data"""
    hits, misses = [], []
    for job in jobs:
        cache_id = f"{profile_id}_{job.job_url}"
        existing = store.get(ids=[cache_id]) 
        
        if existing and existing.get("metadatas"):
            log_message(f"Cache Hit: {job.title} at {job.company_name}")
            raw_json = existing["metadatas"][0].get("analysis_json")
            hits.append(AnalysedJobMatch(**loads(raw_json)))
        else:
            misses.append(job)
    return hits, misses


def sync_with_global_library(global_store, raw_results):
    final_jobs = []
    seen_urls = set()

    for job in raw_results.jobs:
        if job.job_url not in seen_urls:
            existing = global_store.get(ids=[job.job_url])
            seen_urls.add(job.job_url)

            if not existing.get("ids"):
                global_store.add_texts(
                    texts=[job.description],
                    metadatas=[job.model_dump()],
                    ids=[job.job_url]
                )
                final_jobs.append(job)
                log_message(f"New job saved to global library: {job.title}")
                
            else:
                cached_metadata = existing['metadatas'][0]
                if isinstance(cached_metadata.get("qualifications"), str):
                    cached_metadata["qualifications"] = loads(cached_metadata["qualifications"])
                
                cached_job = RawJobMatch(**cached_metadata)
                final_jobs.append(cached_job)
                log_message(f"Using cached global data for: {job.title}")
    return final_jobs

def save_job_analyses(user_store, jobs: list[AnalysedJobMatch], user_id, profile_id):
    """Saves personalized analysis to the vector store."""
    user_store.add_texts(
        texts=[a.top_applicant_reasoning for a in jobs],
        metadatas=[{
            "user_id": user_id,
            "profile_id": profile_id,
            "analysis_json": a.model_dump_json()
        } for a in jobs],
        ids=[f"{profile_id}_{a.job_url}" for a in jobs]
    )

def find_all_candidate_profiles(user_store, user_id):
    result = user_store.get(where={"user_id": user_id})
    
    raw_ids = result.get("ids", [])
    raw_metadatas = result.get("metadatas", [])

    if not raw_metadatas:
        raise ValueError("No data available")
    
    final_profiles = []

    for doc_id, meta in zip(raw_ids, raw_metadatas):
        if "full_name" in meta:
            meta["profile_id"] = doc_id
            for field in ["job_titles", "key_skills", "industries"]:
                if isinstance(meta.get(field), str):
                    try:
                        meta[field] = loads(meta[field])
                    except Exception:
                        meta[field] = []
            
            final_profiles.append(meta)

    final_profiles.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return final_profiles

def find_all_roles_for_profile(jobs_store, profile_id):
    results = jobs_store.get(
        where={"profile_id": profile_id}
    )
    matches = []
    
    for meta in results.get("metadatas", []):
        if "analysis_json" in meta:
            job_dict = loads(meta["analysis_json"])
            matches.append(AnalysedJobMatch(**job_dict))
            
    matches.sort(key=lambda x: x.top_applicant_score, reverse=True)
    
    return matches