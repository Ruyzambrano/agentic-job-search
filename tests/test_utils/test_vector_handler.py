import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from src.utils.vector_handler import (
    is_cache_expired,
    prepare_for_storage,
    sync_with_global_library,
    save_candidate_profile,
)
from src.schema import RawJobMatch, ListRawJobMatch, CandidateProfile

# --- Logic Tests (No Mocks Required) ---


def test_is_cache_expired():
    # 1. Test not expired
    recent_date = datetime.now().isoformat()
    assert is_cache_expired({"last_synced_at": recent_date}, ttl_days=7) is False

    # 2. Test expired
    old_date = (datetime.now() - timedelta(days=10)).isoformat()
    assert is_cache_expired({"last_synced_at": old_date}, ttl_days=7) is True

    # 3. Test missing date
    assert is_cache_expired({}, ttl_days=7) is True


def test_prepare_for_storage():
    job = RawJobMatch(
        title="Engineer",
        company_name="Test",
        description="Text",
        job_url="http://test.com",
        location="Somewhere",
    )
    meta = prepare_for_storage(job)
    assert "last_synced_at" in meta
    assert meta["title"] == "Engineer"


# --- Database Integration Tests (With Mocks) ---


@patch("src.utils.vector_handler.get_embeddings")
def test_save_candidate_profile(mock_embeddings, mock_chroma_store):
    profile = CandidateProfile(
        full_name="Ruy Zambrano",
        summary="AI Dev",
        job_titles=["Engineer"],
        key_skills=["Python"],
        industries=["Tech"],
        years_of_experience=1000,
        current_location="Here",
        work_preference="Never",
    )

    # We use a mock store created via a fixture (see below)
    user_id = "user123"
    profile_id = save_candidate_profile(mock_chroma_store, user_id, profile, {})

    assert "profile_user123_" in profile_id
    # Verify the store's add_texts was called
    mock_chroma_store.add_texts.assert_called_once()


@patch("src.utils.vector_handler.log_message")
def test_sync_with_global_library_new_job(mock_log, mock_chroma_store):
    mock_chroma_store.get.return_value = {"ids": [], "metadatas": []}
    mock_chroma_store.add_texts = MagicMock()

    job = RawJobMatch(
        title="New Job",
        job_url="unique_url",
        description="desc",
        company_name="C",
        location="MA",
    )
    raw_results = ListRawJobMatch(jobs=[job])

    final_jobs = sync_with_global_library(mock_chroma_store, raw_results)

    mock_chroma_store.add_texts.assert_called_once()
    assert final_jobs[0].title == "New Job"
