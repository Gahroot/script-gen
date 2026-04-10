from unittest.mock import patch

from app.pipeline import run_pipeline
from app.schemas import GeneratedScripts


class TestRunPipeline:
    """Tests for the pipeline orchestration logic."""

    @patch("app.pipeline.check_compatibility")
    @patch("app.pipeline.verify_meats")
    @patch("app.pipeline.verify_hooks")
    @patch("app.pipeline.generate_scripts")
    def test_all_pass_first_loop(
        self,
        mock_generate,
        mock_verify_hooks,
        mock_verify_meats,
        mock_compat,
        sample_intake,
        sample_scripts,
    ):
        """When all verification passes on the first loop, no regeneration happens."""
        mock_generate.return_value = sample_scripts
        mock_verify_hooks.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_verify_meats.return_value = {
            "passed": True,
            "failed_meat_indices": [],
            "reasons": [],
        }
        mock_compat.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }

        result = run_pipeline(sample_intake)

        assert result == sample_scripts
        mock_generate.assert_called_once_with(sample_intake)
        mock_verify_hooks.assert_called_once()
        mock_verify_meats.assert_called_once()
        mock_compat.assert_called_once()

    @patch("app.pipeline.regenerate_hooks")
    @patch("app.pipeline.check_compatibility")
    @patch("app.pipeline.verify_meats")
    @patch("app.pipeline.verify_hooks")
    @patch("app.pipeline.generate_scripts")
    def test_hook_regen_then_pass(
        self,
        mock_generate,
        mock_verify_hooks,
        mock_verify_meats,
        mock_compat,
        mock_regen_hooks,
        sample_intake,
        sample_scripts,
    ):
        """When hooks fail once then pass, regeneration is called correctly."""
        mock_generate.return_value = sample_scripts

        # First loop: hook 0 and 2 fail
        mock_verify_hooks.side_effect = [
            {
                "passed": False,
                "failed_hook_indices": [0, 2],
                "reasons": ["bad", "duplicate"],
            },
            {"passed": True, "failed_hook_indices": [], "reasons": []},
        ]
        mock_verify_meats.return_value = {
            "passed": True,
            "failed_meat_indices": [],
            "reasons": [],
        }
        mock_compat.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_regen_hooks.return_value = ["Fixed hook zero", "Fixed hook two"]

        result = run_pipeline(sample_intake)

        assert result.hooks[0] == "Fixed hook zero"
        assert result.hooks[2] == "Fixed hook two"
        mock_regen_hooks.assert_called_once()

    @patch("app.pipeline.regenerate_meats")
    @patch("app.pipeline.check_compatibility")
    @patch("app.pipeline.verify_meats")
    @patch("app.pipeline.verify_hooks")
    @patch("app.pipeline.generate_scripts")
    def test_meat_regen_then_pass(
        self,
        mock_generate,
        mock_verify_hooks,
        mock_verify_meats,
        mock_compat,
        mock_regen_meats,
        sample_intake,
        sample_scripts,
    ):
        """When meats fail once then pass, regeneration is called correctly."""
        mock_generate.return_value = sample_scripts

        mock_verify_hooks.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_verify_meats.side_effect = [
            {"passed": False, "failed_meat_indices": [1], "reasons": ["too long"]},
            {"passed": True, "failed_meat_indices": [], "reasons": []},
        ]
        mock_compat.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_regen_meats.return_value = ["Tighter replacement meat two"]

        result = run_pipeline(sample_intake)

        assert result.meats[1] == "Tighter replacement meat two"
        mock_regen_meats.assert_called_once()

    @patch("app.pipeline.settings")
    @patch("app.pipeline.regenerate_hooks")
    @patch("app.pipeline.check_compatibility")
    @patch("app.pipeline.verify_meats")
    @patch("app.pipeline.verify_hooks")
    @patch("app.pipeline.generate_scripts")
    def test_max_loops_enforced(
        self,
        mock_generate,
        mock_verify_hooks,
        mock_verify_meats,
        mock_compat,
        mock_regen_hooks,
        mock_settings,
        sample_intake,
        sample_scripts,
    ):
        """Pipeline stops after max_regeneration_loops when failures keep shifting."""
        mock_settings.max_regeneration_loops = 3
        mock_generate.return_value = sample_scripts

        # Vary the failing index each loop so oscillation detection doesn't fire
        mock_verify_hooks.side_effect = [
            {"passed": False, "failed_hook_indices": [0], "reasons": ["bad 0"]},
            {"passed": False, "failed_hook_indices": [1], "reasons": ["bad 1"]},
            {"passed": False, "failed_hook_indices": [2], "reasons": ["bad 2"]},
        ]
        mock_verify_meats.return_value = {
            "passed": True,
            "failed_meat_indices": [],
            "reasons": [],
        }
        mock_compat.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_regen_hooks.return_value = ["attempted fix"]

        result = run_pipeline(sample_intake)

        # Should have looped exactly 3 times
        assert mock_verify_hooks.call_count == 3
        assert mock_regen_hooks.call_count == 3
        # Still returns best-effort result
        assert isinstance(result, GeneratedScripts)

    @patch("app.pipeline.settings")
    @patch("app.pipeline.regenerate_hooks")
    @patch("app.pipeline.check_compatibility")
    @patch("app.pipeline.verify_meats")
    @patch("app.pipeline.verify_hooks")
    @patch("app.pipeline.generate_scripts")
    def test_oscillation_detection_breaks_early(
        self,
        mock_generate,
        mock_verify_hooks,
        mock_verify_meats,
        mock_compat,
        mock_regen_hooks,
        mock_settings,
        sample_intake,
        sample_scripts,
    ):
        """When the same indices fail twice in a row, pipeline exits early."""
        mock_settings.max_regeneration_loops = 5
        mock_generate.return_value = sample_scripts

        # Same failing index every loop — should trigger oscillation guard
        mock_verify_hooks.return_value = {
            "passed": False,
            "failed_hook_indices": [0],
            "reasons": ["stuck"],
        }
        mock_verify_meats.return_value = {
            "passed": True,
            "failed_meat_indices": [],
            "reasons": [],
        }
        mock_compat.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_regen_hooks.return_value = ["attempted fix"]

        result = run_pipeline(sample_intake)

        # Loop 1: record signature. Loop 2: detect match, break.
        assert mock_verify_hooks.call_count == 2
        assert isinstance(result, GeneratedScripts)

    @patch("app.pipeline.regenerate_hooks")
    @patch("app.pipeline.check_compatibility")
    @patch("app.pipeline.verify_meats")
    @patch("app.pipeline.verify_hooks")
    @patch("app.pipeline.generate_scripts")
    def test_compatibility_failure_regenerates_hooks(
        self,
        mock_generate,
        mock_verify_hooks,
        mock_verify_meats,
        mock_compat,
        mock_regen_hooks,
        sample_intake,
        sample_scripts,
    ):
        """Compatibility failures trigger hook regeneration."""
        mock_generate.return_value = sample_scripts
        mock_verify_hooks.return_value = {
            "passed": True,
            "failed_hook_indices": [],
            "reasons": [],
        }
        mock_verify_meats.return_value = {
            "passed": True,
            "failed_meat_indices": [],
            "reasons": [],
        }

        mock_compat.side_effect = [
            {
                "passed": False,
                "failed_hook_indices": [5],
                "reasons": ["contradicts meat"],
            },
            {"passed": True, "failed_hook_indices": [], "reasons": []},
        ]
        mock_regen_hooks.return_value = ["Compatible replacement hook"]

        result = run_pipeline(sample_intake)

        assert result.hooks[5] == "Compatible replacement hook"
