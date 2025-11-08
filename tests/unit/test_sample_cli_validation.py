"""
Unit tests for the sample command CLI parameter validation.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from src.commands.sample import sample


class TestSampleCLIParameterValidation:
    """Test the parameter validation logic in the CLI layer."""

    def test_mutually_exclusive_config_and_intensity(self):
        """Test that --config and --intensity cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.yaml").touch()

            result = runner.invoke(
                sample,
                [
                    "--config",
                    "test.yaml",
                    "--intensity",
                    "8",
                    "--workload",
                    "stress_cpu",
                    "--output",
                    "out.pipa",
                ],
            )
            assert result.exit_code != 0
            assert "mutually exclusive" in result.output.lower()

    def test_mutually_exclusive_config_and_attach(self):
        """Test that --config and --attach-to-pid cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.yaml").touch()

            result = runner.invoke(
                sample,
                [
                    "--config",
                    "test.yaml",
                    "--attach-to-pid",
                    "12345",
                    "--duration",
                    "30",
                    "--output",
                    "out.pipa",
                ],
            )
            assert result.exit_code != 0
            assert "mutually exclusive" in result.output.lower()

    def test_mutually_exclusive_intensity_and_attach(self):
        """Test that --intensity and --attach-to-pid cannot be used together."""
        runner = CliRunner()
        result = runner.invoke(
            sample,
            [
                "--intensity",
                "8",
                "--workload",
                "stress_cpu",
                "--attach-to-pid",
                "12345",
                "--duration",
                "30",
                "--output",
                "out.pipa",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_no_mode_specified(self):
        """Test that at least one mode must be specified."""
        runner = CliRunner()
        result = runner.invoke(sample, ["--output", "out.pipa"])
        assert result.exit_code != 0
        assert "must specify a mode" in result.output.lower()

    def test_direct_mode_missing_workload(self):
        """Test that --workload is required when using --intensity."""
        runner = CliRunner()
        result = runner.invoke(sample, ["--intensity", "8", "--output", "out.pipa"])
        assert result.exit_code != 0
        assert "--workload is required" in result.output.lower()

    def test_attach_mode_missing_duration(self):
        """Test that --duration is required when using --attach-to-pid."""
        runner = CliRunner()
        result = runner.invoke(sample, ["--attach-to-pid", "12345", "--output", "out.pipa"])
        assert result.exit_code != 0
        assert "--duration is required" in result.output.lower()

    def test_invalid_intensity_format(self):
        """Test that --intensity must be valid integers."""
        runner = CliRunner()
        result = runner.invoke(
            sample,
            [
                "--intensity",
                "abc",
                "--workload",
                "stress_cpu",
                "--output",
                "out.pipa",
            ],
        )
        assert result.exit_code != 0
        assert "must be a number" in result.output.lower()

    def test_valid_calibrated_mode(self):
        """Test valid calibrated mode invocation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.yaml").write_text("calibrated_parameters: {}")

            with patch("src.commands.sample.run_sampling") as mock_run:
                result = runner.invoke(sample, ["--config", "test.yaml", "--output", "out.pipa"])
                assert result.exit_code == 0
                assert mock_run.called
                assert "completed successfully" in result.output.lower()

    def test_valid_direct_mode(self):
        """Test valid direct mode invocation."""
        runner = CliRunner()
        with patch("src.commands.sample.run_sampling") as mock_run:
            result = runner.invoke(
                sample,
                [
                    "--workload",
                    "stress_cpu",
                    "--intensity",
                    "8,16",
                    "--output",
                    "out.pipa",
                ],
            )
            assert result.exit_code == 0
            assert mock_run.called
            # Verify intensities were parsed correctly
            call_args = mock_run.call_args
            assert call_args[0][3] == [8, 16]  # intensities parameter

    def test_valid_attach_mode(self):
        """Test valid attach mode invocation."""
        runner = CliRunner()
        with patch("src.commands.sample.run_sampling") as mock_run:
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
            )
            assert result.exit_code == 0
            assert mock_run.called
            call_args = mock_run.call_args
            assert call_args[0][4] == "12345"  # attach_pids parameter
            assert call_args[0][5] == 30  # duration parameter

    def test_no_static_info_flag(self):
        """Test that --no-static-info flag is passed correctly."""
        runner = CliRunner()
        with patch("src.commands.sample.run_sampling") as mock_run:
            result = runner.invoke(
                sample,
                [
                    "--workload",
                    "stress_cpu",
                    "--intensity",
                    "8",
                    "--no-static-info",
                    "--output",
                    "out.pipa",
                ],
            )
            assert result.exit_code == 0
            assert mock_run.called
            call_args = mock_run.call_args
            assert call_args[0][6] is True  # no_static_info parameter
