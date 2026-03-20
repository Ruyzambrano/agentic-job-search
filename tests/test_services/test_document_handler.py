import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from pathlib import Path
from src.services.document_service import DocumentService
from src.schema import AnalysedJobMatchWithMeta, WorkSetting, SeniorityLevel

@pytest.fixture
def doc_service():
    """Provides an instance of DocumentService with a mocked output directory."""
    with patch("pathlib.Path.mkdir"):
        return DocumentService(output_path="mock_output")

@patch("src.services.document_service.pathlib.Path") 
@patch("src.services.document_service.MarkItDown")
def test_ingest_directory_success(mock_mid_class, mock_path_class, doc_service):
    mock_path_instance = mock_path_class.return_value
    mock_path_instance.exists.return_value = True 
    
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.name = "resume.pdf"
    mock_path_instance.iterdir.return_value = [mock_file]
    
    mock_mid_instance = mock_mid_class.return_value
    mock_result = MagicMock()
    mock_result.text_content = "Parsed Resume Content"
    mock_mid_instance.convert.return_value = mock_result

    doc_service.md = mock_mid_instance

    result = doc_service.ingest_directory("mock_path")

    assert "Parsed Resume Content" in result
    assert "--- SOURCE: resume.pdf ---" in result

def test_convert_to_text_logic(doc_service):
    """Tests the temporary file conversion flow."""
    mock_content = b"fake pdf content"
    mock_name = "test.pdf"
    
    with patch.object(doc_service.md, "convert") as mock_convert:
        mock_result = MagicMock()
        mock_result.text_content = "Converted Text"
        mock_convert.return_value = mock_result
        
        result = doc_service.convert_to_text(mock_content, mock_name)
        
        assert result == "Converted Text"
        mock_convert.assert_called_once()

def test_generate_research_report_success(doc_service, mock_analysed_job):
    

    mock_state = {
        "cv_data": MagicMock(full_name="Ruy Zambrano"),
        "writer_data": MagicMock(jobs=[mock_analysed_job]),
    }

    result = doc_service.generate_research_report(mock_state)

    assert isinstance(result, BytesIO)
    assert result.getvalue().startswith(b"PK")

def test_get_standard_filename(doc_service):
    filename = doc_service.get_standard_filename("Ruy Zambrano")
    assert "ruy_zambrano" in filename
    assert filename.endswith(".docx")