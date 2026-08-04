import json
from unittest.mock import MagicMock, patch

import pytest

from apps.operations.ai_providers import GeminiAIProvider


def test_gemini_provider_missing_api_key():
    provider = GeminiAIProvider(api_key="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable is missing"):
        provider._get_client()


@patch("google.genai.Client")
def test_gemini_provider_management_suggestions(mock_genai_client):
    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "summary": "Gemini management review",
            "suggestions": [
                {
                    "title": "Fix constraint",
                    "rationale": "High priority",
                    "function": "direction",
                    "evidence": [{"record_type": "metric", "record_id": "1"}],
                }
            ],
        }
    )
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    mock_client_instance.models.generate_content.return_value = mock_response

    provider = GeminiAIProvider(api_key="test_key")
    snapshot = {"risks": [], "metrics": [], "goals": []}
    res = provider.management_suggestions(snapshot=snapshot)

    assert res.provider == "gemini"
    assert res.output.summary == "Gemini management review"
    assert res.input_tokens == 100
    assert res.output_tokens == 50
