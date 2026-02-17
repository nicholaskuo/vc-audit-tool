import os
import pytest
from backend.services.llm_service import LLMService

# Skip entire directory if no API key is available
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping live LLM eval tests",
)


@pytest.fixture
def llm_service():
    """Provide a real LLMService instance backed by the live OpenAI API."""
    return LLMService()
