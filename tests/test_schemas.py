import pytest
from pydantic import ValidationError

from app.schemas import (
    GeneratedScripts,
    IntakeData,
    PainPointSolution,
    PipelineResponse,
)


class TestIntakeData:
    """Tests for intake data validation."""

    def test_valid_minimal(self):
        data = IntakeData(
            business_name="Test",
            target_audience="Everyone",
            pain_points_solutions=[PainPointSolution(pain_point="p", solution="s")],
            offer="Free thing",
            top_stats=["stat one"],
            contact_name="Jane",
            contact_email="jane@example.com",
        )
        assert data.business_name == "Test"
        assert data.risk_reversal == ""
        assert data.contact_phone == ""

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            IntakeData(
                business_name="Test",
                target_audience="Everyone",
                pain_points_solutions=[PainPointSolution(pain_point="p", solution="s")],
                offer="Free thing",
                top_stats=["stat"],
                contact_name="Jane",
                contact_email="not-an-email",
            )

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            IntakeData(
                business_name="Test",
                # missing target_audience, pain_points_solutions, etc.
                offer="Free thing",
                top_stats=["stat"],
                contact_name="Jane",
                contact_email="jane@example.com",
            )


class TestGeneratedScripts:
    def test_valid(self):
        scripts = GeneratedScripts(hooks=["h"], meats=["m"], ctas=["c"])
        assert scripts.hooks == ["h"]


class TestPipelineResponse:
    def test_valid(self):
        resp = PipelineResponse(
            success=True,
            markdown="# Test",
            contact_name="Jane",
            contact_email="jane@example.com",
            contact_phone="",
            business_name="Test",
        )
        assert resp.success is True
