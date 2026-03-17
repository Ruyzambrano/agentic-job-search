import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.services.storage_service import StorageService
from src.schema import RawJobMatch, RawJobMatchList
from src.utils.text_processing import generate_safe_id

@pytest.fixture
def mock_embeddings():
    """Mock embeddings that return 3072-dimension vectors."""
    mock = MagicMock()
    mock.embed_query.return_value = [0.0] * 3072
    return mock

@pytest.fixture
def storage_service(mock_pinecone, mock_embeddings):
    """Instantiates the StorageService with a mocked Pinecone index."""
    _, index = mock_pinecone
    service = StorageService(index_name="test-index", embeddings=mock_embeddings)
    with patch.object(service, '_get_store') as mock_get_store:
        mock_store = MagicMock()
        mock_store.get_pinecone_index.return_value = index
        mock_get_store.return_value = mock_store
        yield service, index

def test_save_candidate_profile_serialization(mock_pinecone, mock_candidate_profile):
    """
    SOP: Test that the REAL service logic correctly serializes Pydantic lists 
    into JSON strings before sending to Pinecone.
    """
    user_id = "test_user_123"
    _, index = mock_pinecone
    
    mock_emb = MagicMock()
    service = StorageService(index_name="test-index", embeddings=mock_emb)
    
    mock_store = MagicMock()
    service._get_store = MagicMock(return_value=mock_store)
    
    service.save_candidate_profile(user_id, mock_candidate_profile)
    
    mock_store.add_texts.assert_called_once()
    
    _, kwargs = mock_store.add_texts.call_args
    metadata = kwargs['metadatas'][0]
    
    assert isinstance(metadata["key_skills"], str)
    assert "Python" in metadata["key_skills"]

def test_sync_global_library_expiration_logic(mock_pinecone, mock_raw_job):
    """
    SOP: Test that the REAL service logic correctly identifies an expired 
    job and calls add_texts to refresh it.
    """
    _, index = mock_pinecone
    mock_emb = MagicMock()
    service = StorageService(index_name="test-index", embeddings=mock_emb)
    
    mock_store = MagicMock()
    mock_store.get_pinecone_index.return_value = index
    service._get_store = MagicMock(return_value=mock_store)
    
    job_id = generate_safe_id(mock_raw_job.job_url)
    
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    mock_vector = MagicMock()
    mock_vector.metadata = {"last_synced_at": old_date}
    
    fetch_response = MagicMock()
    fetch_response.vectors = {job_id: mock_vector}
    index.fetch.return_value = fetch_response

    raw_list = RawJobMatchList(jobs=[mock_raw_job])
    service.sync_global_library(raw_list, ttl_days=7)
    
    assert mock_store.add_texts.called

def test_find_raw_job_by_url_schema_conversion(mock_pinecone, mock_raw_job):
    """
    Test that the REAL service correctly converts Pinecone 
    metadata dictionaries back into RawJobMatch Pydantic objects.
    """
    _, index = mock_pinecone
    mock_emb = MagicMock()
    service = StorageService(index_name="test-index", embeddings=mock_emb)
    
    mock_store = MagicMock()
    mock_store.get_pinecone_index.return_value = index
    service._get_store = MagicMock(return_value=mock_store)

    index.query.return_value = {
        "matches": [{
            "metadata": mock_raw_job.model_dump()
        }]
    }

    result = service.find_raw_job_by_url("https://example.com/1")

    assert isinstance(result, RawJobMatch)
    assert result.job_url == "https://example.com/1"
    assert result.title == mock_raw_job.title

def test_find_all_jobs_for_user_filtering(mock_pinecone):
    """
    Test that the REAL service correctly applies the Pinecone
    metadata filter for a specific user_id and uses the correct namespace.
    """
    _, index = mock_pinecone
    mock_emb = MagicMock()
    service = StorageService(index_name="test-index", embeddings=mock_emb)
    
    mock_store = MagicMock()
    mock_store.get_pinecone_index.return_value = index
    service._get_store = MagicMock(return_value=mock_store)
    
    index.query.return_value = {"matches": []}
    
    service.find_all_jobs_for_user("user_999")
    
    assert index.query.called
    _, kwargs = index.query.call_args
    
    assert kwargs["filter"]["user_id"]["$eq"] == "user_999"
    assert kwargs["namespace"] == service.NS_USER_DATA