from src.utils.tools import extract_best_url

def test_extract_best_url(url_test_case):
    """Clean, modular test using the parameterized fixture"""
    job_data, expected_url = url_test_case
    assert extract_best_url(job_data) == expected_url