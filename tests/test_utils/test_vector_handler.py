import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
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
    recent_date = datetime.now(timezone.utc).isoformat()
    assert is_cache_expired({"last_synced_at": recent_date}, ttl_days=7) is False

    # 2. Test expired
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
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



@pytest.mark.asyncio
@patch("src.utils.vector_handler.get_user_analysis_store")
@patch("src.utils.embeddings_handler.get_embeddings")
async def test_save_candidate_profile(mock_embed, mock_store, mock_settings, mock_candidate_profile):
    mock_embed.return_value = MagicMock()
    mock_vectorstore = MagicMock()
    mock_store.return_value = mock_vectorstore
    
    result_id = save_candidate_profile(
        profile=mock_candidate_profile,
        store=mock_vectorstore,
        user_id="user_123",
        config={}
    )

    assert result_id is not None
    mock_vectorstore.add_texts.assert_called_once()
    
    _, kwargs = mock_vectorstore.add_texts.call_args
    
    texts = kwargs.get('texts', [])
    print(texts)
    assert any("Ruy Zambrano" in t for t in texts)
    
    metadatas = kwargs.get('metadatas', [{}])
    print(metadatas)
    assert metadatas[0].get("user_id") == "user_123"

@patch("src.utils.vector_handler.log_message")
def test_sync_with_global_library_new_job(mock_log, mock_pinecone, mock_streamlit):
    store, index, fetch_res = mock_pinecone
    
    fetch_res.vectors = {}

    job = RawJobMatch(
        title="New Job",
        job_url="unique_url",
        description="desc",
        company_name="C",
        location="MA"
    )
    raw_results = ListRawJobMatch(jobs=[job])

    final_jobs = sync_with_global_library(store, raw_results)

    assert len(final_jobs) == 1
    store.add_texts.assert_called_once()
    mock_log.assert_any_call("🆕 New: New Job")
