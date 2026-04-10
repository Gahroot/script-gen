import json
from unittest.mock import patch

import pytest

from app.generator import _format_intake, _parse_json, generate_scripts
from app.schemas import GeneratedScripts


class TestParseJson:
    """Tests for JSON parsing with markdown code block stripping."""

    def test_plain_json(self):
        result = _parse_json('{"hooks": ["a"], "meats": ["b"], "ctas": ["c"]}')
        assert result == {"hooks": ["a"], "meats": ["b"], "ctas": ["c"]}

    def test_json_with_code_block(self):
        raw = '```json\n{"key": "value"}\n```'
        result = _parse_json(raw)
        assert result == {"key": "value"}

    def test_json_with_plain_code_block(self):
        raw = '```\n{"key": "value"}\n```'
        result = _parse_json(raw)
        assert result == {"key": "value"}

    def test_json_with_whitespace(self):
        raw = '  \n  {"key": "value"}  \n  '
        result = _parse_json(raw)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("not json at all")


class TestFormatIntake:
    """Tests for intake data formatting."""

    def test_all_fields_populated(self, sample_intake):
        result = _format_intake(sample_intake)
        assert result["business_name"] == "Acme Roofing"
        assert (
            result["target_audience"]
            == "Homeowners aged 30-55 in the Greater Toronto Area"
        )
        assert "Toronto / Greater Toronto Area" == result["city_service_area"]
        assert "Pain Point 1:" in result["pain_points_solutions"]
        assert "Solution 1:" in result["pain_points_solutions"]
        assert result["offer"] == sample_intake.offer
        assert result["landing_page_url"] == "https://acmeroofing.ca/offer"

    def test_optional_fields_default_to_na(self):
        from app.schemas import IntakeData, PainPointSolution

        minimal = IntakeData(
            business_name="Test Biz",
            target_audience="Everyone",
            pain_points_solutions=[PainPointSolution(pain_point="p", solution="s")],
            offer="Free thing",
            top_stats=["one stat"],
            contact_name="Jane",
            contact_email="jane@test.com",
        )
        result = _format_intake(minimal)
        assert result["risk_reversal"] == "N/A"
        assert result["guarantees"] == "N/A"
        assert result["city_service_area"] == "N/A"
        assert result["landing_page_url"] == "N/A"


class TestGenerateScripts:
    """Tests for the generate_scripts function with mocked Gemini calls."""

    @patch("app.generator._call_gemini")
    def test_returns_generated_scripts(self, mock_call, sample_intake):
        mock_call.return_value = json.dumps(
            {
                "hooks": [f"hook {i}" for i in range(50)],
                "meats": ["meat 1", "meat 2", "meat 3"],
                "ctas": ["cta 1", "cta 2"],
            }
        )

        result = generate_scripts(sample_intake)

        assert isinstance(result, GeneratedScripts)
        assert len(result.hooks) == 50
        assert len(result.meats) == 3
        assert len(result.ctas) == 2
        mock_call.assert_called_once()

    @patch("app.generator._call_gemini")
    def test_invalid_json_raises(self, mock_call, sample_intake):
        mock_call.return_value = "not valid json"

        with pytest.raises(json.JSONDecodeError):
            generate_scripts(sample_intake)
