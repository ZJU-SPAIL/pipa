"""
Unit tests for the simplified, attach-only sample command CLI.
"""

from unittest.mock import patch

from click.testing import CliRunner

from src.commands.sample import sample


class TestSampleCLIParameterValidation:
    """Test the parameter validation logic for the attach-only CLI."""

    @patch("src.commands.sample.run_sampling")
    def test_valid_attach_mode_invocation(self, mock_run):
        """Test a valid, standard invocation."""
        runner = CliRunner()
        result = runner.invoke(
            sample,
            [
                "--attach-to-pid",
                "12345",
                "--duration",
                "30",
                "--output",
                "out.pipa",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args.kwargs
        assert call_args["attach_pids"] == "12345"
        assert call_args["duration"] == 30
        assert call_args["collectors_config_path"] is None

    @patch("src.commands.sample.run_sampling")
    def test_with_custom_collectors_config(self, mock_run, tmp_path):
        """Test that --collectors-config path is passed correctly."""
        runner = CliRunner()
        config_file = tmp_path / "my_collectors.yaml"
        config_file.touch()

        result = runner.invoke(
            sample,
            [
                "--attach-to-pid",
                "12345",
                "--duration",
                "30",
                "--output",
                "out.pipa",
                "--collectors-config",
                str(config_file),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args.kwargs
        assert call_args["collectors_config_path"] == str(config_file)

    def test_missing_required_options(self):
        """Test that missing required options cause a failure."""
        runner = CliRunner()
        result1 = runner.invoke(sample, ["--duration", "30", "--output", "out.pipa"])
        assert result1.exit_code != 0
        assert "missing option" in result1.output.lower()

        result2 = runner.invoke(sample, ["--attach-to-pid", "12345", "--output", "out.pipa"])
        assert result2.exit_code != 0
        assert "missing option" in result2.output.lower()
