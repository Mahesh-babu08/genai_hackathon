import pytest
from services.groq_service import GroqService

def test_groq_service_initialization():
    """Test service initializes correctly"""
    # Requires env setup, so we might need to mock or ensure .env exists or use default
    # For now, simplistic check if key is mocked or present
    try:
        service = GroqService(api_key="test_key")
        assert service.api_key == "test_key"
        assert service.model is not None
    except Exception as e:
        # Should not fail with provided key
        pytest.fail(f"Initialization failed: {e}")

def test_review_code_empty_input():
    """Test error handling for empty code"""
    service = GroqService(api_key="test_key")
    with pytest.raises(ValueError, match="Code parameter cannot be empty"):
        service.review_code("")

def test_review_code_invalid_language():
    """Test handling of invalid language parameter"""
    service = GroqService(api_key="test_key")
    # Expected behavior depends on implementation. 
    # Current implementation raises ValueError for non-string, but logic says "must be non-empty string".
    with pytest.raises(ValueError):
        service.review_code("print('hello')", language="")

def test_parse_review_response_empty():
    """Test parsing empty review text"""
    service = GroqService(api_key="test_key")
    result = service.parse_review_response("")
    assert result["success"] == False
    assert "error" in result
