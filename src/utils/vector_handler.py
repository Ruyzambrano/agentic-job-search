from datetime import datetime, timedelta
from json import loads, dumps
from typing import List

from langchain_pinecone import PineconeVectorStore
from langchain_core.runnables import RunnableConfig

from src.schema import (
    CandidateProfile,
    AnalysedJobMatchWithMeta,
    RawJobMatch,
    ListRawJobMatch,
)
from src.utils.func import log_message


def get_global_jobs_store(embedding_model):
    """Global deduplicated jobs stored in the 'global' namespace."""
    return PineconeVectorStore(
        index_name="agent-pipeline", 
        embedding=embedding_model,
        namespace="global_raw_jobs"
    )


def get_user_analysis_store(embedding_model):
    """Personalized analyses stored in the 'user_analyses' namespace."""
    return PineconeVectorStore(
        index_name="agent-pipeline", 
        embedding=embedding_model,
        namespace="user_job_analyses"
    )


def save_candidate_profile(
    store, user_id: str, profile: CandidateProfile, config: RunnableConfig
):
    timestamp_id = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    metadata["created_at"] = datetime.now().isoformat()

    store.add_texts(texts=[document_content], metadatas=[metadata], ids=[profile_id])
    return profile_id


def fetch_candidate_profile(profile_id: str, user_store: PineconeVectorStore) -> CandidateProfile:
    index = user_store.get_pinecone_index("agent-pipeline")
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
    """Checks the store for cached data"""
    hits, misses = [], []
    for job in jobs:
        cache_id = f"{profile_id}_{job.job_url}"
        existing = store.get_by_ids(ids=[cache_id])

        if existing and existing.get("metadatas"):
            log_message(f"Cache Hit: {job.title} at {job.company_name}")
            raw_json = existing["metadatas"][0].get("analysis_json")
            hits.append(AnalysedJobMatchWithMeta(**loads(raw_json)))
        else:
            misses.append(job)
    return hits, misses


def is_cache_expired(metadata: dict, ttl_days: int) -> bool:
    """Checks if the stored record has outlived its TTL."""
    last_synced = metadata.get("last_synced_at")
    if not last_synced:
        return True

    expiry_date = datetime.fromisoformat(last_synced) + timedelta(days=ttl_days)
    return datetime.now() > expiry_date


def prepare_for_storage(job: RawJobMatch) -> dict:
    """Ensures metadata is DB-ready with a fresh timestamp."""
    meta = job.model_dump()
    meta["last_synced_at"] = datetime.now().isoformat()
    return meta


def parse_cached_meta(metadata: dict) -> RawJobMatch:
    """Reconstructs Pydantic model, handling JSON string conversions."""
    list_fields = ["qualifications", "key_skills", "attributes"]
    for field in list_fields:
        if isinstance(metadata.get(field), str):
            metadata[field] = loads(metadata[field])
    return RawJobMatch(**metadata)


def sync_with_global_library(
    global_store: PineconeVectorStore, raw_results: ListRawJobMatch, ttl_days: int = 7
) -> List[RawJobMatch]:
    final_jobs = []
    seen_identifiers = set()
    log_message(f"Syncing roles with Global Library")
    for job in raw_results.jobs:
        unique_key = f"{job.job_url}_{job.title}"
        if unique_key in seen_identifiers:
            continue
        seen_identifiers.add(unique_key)

        res = global_store.get_by_ids(ids=[job.job_url])
        existing_meta = res["metadatas"][0] if res.get("ids") else None

        if not existing_meta or is_cache_expired(existing_meta, ttl_days):
            try:
                global_store.add_texts(
                    texts=[job.description],
                    metadatas=[prepare_for_storage(job)],
                    ids=[job.job_url],
                )
                final_jobs.append(job)
                status = "✨ Updated" if existing_meta else "🆕 New"
                log_message(f"{status}: {job.title}")
            except Exception as e:
                log_message(f"❌ Storage Error ({job.title}): {e}")
                final_jobs.append(job)
        else:
            try:
                final_jobs.append(parse_cached_meta(existing_meta))
                log_message(f"📦 Cached: {job.title}")
            except Exception:
                final_jobs.append(job)
    return final_jobs


def save_job_analyses(
    user_store: PineconeVectorStore, jobs: list[AnalysedJobMatchWithMeta], user_id, profile_id
):
    """Saves personalized analysis to the vector store."""
    user_store.add_texts(
        texts=[a.top_applicant_reasoning for a in jobs],
        metadatas=[
            {
                "user_id": user_id,
                "profile_id": profile_id,
                "analysed_at": (
                    a.analysed_at.isoformat()
                    if hasattr(a.analysed_at, "isoformat")
                    else str(a.analysed_at)
                ),
                "analysis_json": a.model_dump_json(),
                "target_role": a.target_role,
                "target_location": a.target_location,
            }
            for a in jobs
        ],
        ids=[f"{profile_id}_{a.job_url}" for a in jobs],
    )

def find_all_candidate_profiles(user_store, user_id):
    index = user_store.get_pinecone_index('agent-pipeline')
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
    index = jobs_store.get_pinecone_index('agent-pipeline')
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
    index = jobs_store.get_pinecone_index('agent-pipeline')
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
    index = global_store.get_pinecone_index('agent-pipeline')
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
