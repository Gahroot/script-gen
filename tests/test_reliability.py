from unittest.mock import patch

import pytest

from app.reliability import (
    EmailDeliveryError,
    MarkdownEmptyError,
    ScriptsIncompleteError,
    _assert_scripts_complete,
    assert_markdown_nonempty,
    generate_scripts_reliably,
    send_email_reliably,
)
from app.schemas import GeneratedScripts


class TestAssertScriptsComplete:
    def test_accepts_correctly_shaped(self, sample_scripts):
        _assert_scripts_complete(sample_scripts)

    def test_rejects_wrong_hook_count(self, sample_scripts):
        bad = sample_scripts.model_copy(update={"hooks": sample_scripts.hooks[:49]})
        with pytest.raises(ScriptsIncompleteError, match="hooks=49"):
            _assert_scripts_complete(bad)

    def test_rejects_wrong_meat_count(self, sample_scripts):
        bad = sample_scripts.model_copy(update={"meats": sample_scripts.meats[:2]})
        with pytest.raises(ScriptsIncompleteError, match="meats=2"):
            _assert_scripts_complete(bad)

    def test_rejects_wrong_cta_count(self, sample_scripts):
        bad = sample_scripts.model_copy(update={"ctas": sample_scripts.ctas[:1]})
        with pytest.raises(ScriptsIncompleteError, match="ctas=1"):
            _assert_scripts_complete(bad)

    def test_rejects_empty_hook_string(self, sample_scripts):
        hooks = list(sample_scripts.hooks)
        hooks[7] = "   "
        bad = sample_scripts.model_copy(update={"hooks": hooks})
        with pytest.raises(ScriptsIncompleteError, match=r"hook\[7\] empty"):
            _assert_scripts_complete(bad)


class TestAssertMarkdownNonempty:
    def test_accepts_long_markdown(self):
        assert_markdown_nonempty("x" * 501)

    def test_rejects_empty(self):
        with pytest.raises(MarkdownEmptyError):
            assert_markdown_nonempty("")

    def test_rejects_whitespace(self):
        with pytest.raises(MarkdownEmptyError):
            assert_markdown_nonempty("   \n  \t  ")

    def test_rejects_too_short(self):
        with pytest.raises(MarkdownEmptyError):
            assert_markdown_nonempty("too short")


class TestGenerateScriptsReliably:
    @patch("app.reliability.run_pipeline")
    def test_succeeds_first_try(self, mock_pipeline, sample_intake, sample_scripts):
        mock_pipeline.return_value = sample_scripts
        result = generate_scripts_reliably(sample_intake, "job-1")
        assert result is sample_scripts
        assert mock_pipeline.call_count == 1

    @patch("app.reliability.wait_exponential")
    @patch("app.reliability.run_pipeline")
    def test_retries_on_transient_failure(
        self, mock_pipeline, mock_wait, sample_intake, sample_scripts
    ):
        # Skip sleeping between retries
        mock_wait.return_value = lambda _: 0
        mock_pipeline.side_effect = [RuntimeError("transient"), sample_scripts]
        result = generate_scripts_reliably(sample_intake, "job-2")
        assert result is sample_scripts
        assert mock_pipeline.call_count == 2

    @patch("app.reliability.run_pipeline")
    def test_rejects_incomplete_scripts(self, mock_pipeline, sample_intake):
        short = GeneratedScripts(hooks=["only one"], meats=[], ctas=[])
        mock_pipeline.return_value = short
        # 2 attempts, both return incomplete → raises on last
        with pytest.raises(ScriptsIncompleteError):
            generate_scripts_reliably(sample_intake, "job-3")
        assert mock_pipeline.call_count == 2


class TestSendEmailReliably:
    @patch("app.reliability.email_delivery.is_enabled", return_value=False)
    def test_returns_false_when_disabled(self, _is_enabled, sample_intake):
        assert send_email_reliably(sample_intake, "markdown", "job-1") is False

    @patch("app.reliability.email_delivery.is_enabled", return_value=True)
    @patch("app.reliability.email_delivery.send_scripts")
    def test_succeeds_first_try(self, mock_send, _is_enabled, sample_intake):
        mock_send.return_value = True
        assert send_email_reliably(sample_intake, "markdown", "job-1") is True
        assert mock_send.call_count == 1

    @patch("app.reliability.wait_exponential")
    @patch("app.reliability.email_delivery.is_enabled", return_value=True)
    @patch("app.reliability.email_delivery.send_scripts")
    def test_retries_on_transient_failure(
        self, mock_send, _is_enabled, mock_wait, sample_intake
    ):
        mock_wait.return_value = lambda _: 0
        mock_send.side_effect = [RuntimeError("resend down"), True]
        assert send_email_reliably(sample_intake, "markdown", "job-1") is True
        assert mock_send.call_count == 2

    @patch("app.reliability.wait_exponential")
    @patch("app.reliability.email_delivery.is_enabled", return_value=True)
    @patch("app.reliability.email_delivery.send_scripts")
    def test_raises_after_all_attempts(
        self, mock_send, _is_enabled, mock_wait, sample_intake
    ):
        mock_wait.return_value = lambda _: 0
        mock_send.side_effect = RuntimeError("persistent")
        with pytest.raises(EmailDeliveryError, match="3 attempts"):
            send_email_reliably(sample_intake, "markdown", "job-1")
        assert mock_send.call_count == 3
