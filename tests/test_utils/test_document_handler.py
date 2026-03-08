import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from src.utils.document_handler import ingest_input_folder, save_findings_to_docx

# --- Tests for ingest_input_folder ---


@patch("src.utils.document_handler.glob")
@patch("src.utils.document_handler.MarkItDown")
def test_ingest_input_folder_success(mock_mid_class, mock_glob):
    # Setup mocks
    mock_glob.return_value = ["files/input/resume.pdf"]
    mock_mid_instance = mock_mid_class.return_value
    mock_result = MagicMock()
    mock_result.text_content = "Parsed Resume Content"
    mock_mid_instance.convert.return_value = mock_result

    result = ingest_input_folder("mock_path")

    assert "Parsed Resume Content" in result
    assert "--- CONTENT FROM resume.pdf ---" in result
    mock_mid_instance.convert.assert_called_once_with("files/input/resume.pdf")


@patch("src.utils.document_handler.glob")
@patch("src.utils.document_handler.log_message")
def test_ingest_input_folder_empty(mock_log, mock_glob):
    mock_glob.return_value = []
    result = ingest_input_folder("empty_path")
    assert result == ""


# --- Tests for save_findings_to_docx ---


def test_save_findings_to_docx_success():
    # Mocking the AgentState and internal data models
    mock_job = MagicMock()
    mock_job.title = "Data Engineer"
    mock_job.company = "Tech Corp"
    mock_job.job_url = "http://test.com"
    mock_job.salary_min = 50000
    mock_job.salary_max = 70000
    mock_job.job_summary = "A great role."
    mock_job.top_applicant_score = 95
    mock_job.top_applicant_reasoning = "Because you are awesome."
    mock_job.key_skills = ["Python", "AWS"]

    mock_state = {
        "cv_data": MagicMock(full_name="John Doe"),
        "writer_data": MagicMock(jobs=[mock_job]),
    }

    # We patch pathlib.Path.mkdir to avoid creating actual folders
    with patch("pathlib.Path.mkdir"):
        result = save_findings_to_docx(mock_state)

    # Assertions
    assert isinstance(result, BytesIO)
    assert result.getvalue().startswith(b"PK")  # Standard Word doc (ZIP) header


def test_save_findings_to_docx_error_handling():
    # Passing bad state to trigger exception
    result = save_findings_to_docx({})
    assert "Error saving docx" in result
