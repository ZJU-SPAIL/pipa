from pipa.common.cmd import run_command
import pytest


def test_run_command_success():
    # Test a successful command execution
    command = "echo 'Hello, World!'"
    output = run_command(command)
    assert output == "Hello, World!"


def test_run_command_failure():
    # Test a failed command execution
    command = "invalid_command"
    with pytest.raises(Exception):
        run_command(command)


def test_run_command_with_log():
    # Test command execution with logging enabled
    command = "echo 'Hello, World!'"
    output = run_command(command, log=True)
    assert output == "Hello, World!"


def test_run_command_with_custom_cwd():
    # Test command execution with a custom working directory
    command = "pwd"
    cwd = "/tmp"
    output = run_command(command, cwd=cwd)
    assert output == "/tmp"


if __name__ == "__main__":
    pytest.main([__file__])
