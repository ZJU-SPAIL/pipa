"""
Unit tests for the new two-phase sample command CLI.
"""

from unittest.mock import patch

from click.testing import CliRunner

from src.commands.sample import sample


class TestSampleCLIParameterValidation:
    @patch("src.commands.sample.run_sampling")
    def test_valid_default_invocation(self, mock_run):
        """Test a standard invocation using all defaults."""
        runner = CliRunner()
        result = runner.invoke(
            sample,
            ["--attach-to-pid", "12345", "--output", "out.pipa"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args.kwargs

        assert call_args["attach_pids"] == "12345"
        assert call_args["duration_stat"] == 60
        assert call_args["duration_record"] == 60
        assert call_args["run_stat_phase"] is True
        assert call_args["run_record_phase"] is True

    @patch("src.commands.sample.run_sampling")
    def test_disabling_phases(self, mock_run):
        """Test the --no-stat and --no-record flags."""
        runner = CliRunner()
        runner.invoke(
            sample,
            ["--attach-to-pid", "123", "--output", "out.pipa", "--no-record"],
            catch_exceptions=False,
        )
        assert mock_run.call_args.kwargs["run_record_phase"] is False

        runner.invoke(
            sample,
            ["--attach-to-pid", "123", "--output", "out.pipa", "--no-stat"],
            catch_exceptions=False,
        )
        assert mock_run.call_args.kwargs["run_stat_phase"] is False

    def test_disabling_both_phases_is_an_error(self):
        """Test that using both --no-stat and --no-record fails."""
        runner = CliRunner()
        result = runner.invoke(
            sample,
            ["--attach-to-pid", "123", "--output", "out.pipa", "--no-stat", "--no-record"],
        )
        assert result.exit_code != 0
        assert "cannot specify both" in result.output.lower()

    @patch("src.commands.sample.run_sampling")
    def test_expert_overrides_are_passed_correctly(self, mock_run):
        """Test that all optional override parameters are passed to the engine."""
        runner = CliRunner()
        result = runner.invoke(
            sample,
            [
                "--attach-to-pid",
                "123",
                "--output",
                "out.pipa",
                "--duration-stat",
                "10",
                "--perf-stat-interval",
                "500",
                "--perf-events",
                "my-event",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        call_args = mock_run.call_args.kwargs
        assert call_args["duration_stat"] == 10
        assert call_args["perf_stat_interval"] == 500
        assert call_args["perf_events_override"] == "my-event"
