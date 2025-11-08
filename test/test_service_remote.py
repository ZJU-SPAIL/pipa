import pytest
from unittest.mock import patch, mock_open, MagicMock

from pipa.service.remote import RemoteProfiler, remote


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"',
)
@patch("os.path.exists")
def test_remote_profiler_init(mock_exists, mock_file):
    """Test initialization of the RemoteProfiler class"""
    mock_exists.return_value = True
    profiler = RemoteProfiler("dummy_config.yaml")

    # Verify that the configuration file is loaded correctly
    mock_file.assert_called_once_with("dummy_config.yaml", "r")

    # Verify that the basic properties are set correctly
    assert profiler.config["host"] == "test-host"
    assert profiler.config["username"] == "test-user"
    assert profiler.ssh_client is None
    assert profiler.profiling_mode == "sar"  # Default mode


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"',
)
@patch("os.path.exists")
def test_load_config_success(mock_exists, mock_file):
    """Test successful loading of the configuration file"""
    mock_exists.return_value = True

    profiler = RemoteProfiler("dummy_config.yaml")
    config = profiler.config

    assert config["host"] == "test-host"
    assert config["username"] == "test-user"


@patch("os.path.exists")
def test_load_config_file_not_found(mock_exists):
    """Test the case where the configuration file does not exist"""
    mock_exists.return_value = False

    with pytest.raises(FileNotFoundError):
        RemoteProfiler("non_existent_config.yaml")


@patch("builtins.open", new_callable=mock_open, read_data='host: "test-host"')
@patch("os.path.exists")
def test_load_config_missing_fields(mock_exists, mock_file):
    """Test the case where the configuration file is missing required fields"""
    mock_exists.return_value = True

    with pytest.raises(ValueError):
        RemoteProfiler("incomplete_config.yaml")


@patch("paramiko.SSHClient")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"\npassword: "test-pass"',
)
@patch("os.path.exists")
def test_connect_with_password(mock_exists, mock_file, mock_ssh):
    """Test connecting to the remote host using a password"""
    mock_exists.return_value = True
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client

    profiler = RemoteProfiler("dummy_config.yaml")
    result = profiler.connect()

    assert result is True
    mock_client.connect.assert_called_once_with(
        hostname="test-host", username="test-user", password="test-pass", port=22
    )


@patch("paramiko.SSHClient")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"\nkey_path: "/path/to/key.pem"',
)
@patch("os.path.exists")
def test_connect_with_key(mock_exists, mock_file, mock_ssh):
    """Test connecting to the remote host using a key"""
    mock_exists.side_effect = [True, True]  # Configuration file exists, key file exists
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client

    profiler = RemoteProfiler("dummy_config.yaml")
    result = profiler.connect()

    assert result is True
    mock_client.connect.assert_called_once_with(
        hostname="test-host",
        username="test-user",
        key_filename="/path/to/key.pem",
        port=22,
    )


@patch("paramiko.SSHClient")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"',
)
@patch("os.path.exists")
def test_connect_no_auth(mock_exists, mock_file, mock_ssh):
    """Test the case where no authentication method is provided"""
    mock_exists.return_value = True
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client

    profiler = RemoteProfiler("dummy_config.yaml")
    result = profiler.connect()

    assert result is False
    mock_client.connect.assert_not_called()


@patch("paramiko.SSHClient")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"\npassword: "test-pass"',
)
@patch("os.path.exists")
def test_check_remote_tools(mock_exists, mock_file, mock_ssh):
    """Test checking the availability of remote tools"""
    mock_exists.return_value = True

    # Mock SSH client and command execution
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client

    # Mock command execution results
    mock_stdout_sar = MagicMock()
    mock_stdout_sar.channel.recv_exit_status.return_value = 0

    mock_stdout_perf = MagicMock()
    mock_stdout_perf.channel.recv_exit_status.return_value = 0

    mock_client.exec_command.side_effect = [
        (None, mock_stdout_sar, None),  # sar command
        (None, mock_stdout_perf, None),  # perf command
    ]

    profiler = RemoteProfiler("dummy_config.yaml")
    profiler.ssh_client = mock_client

    result = profiler.check_remote_tools()

    assert result["connected"] is True
    assert result["sar"] is True
    assert result["perf"] is True
    assert mock_client.exec_command.call_count == 2


@patch("paramiko.SSHClient")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"\npassword: "test-pass"\ncleanup_remote: true',
)
@patch("os.path.exists")
def test_cleanup_remote(mock_exists, mock_file, mock_ssh):
    """Test the remote cleanup functionality"""
    mock_exists.return_value = True

    # Mock SSH client and command execution
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client

    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_client.exec_command.return_value = (None, mock_stdout, None)

    profiler = RemoteProfiler("dummy_config.yaml")
    profiler.ssh_client = mock_client

    result = profiler.cleanup_remote()

    assert result is True
    mock_client.exec_command.assert_called_once_with(
        f"rm -rf {profiler.remote_output_dir}"
    )


@patch("paramiko.SSHClient")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='host: "test-host"\nusername: "test-user"\npassword: "test-pass"',
)
@patch("os.path.exists")
def test_disconnect(mock_exists, mock_file, mock_ssh):
    """Test the disconnect functionality"""
    mock_exists.return_value = True

    # Mock SSH client
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client

    profiler = RemoteProfiler("dummy_config.yaml")
    profiler.ssh_client = mock_client

    profiler.disconnect()

    mock_client.close.assert_called_once()
    assert profiler.ssh_client is None


@patch("pipa.service.remote.RemoteProfiler")
@patch("questionary.text")
def test_remote_main_function(mock_text, mock_remote_profiler):
    """Test the main entry function of the remote service"""
    mock_text.return_value.ask.return_value = "dummy_config.yaml"

    # Mock RemoteProfiler instance
    mock_profiler = MagicMock()
    mock_remote_profiler.return_value = mock_profiler

    # Set the return values for each method
    mock_profiler.connect.return_value = True
    mock_profiler.check_remote_tools.return_value = {
        "connected": True,
        "sar": True,
        "perf": True,
    }
    mock_profiler.run_profiling.return_value = True

    # Execute the test
    result = remote(verbose=True)

    assert result is True
    mock_profiler.connect.assert_called_once()
    mock_profiler.check_remote_tools.assert_called_once()
    mock_profiler.run_profiling.assert_called_once()
    mock_profiler.cleanup_remote.assert_called_once()
    mock_profiler.disconnect.assert_called_once()


@patch("pipa.service.remote.RemoteProfiler")
def test_remote_with_provided_config(mock_remote_profiler):
    """Test the case where a configuration file path is provided"""
    # Mock RemoteProfiler instance
    mock_profiler = MagicMock()
    mock_remote_profiler.return_value = mock_profiler

    # Set the return values for each method
    mock_profiler.connect.return_value = True
    mock_profiler.check_remote_tools.return_value = {
        "connected": True,
        "sar": True,
        "perf": True,
    }
    mock_profiler.run_profiling.return_value = True

    # Execute the test
    result = remote(config_path="provided_config.yaml")

    assert result is True
    mock_remote_profiler.assert_called_once_with("provided_config.yaml")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
