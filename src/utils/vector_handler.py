from os import environ as ENV
from datetime import datetime
from json import loads, dumps

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.schema import CandidateProfile, AnalysedJobMatch, RawJobMatch

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
    """Note how 'store' is now a parameter, not something we 'get' inside."""
    hits, misses = [], []
    for job in jobs:
        cache_id = f"{profile_id}_{job.job_url}"
        existing = store.get(ids=[cache_id]) 
        
        if existing and existing.get("metadatas"):
            print(f"LOG: Cache Hit: {job.title} at {job.company_name}")
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
                print(f"LOG: New job saved to global library: {job.title}")
                
            else:
                cached_metadata = existing['metadatas'][0]
                if isinstance(cached_metadata.get("qualifications"), str):
                    cached_metadata["qualifications"] = loads(cached_metadata["qualifications"])
                
                cached_job = RawJobMatch(**cached_metadata)
                final_jobs.append(cached_job)
                print(f"DEBUG: Using cached global data for: {job.title}")
    return final_jobs