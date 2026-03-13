from datetime import datetime, timedelta, timezone
from json import loads, dumps
from typing import List
import hashlib

import streamlit as st
from langchain_pinecone import PineconeVectorStore
from langchain_core.runnables import RunnableConfig

from src.schema import (
    CandidateProfile,
    AnalysedJobMatchWithMeta,
    RawJobMatch,
    ListRawJobMatch,
)
from src.utils.func import log_message

def generate_safe_id(input_string: str) -> str:
    """Creates a deterministic, ASCII-only MD5 hash of any string (URL, Title, etc)."""
    return hashlib.md5(input_string.encode('utf-8')).hexdigest()


def clean_text_for_embedding(text: str) -> str:
    """Prevents Gemini 'Empty Part' errors by ensuring text is never empty or None."""
    if not text or not text.strip():
        return "No description provided."
    return text.strip()


def get_global_jobs_store(embedding_model):
    """Global deduplicated jobs stored in the 'global' namespace."""
    return PineconeVectorStore(
        index_name=st.secrets.PINECONE_NAME, 
        embedding=embedding_model,
        namespace="global_raw_jobs"
    )


def get_user_analysis_store(embedding_model):
    """Personalized analyses stored in the 'user_analyses' namespace."""
    return PineconeVectorStore(
        index_name=st.secrets.PINECONE_NAME, 
        embedding=embedding_model,
        namespace="user_job_analyses"
    )


def save_candidate_profile(
    store, user_id: str, profile: CandidateProfile, config: RunnableConfig
):
    timestamp_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    profile_id = f"profile_{user_id}_{timestamp_id}"

    document_content = (
        f"Candidate: {profile.full_name}" 
        f"Summary: {profile.summary} "
        f"Skills: {', '.join(profile.key_skills)}. "
        f"Roles: {', '.join(profile.job_titles)}"
    )
    metadata = profile.model_dump()

    for key, value in metadata.items():
        if isinstance(value, list):
            metadata[key] = dumps(value)

    metadata["user_id"] = user_id
    metadata["created_at"] = datetime.now(timezone.utc).isoformat()

    store.add_texts(texts=[document_content], metadatas=[metadata], ids=[profile_id])
    return profile_id


def fetch_candidate_profile(profile_id: str, user_store: PineconeVectorStore) -> CandidateProfile:
    index = user_store.get_pinecone_index(st.secrets.PINECONE_NAME)
    ns = user_store._namespace 
    log_message(f"🔍 Fetching ID from Namespace: '{ns}'")
    
    response = index.fetch(ids=[profile_id], namespace=ns)
    
    if not response or profile_id not in response.vectors:
        stats = index.describe_index_stats()
        log_message(f"❌ ID not found in '{ns}'. Available namespaces: {stats['namespaces'].keys()}")
        raise ValueError(f"Profile {profile_id} not found in namespace '{ns}'.")
    meta = response.vectors[profile_id].metadata

    for field in ["job_titles", "key_skills", "industries"]:
        if isinstance(meta.get(field), str):
            meta[field] = loads(meta[field])
    return CandidateProfile(**meta)


def check_analysis_cache(store: PineconeVectorStore, jobs: list[RawJobMatch], profile_id: str):
    hits, misses = [], []
    index = store.get_pinecone_index(st.secrets.PINECONE_NAME)
    ns = store._namespace

    cache_map = {generate_safe_id(f"{profile_id}_{job.job_url}"): job for job in jobs}
    cache_ids = list(cache_map.keys())
    
    if not cache_ids:
        return [], []
    
    response = index.fetch(ids=cache_ids, namespace=ns)
    existing_vectors = response.vectors if response else {}

    for cid, job in cache_map.items():
        if cid in existing_vectors:
            log_message(f"✅ Cache Hit: {job.title}")
            meta = existing_vectors[cid].metadata
            raw_json = meta.get("analysis_json")
            if raw_json:
                hits.append(AnalysedJobMatchWithMeta(**loads(raw_json)))
            else:
                misses.append(job)
        else:
            misses.append(job)
            
    return hits, misses


def is_cache_expired(metadata: dict, ttl_days: int) -> bool:
    """Checks if the stored record has outlived its TTL."""
    last_synced = metadata.get("last_synced_at")
    if not last_synced:
        return True

    expiry_date = datetime.fromisoformat(last_synced) + timedelta(days=ttl_days)
    return datetime.now(timezone.utc) > expiry_date


def prepare_for_storage(job: RawJobMatch) -> dict:
    """Ensures metadata is DB-ready: no nulls, ASCII safe, and fresh timestamps."""
    raw_meta = job.model_dump()
    clean_meta = {}

    for key, value in raw_meta.items():
        if isinstance(value, list):
            clean_meta[key] = [str(i) for i in value if i is not None]
        
        elif value is None:
            if "salary" in key or "score" in key:
                clean_meta[key] = 0
            else:
                clean_meta[key] = ""
        
        else:
            clean_meta[key] = value

    clean_meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    
    return clean_meta


def parse_cached_meta(metadata: dict) -> RawJobMatch:
    """Reconstructs Pydantic model, handling JSON string conversions."""
    list_fields = ["qualifications", "key_skills", "attributes"]
    for field in list_fields:
        if isinstance(metadata.get(field), str):
            metadata[field] = loads(metadata[field])
    return RawJobMatch(**metadata)


def sync_with_global_library(
    global_store: PineconeVectorStore, 
    raw_results: ListRawJobMatch, 
    ttl_days: int = 7
    ) -> List[RawJobMatch]:
    final_jobs = []
    jobs_to_upsert = []
    
    if not raw_results.jobs:
        log_message("ℹ️ No jobs provided to sync.")
        return []

    log_message(f"🔍 Syncing {len(raw_results.jobs)} roles with Global Library")
    
    index = global_store.get_pinecone_index(st.secrets.PINECONE_NAME)
    ns = global_store._namespace

    job_map = {generate_safe_id(j.job_url): j for j in raw_results.jobs}
    unique_ids = list(job_map.keys())

    try:
        response = index.fetch(ids=unique_ids, namespace=ns)
        existing_vectors = response.vectors if response and hasattr(response, 'vectors') else {}    
    except Exception as e:
        log_message(f"⚠️ Fetch Error: {e}. Proceeding with fresh sync.")
        existing_vectors = {}

    for uid, job in job_map.items():
        vector_data = existing_vectors.get(uid)
        existing_meta = vector_data.metadata if vector_data and hasattr(vector_data, 'metadata') else None
        
        if not existing_meta or is_cache_expired(existing_meta, ttl_days):
            jobs_to_upsert.append({
                "id": uid,
                # FIX: Protect against empty descriptions
                "text": clean_text_for_embedding(job.description),
                "metadata": prepare_for_storage(job) 
            })
            final_jobs.append(job)
            status = "✨ Updated" if existing_meta else "🆕 New"
            log_message(f"{status}: {job.title}")
        else:
            try:
                final_jobs.append(parse_cached_meta(existing_meta))
                log_message(f"📦 Cached: {job.title}")
            except Exception as e:
                log_message(f"⚠️ Resyncing {job.title}: {e}")
                jobs_to_upsert.append({
                    "id": uid, 
                    "text": clean_text_for_embedding(job.description), 
                    "metadata": prepare_for_storage(job)
                })
                final_jobs.append(job)

    if jobs_to_upsert:
        try:
            log_message(f"🚀 Batch uploading {len(jobs_to_upsert)} jobs to Pinecone...")
            global_store.add_texts(
                texts=[j["text"] for j in jobs_to_upsert],
                metadatas=[j["metadata"] for j in jobs_to_upsert],
                ids=[j["id"] for j in jobs_to_upsert]
            )
        except Exception as e:
            log_message(f"❌ Critical Storage Error: {e}")

    return final_jobs


def save_job_analyses(
    user_store: PineconeVectorStore, jobs: list[AnalysedJobMatchWithMeta], user_id, profile_id
):
    if not jobs:
        return

    texts = [clean_text_for_embedding(a.top_applicant_reasoning) for a in jobs]
    metadatas = []
    ids = []

    for a in jobs:
        meta = {
            "user_id": user_id,
            "profile_id": profile_id,
            "analysed_at": a.analysed_at.isoformat() if hasattr(a.analysed_at, "isoformat") else str(a.analysed_at),
            "analysis_json": a.model_dump_json(),
            "target_role": a.target_role,
            "target_location": a.target_location,
            "job_url": a.job_url 
        }
        metadatas.append(meta)
        ids.append(generate_safe_id(f"{profile_id}_{a.job_url}"))

    user_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

def find_all_candidate_profiles(user_store, user_id):
    index = user_store.get_pinecone_index(st.secrets.PINECONE_NAME)
    ns = user_store._namespace
    
    zero_vector = [0.0] * 3072 
    
    results = index.query(
        vector=zero_vector,
        top_k=100,
        namespace=ns,
        filter={"user_id": user_id},
        include_metadata=True
    )

    if not results or not results['matches']:
        return []

    final_profiles = []
    for match in results['matches']:
        meta = match['metadata']
        if "full_name" in meta:
            meta["profile_id"] = match['id']
            # Re-parse JSON fields
            for field in ["job_titles", "key_skills", "industries"]:
                if isinstance(meta.get(field), str):
                    try:
                        meta[field] = loads(meta[field])
                    except:
                        meta[field] = []
            final_profiles.append(meta)

    final_profiles.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return final_profiles


def find_all_roles_for_profile(jobs_store, profile_id):
    results = jobs_store.search(
        query="job analysis",
        search_type="similarity",
        filter={"profile_id": profile_id},
        k=100
    )
    matches = []
    
    for doc in results:
        meta = doc.metadata
        if "analysis_json" in meta:
            job_dict = loads(meta["analysis_json"])
            matches.append(AnalysedJobMatchWithMeta(**job_dict))

    return matches

def find_all_roles_for_profile(jobs_store, profile_id):
    index = jobs_store.get_pinecone_index(st.secrets.PINECONE_NAME)
    zero_vector = [0.0] * 3072 

    results = index.query(
        vector=zero_vector,
        top_k=100,
        namespace=jobs_store._namespace,
        filter={"profile_id": profile_id},
        include_metadata=True
    )

    matches = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        if "analysis_json" in meta:
            job_dict = loads(meta["analysis_json"])
            matches.append(AnalysedJobMatchWithMeta(**job_dict))

    return matches


def find_all_roles_for_user(jobs_store, user_id):
    index = jobs_store.get_pinecone_index(st.secrets.PINECONE_NAME)
    zero_vector = [0.0] * 3072

    results = index.query(
        vector=zero_vector,
        top_k=100,
        namespace=jobs_store._namespace,
        filter={"user_id": user_id},
        include_metadata=True
    )

    matches = []
    seen_urls = set()
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        if "analysis_json" in meta:
            job_dict = loads(meta["analysis_json"])
            
            if job_dict.get("analysed_at"):
                job_url = job_dict.get("job_url")
                if job_url not in seen_urls:
                    seen_urls.add(job_url)
                    matches.append(AnalysedJobMatchWithMeta(**job_dict))

    return matches


def fetch_raw_job_data(global_store, job_url) -> RawJobMatch:
    """Fetches a single raw job by its URL ID without using embeddings."""
    index = global_store.get_pinecone_index(st.secrets.PINECONE_NAME)
    ns = global_store._namespace
    
    response = index.fetch(ids=[job_url], namespace=ns)
    
    if response and job_url in response.vectors:
        meta = response.vectors[job_url]['metadata']
        
        list_fields = ["qualifications", "key_skills", "attributes"]
        for field in list_fields:
            if isinstance(meta.get(field), str):
                try:
                    import json
                    meta[field] = json.loads(meta[field])
                except Exception:
                    meta[field] = []
                    
        return RawJobMatch(**meta)
    
    return None


def delete_profile(store, profile_id):
    store.delete(ids=[profile_id])


def get_all_jobs_global(global_store):
    global_store
