"""Storage Service: Handles all vector database persistence and retrieval."""

from datetime import datetime, timezone, timedelta
from json import loads, dumps
from typing import List, Optional, Any
import streamlit as st

from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from src.schema import (
    CandidateProfile,
    AnalysedJobMatchWithMeta,
    RawJobMatch,
    generate_safe_id
)
from src.utils.text_processing import clean_text_for_embedding


class StorageService:
    def __init__(self, index_name: str, embeddings: Any):
        """
        Initializes the service.
        """
        self.index_name = index_name
        self.embeddings = embeddings
        self.NS_USER_DATA = "user_job_analyses"
        self.NS_GLOBAL_JOBS = "global_raw_jobs"
        self.NS_ANALYSES = "user_job_analyses"
        self.pc = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
        try: 
            self.pc.list_indexes()
        except Exception as e:
            raise ConnectionError(f"Pinecone authentication error: {str(e)}")

    def _get_store(self, namespace: str) -> PineconeVectorStore:
        """Internal helper to create a LangChain Pinecone store instance."""
        return PineconeVectorStore(
            index_name=self.index_name, embedding=self.embeddings, namespace=namespace
        )

    def save_candidate_profile(self, user_id: str, profile: CandidateProfile) -> str:
        """Saves a new CV profile with the required document_type tag."""
        profile_id = (
            f"profile_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        metadata = profile.model_dump()

        metadata["document_type"] = "candidate_profile"
        metadata["user_id"] = user_id
        metadata["created_at"] = datetime.now(timezone.utc).isoformat()

        for key in ["job_titles", "key_skills", "industries"]:
            if key in metadata and isinstance(metadata[key], list):
                metadata[key] = dumps(metadata[key])

        store = self._get_store(self.NS_USER_DATA)
        store.add_texts(
            texts=[f"Profile: {profile.full_name}. Summary: {profile.summary}"],
            metadatas=[metadata],
            ids=[profile_id],
        )
        return profile_id

    def fetch_candidate_profile(self, profile_id: str) -> CandidateProfile:
        """Retrieves a specific profile by its ID."""
        store = self._get_store(self.NS_USER_DATA)
        index = store.get_pinecone_index(self.index_name)
        response = index.fetch(ids=[profile_id], namespace=self.NS_USER_DATA)

        if not response or profile_id not in response.vectors:
            raise ValueError(f"Profile {profile_id} not found.")

        meta = response.vectors[profile_id].metadata

        for field in ["job_titles", "key_skills", "industries"]:
            if isinstance(meta.get(field), str):
                try:
                    meta[field] = loads(meta[field])
                except:
                    meta[field] = []
        return CandidateProfile(**meta)

    def find_all_candidate_profiles(self, user_id: str) -> list[dict]:
        """Queries for all profiles belonging to a user using the SOP tag."""
        try:
            store = self._get_store(self.NS_USER_DATA)
            index = store.get_pinecone_index(self.index_name)

            results = index.query(
                vector=[0.0] * 3072,
                filter={
                    "user_id": {"$eq": user_id},
                    "document_type": {"$eq": "candidate_profile"},
                },
                namespace=self.NS_USER_DATA,
                top_k=100,
                include_metadata=True,
            )

            profiles = []
            for match in results.get("matches", []):
                meta = match.get("metadata", {})
                meta["profile_id"] = match.get("id")

                for field in ["job_titles", "key_skills", "industries"]:
                    if isinstance(meta.get(field), str):
                        try:
                            meta[field] = loads(meta[field])
                        except:
                            meta[field] = []
                profiles.append(meta)

            return sorted(profiles, key=lambda x: x.get("created_at", ""), reverse=True)
        except Exception as e:
            st.error(f"Error fetching profiles: {e}")
            return []

    def delete_profile(self, profile_id: str):
        """Deletes a profile from the vector store."""
        store = self._get_store(self.NS_USER_DATA)
        index = store.get_pinecone_index(self.index_name)
        index.delete(ids=[profile_id], namespace=self.NS_USER_DATA)

    def save_job_analyses(
        self, jobs: List[AnalysedJobMatchWithMeta], user_id: str, profile_id: str
    ):
        """Saves processed AI job analyses with appropriate tagging."""
        store = self._get_store(self.NS_USER_DATA)
        texts, metadatas, ids = [], [], []

        for a in jobs:
            ids.append(generate_safe_id(f"{profile_id}_{a.job_url}"))
            texts.append(clean_text_for_embedding(a.top_applicant_reasoning))
            metadatas.append(
                {
                    "document_type": "job_analysis",
                    "user_id": user_id,
                    "profile_id": profile_id,
                    "analysis_json": a.model_dump_json(),
                    "job_url": a.job_url,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def check_analysis_cache(self, jobs: Any, profile_id: str):
        """Checks if a job has already been analyzed for a specific profile."""
        if hasattr(jobs, 'jobs'):
            job_list = jobs.jobs
        elif isinstance(jobs, list):
            job_list = jobs
        else:
            job_list = list(jobs) if isinstance(jobs, (tuple, set)) else []

        store = self._get_store(self.NS_USER_DATA)
        index = store.get_pinecone_index(self.index_name)
        hits, misses = [], []

        cache_map = {
            generate_safe_id(f"{profile_id}_{j.job_url}"): j 
            for j in job_list if hasattr(j, 'job_url')
        }
        
        if not cache_map:
            return [], job_list

        response = index.fetch(ids=list(cache_map.keys()), namespace=self.NS_USER_DATA)
        vectors = response.vectors if response else {}

        for cid, job in cache_map.items():
            if cid in vectors:
                meta = vectors[cid].metadata
                hits.append(AnalysedJobMatchWithMeta(**loads(meta["analysis_json"])))
            else:
                misses.append(job)
                
        return hits, misses

    def sync_global_library(
    self, raw_results: Any, ttl_days: int = 7) -> List[Any]:
        """Syncs scraped jobs to a global library to avoid redundant processing."""
        if not raw_results or not hasattr(raw_results, "jobs") or not raw_results.jobs:
            return []

        store = self._get_store(self.NS_GLOBAL_JOBS)
        index = store.get_pinecone_index(self.index_name)
        final_jobs, to_upsert = [], []

        job_map = {generate_safe_id(j.job_url): j for j in raw_results.jobs if getattr(j, "job_url", None)}
        if not job_map:
            return []
        
        ids_to_fetch = list(job_map.keys())
        response = index.fetch(ids=ids_to_fetch, namespace=self.NS_GLOBAL_JOBS)
        vectors = response.vectors if response else {}

        for uid, job in job_map.items():
            existing = vectors.get(uid)
            if not existing or self._is_expired(existing.metadata, ttl_days):
                meta = self._prepare_job_meta(job)
                to_upsert.append(
                    {
                        "id": uid,
                        "text": clean_text_for_embedding(job.description),
                        "metadata": meta,
                    }
                )
                final_jobs.append(job)
            else:
                try:
                    final_jobs.append(self._parse_cached_job(existing.metadata))
                except:
                    final_jobs.append(job)

        if to_upsert:
            store.add_texts(
                texts=[x["text"] for x in to_upsert],
                ids=[x["id"] for x in to_upsert],
                metadatas=[
                    {
                        **x["metadata"], 
                        "job_url": x["metadata"].get("job_url")
                    } for x in to_upsert
                ],
            )
        return [
            RawJobMatch(**j) if isinstance(j, dict) else j 
            for j in final_jobs
        ]

    def _is_expired(self, meta: dict, ttl: int) -> bool:
        last = meta.get("last_synced_at")
        if not last:
            return True
        return datetime.now(timezone.utc) > (
            datetime.fromisoformat(last) + timedelta(days=ttl)
        )

    def _prepare_job_meta(self, job: RawJobMatch) -> dict:
        d = job.model_dump(mode='json') 
        
        d["id"] = job.id
        d["created_at_ts"] = int(datetime.now(timezone.utc).timestamp())
        
        for k, v in d.items():
            if v is None:
                d[k] = 0 if "salary" in k else ""
            if isinstance(v, (list, dict)):
                d[k] = dumps(v)
        
        d["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        return d

    def _parse_cached_job(self, metadata: dict) -> RawJobMatch:
        list_fields = ["qualifications", "key_skills", "attributes"]
        for field in list_fields:
            value = metadata.get(field)
            if isinstance(value, str):
                try:
                    metadata[field] = loads(value)
                except:
                    metadata[field] = []
        metadata.pop("id", None)
        return RawJobMatch(**metadata)

    def find_job_matches_for_profile(
        self, profile_id: str
    ) -> List[AnalysedJobMatchWithMeta]:
        """
        SOP: Fetches all analysed job results for a specific profile ID.
        Uses the 3072-dimension dummy vector and filters by document_type.
        """
        try:
            store = self._get_store(self.NS_USER_DATA)
            index = store.get_pinecone_index(self.index_name)

            results = index.query(
                vector=[0.0] * 3072,
                filter={"profile_id": profile_id, "document_type": "job_analysis"},
                namespace=self.NS_USER_DATA,
                top_k=20,
                include_metadata=True,
            )

            matches = []
            for m in results.get("matches", []):
                meta = m.get("metadata", {})
                analysis_json = meta.get("analysis_json")

                if analysis_json:
                    try:
                        match_obj = AnalysedJobMatchWithMeta(**loads(analysis_json))
                        matches.append(match_obj)
                    except Exception as parse_error:
                        print(f"Error parsing job analysis: {parse_error}")

            return sorted(matches, key=lambda x: x.top_applicant_score, reverse=True)

        except Exception as e:
            st.error(f"Error fetching job matches from StorageService: {e}")
            return []

    def delete_current_profile(self, profile_id: str):
        """
        SOP: Deletes a specific profile vector from the user data namespace.
        """
        try:
            store = self._get_store(self.NS_USER_DATA)
            index = store.get_pinecone_index(self.index_name)
            index.delete(ids=[profile_id], namespace=self.NS_USER_DATA)
            return True
        except Exception as e:
            print(f"Error deleting profile {profile_id}: {e}")
            return False

    def find_all_jobs_for_user(self, user_id: str) -> List[AnalysedJobMatchWithMeta]:
        """
        SOP: Fetches every job analysis vector belonging to a user ID.
        Ignores profile_id to give a 'Global' view of the user's market matches.
        """
        try:
            store = self._get_store(self.NS_USER_DATA)
            index = store.get_pinecone_index(self.index_name)
            results = index.query(
                vector=[0.0] * 3072,
                filter={
                    "user_id": {"$eq": user_id},
                    "document_type": {"$eq": "job_analysis"},
                },
                namespace=self.NS_USER_DATA,
                top_k=100,
                include_metadata=True,
            )

            matches = []
            seen_urls = set()
            for m in results.get("matches", []):
                meta = m.get("metadata", {})
                analysis_json = meta.get("analysis_json")
                if analysis_json:
                    try:
                        job = AnalysedJobMatchWithMeta(**loads(analysis_json))
                        if job.job_url not in seen_urls and job.title and job.company:
                            matches.append(job)
                            seen_urls.add(job.job_url)
                    except Exception as e:
                        print(f"Skipping malformed job record: {e}")

            return matches
        except Exception as e:
            print(f"Error fetching all user jobs: {e}")
            return []

    def find_raw_job_by_url(self, job_url: str) -> Optional[RawJobMatch]:
        """
        Retrieves the original raw job data from the global namespace.
        Uses the job_url as the filter.
        """
        try:
            job_id = generate_safe_id(job_url)
            
            store = self._get_store(self.NS_GLOBAL_JOBS)
            index = store.get_pinecone_index(self.index_name)
            
            response = index.fetch(ids=[job_id], namespace=self.NS_GLOBAL_JOBS)
            
            if response and job_id in response.vectors:
                return self._parse_cached_job(response.vectors[job_id].metadata)

            results = index.query(
                vector=[0.0] * 3072,
                filter={"job_url": {"$eq": job_url}},
                namespace=self.NS_GLOBAL_JOBS,
                top_k=1,
                include_metadata=True,
            )

            if getattr(results, "matches"):
                return self._parse_cached_job(results["matches"][0]["metadata"])
            
            return None

        except Exception as e:
            st.error(f"Error fetching raw job: {e}")
            return None

    def get_all_global_jobs(self, limit: int = 100) -> List[RawJobMatch]:
        """Retrieves raw job data using the hashed ID (O(1) lookup)."""
        try:
            store = self._get_store(self.NS_USER_DATA)
            index = store.get_pinecone_index(self.index_name)
            results = index.query(
                vector=[0.0] * 3072,
                top_k=limit,
                namespace=self.NS_GLOBAL_JOBS,
                include_metadata=True,
            )

            jobs = []
            for match in results.get("matches", []):
                meta = match.get("metadata", {})
                jobs.append(RawJobMatch(**meta))
            return jobs
        except Exception as e:
            print(f"Error fetching global jobs: {e}")
            return []

    def get_market_data(self) -> tuple[list[dict], list[dict]]:
        """Fetches all candidate profiles and global jobs for visualization."""
        store = self._get_store(self.NS_USER_DATA)
        index = store.get_pinecone_index(self.index_name)
        profile_results = index.query(
            vector=[0.0] * 3072,
            top_k=100,
            filter={"document_type": {"$eq": "candidate_profile"}},
            namespace=self.NS_USER_DATA,
            include_metadata=True,
        )

        profiles = []
        for m in profile_results.get("matches", []):
            meta = m["metadata"]
            for field in ["job_titles", "key_skills", "industries"]:
                if isinstance(meta.get(field), str):
                    try:
                        meta[field] = loads(meta[field])
                    except:
                        meta[field] = []
            profiles.append(meta)

        job_results = index.query(
            vector=[0.0] * 3072,
            top_k=1000,
            namespace=self.NS_GLOBAL_JOBS,
            include_metadata=True,
        )
        jobs = [m["metadata"] for m in job_results.get("matches", [])]

        return profiles, jobs
    
    def cleanup_stale_jobs(self, months_old: int = 6):
        """
        SOP: Purges jobs older than X months from the global library.
        Requires 'created_at_ts' metadata field to be present.
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=months_old * 30)
            cutoff_ts = int(cutoff_date.timestamp())

            index = self._get_store(self.NS_GLOBAL_JOBS).get_pinecone_index(self.index_name)

            delete_response = index.delete(
                filter={"created_at_ts": {"$lt": cutoff_ts}},
                namespace=self.NS_GLOBAL_JOBS
            )
            
            st.success(f"Cleanup complete! Removed jobs older than {cutoff_date.date()}.")
            return delete_response
        except Exception as e:
            st.error(f"Cleanup failed: {e}")
            return None
