import os
import yaml
import time
import logging
import paramiko
from pathlib import Path
from typing import Dict
from pipa.common.logger import logger


class RemoteProfiler:
    """
    RemoteProfiler provides functionality to profile applications on a remote machine via SSH.
    """

    def __init__(self, config_path: str):
        """
        Initialize the RemoteProfiler with configuration from a file.

        Args:
            config_path (str): Path to the YAML configuration file.
        """
        self.config = self._load_config(config_path)
        self.ssh_client = None
        self.profiling_mode = self.config.get("profiling_mode", "sar")
        self.output_dir = Path(
            self.config.get("local_output_dir", "./remote_profile_output")
        )
        self.remote_output_dir = self.config.get(
            "remote_output_dir", "/tmp/pipa_remote_profile"
        )
        self.workload_command = self.config.get("workload_command", "")

        # Create local output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from YAML file.

        Args:
            config_path (str): Path to the YAML configuration file.

        Returns:
            dict: Configuration dictionary.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            yaml.YAMLError: If config file isn't valid YAML.
        """
        if not os.path.exists(config_path):
            logger.error(f"Configuration file {config_path} not found.")
            raise FileNotFoundError(f"Configuration file {config_path} not found.")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Validate required configuration
            required_fields = ["host", "username"]
            missing_fields = [field for field in required_fields if field not in config]

            if missing_fields:
                error_msg = f"Missing required configuration fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            return config
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise

    def connect(self) -> bool:
        """
        Connect to the remote machine via SSH.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            host = self.config["host"]
            username = self.config["username"]
            password = self.config.get("password")
            key_path = self.config.get("key_path")
            port = self.config.get("port", 22)

            if key_path and os.path.exists(key_path):
                logger.info(f"Connecting to {host} using SSH key authentication")
                self.ssh_client.connect(
                    hostname=host, username=username, key_filename=key_path, port=port
                )
            elif password:
                logger.info(f"Connecting to {host} using password authentication")
                self.ssh_client.connect(
                    hostname=host, username=username, password=password, port=port
                )
            else:
                logger.error(
                    "No authentication method provided. Need either password or key_path."
                )
                return False

            logger.info(f"Successfully connected to {host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to remote host: {e}")
            return False

    def check_remote_tools(self) -> Dict[str, bool]:
        """
        Check if required profiling tools are available on the remote machine.

        Returns:
            Dict[str, bool]: Dictionary of tool availability.
        """
        if not self.ssh_client:
            logger.error("Not connected to remote host. Call connect() first.")
            return {"connected": False}

        tools_availability = {"connected": True, "sar": False, "perf": False}

        # Check for sar
        _, stdout, _ = self.ssh_client.exec_command("which sar")
        tools_availability["sar"] = stdout.read().decode().strip() != ""

        # Check for perf
        _, stdout, _ = self.ssh_client.exec_command("which perf")
        tools_availability["perf"] = stdout.read().decode().strip() != ""

        logger.info(f"Remote tools availability: {tools_availability}")
        return tools_availability

    def setup_remote_environment(self) -> bool:
        """
        Setup the remote environment for profiling.

        Returns:
            bool: True if setup successful, False otherwise.
        """
        if not self.ssh_client:
            logger.error("Not connected to remote host. Call connect() first.")
            return False

        # Create remote output directory if it doesn't exist
        _, stdout, stderr = self.ssh_client.exec_command(
            f"mkdir -p {self.remote_output_dir}"
        )
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            logger.error(
                f"Failed to create remote output directory: {stderr.read().decode()}"
            )
            return False

        logger.info(
            f"Remote environment setup complete. Output directory: {self.remote_output_dir}"
        )
        return True

    def run_profiling(self) -> bool:
        """
        Run the selected profiling mode on the remote machine.

        Returns:
            bool: True if profiling successful, False otherwise.
        """
        if not self.ssh_client:
            logger.error("Not connected to remote host. Call connect() first.")
            return False

        # Check if the remote environment is ready
        if not self.setup_remote_environment():
            return False

        # Generate a timestamp for this profiling run
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Run the appropriate profiling command based on the selected mode
        if self.profiling_mode == "sar":
            return self._run_sar_profiling(timestamp)
        elif self.profiling_mode == "perf_stat":
            return self._run_perf_stat_profiling(timestamp)
        elif self.profiling_mode == "perf_record":
            return self._run_perf_record_profiling(timestamp)
        else:
            logger.error(f"Unsupported profiling mode: {self.profiling_mode}")
            return False

    def _run_sar_profiling(self, timestamp: str) -> bool:
        """
        Run system-wide statistics profiling with sar.

        Args:
            timestamp (str): Timestamp string for output files.

        Returns:
            bool: True if profiling successful, False otherwise.
        """
        interval = self.config.get("sar_interval", 1)
        count = self.config.get("sar_count", "all")
        output_file = f"{self.remote_output_dir}/sar-{timestamp}.log"

        # Construct the sar command
        if count == "all":
            # Run sar in background and capture all metrics until workload finishes
            sar_cmd = (
                f"sar -A {interval} -o {output_file} > /dev/null 2>&1 & SAR_PID=$!;"
            )
            workload_cmd = f"{self.workload_command}; WORKLOAD_EXIT=$?;"
            kill_cmd = "kill -TERM $SAR_PID;"
            final_cmd = f"{sar_cmd} {workload_cmd} {kill_cmd} exit $WORKLOAD_EXIT"
        else:
            # Run sar for a specific number of samples
            sar_cmd = f"sar -A {interval} {count} -o {output_file} > {output_file}.txt 2>&1 & SAR_PID=$!;"
            workload_cmd = f"{self.workload_command}; WORKLOAD_EXIT=$?;"
            wait_cmd = "wait $SAR_PID;"
            final_cmd = f"{sar_cmd} {workload_cmd} {wait_cmd} exit $WORKLOAD_EXIT"

        logger.info(f"Running sar profiling with command: {final_cmd}")

        # Execute the command
        _, stdout, stderr = self.ssh_client.exec_command(final_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            logger.error(
                f"sar profiling failed with exit code {exit_code}: {stderr.read().decode()}"
            )
            return False

        # Transfer the results back
        return self._transfer_results(f"{output_file}*", timestamp)

    def _run_perf_stat_profiling(self, timestamp: str) -> bool:
        """
        Run aggregate counter profiling with perf stat.

        Args:
            timestamp (str): Timestamp string for output files.

        Returns:
            bool: True if profiling successful, False otherwise.
        """
        output_file = f"{self.remote_output_dir}/perf-stat-{timestamp}.log"
        events = self.config.get("perf_stat_events", "cycles,instructions")

        # Construct the perf stat command
        perf_cmd = f"perf stat -e {events} -o {output_file} {self.workload_command}"

        logger.info(f"Running perf stat profiling with command: {perf_cmd}")

        # Execute the command
        _, stdout, stderr = self.ssh_client.exec_command(perf_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            logger.error(
                f"perf stat profiling failed with exit code {exit_code}: {stderr.read().decode()}"
            )
            return False

        # Transfer the results back
        return self._transfer_results(output_file, timestamp)

    def _run_perf_record_profiling(self, timestamp: str) -> bool:
        """
        Run detailed sampling profiling with perf record.

        Args:
            timestamp (str): Timestamp string for output files.

        Returns:
            bool: True if profiling successful, False otherwise.
        """
        output_file = f"{self.remote_output_dir}/perf-{timestamp}.data"
        events = self.config.get("perf_record_events", "{cycles,instructions}:S")
        freq = self.config.get("perf_record_freq", 999)
        callgraph = self.config.get("perf_record_callgraph", False)

        # Construct the perf record command
        call_graph_opt = "-g" if callgraph else ""
        perf_cmd = f"perf record -e {events} -F {freq} {call_graph_opt} -o {output_file} {self.workload_command}"

        logger.info(f"Running perf record profiling with command: {perf_cmd}")

        # Execute the command
        _, stdout, stderr = self.ssh_client.exec_command(perf_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            logger.error(
                f"perf record profiling failed with exit code {exit_code}: {stderr.read().decode()}"
            )
            return False

        # Transfer the results back
        return self._transfer_results(output_file, timestamp)

    def _transfer_results(self, remote_pattern: str, timestamp: str) -> bool:
        """
        Transfer profiling results from remote to local machine.

        Args:
            remote_pattern (str): Pattern matching remote files to transfer.
            timestamp (str): Timestamp string for organizing output files.

        Returns:
            bool: True if transfer successful, False otherwise.
        """
        try:
            # Create a timestamped directory for this run's results
            local_dir = os.path.join(self.output_dir, timestamp)
            os.makedirs(local_dir, exist_ok=True)

            # Open an SFTP session
            sftp = self.ssh_client.open_sftp()

            # List files matching the pattern
            _, stdout, _ = self.ssh_client.exec_command(
                f"ls -1 {remote_pattern} 2>/dev/null || echo ''"
            )
            files = stdout.read().decode().strip().split("\n")
            files = [f for f in files if f]  # Filter out empty strings

            if not files:
                logger.warning(f"No files found matching pattern {remote_pattern}")
                return False

            # Transfer each file
            for remote_file in files:
                filename = os.path.basename(remote_file)
                local_file = os.path.join(local_dir, filename)
                logger.info(f"Transferring {remote_file} to {local_file}")
                sftp.get(remote_file, local_file)

            sftp.close()
            logger.info(f"Successfully transferred profiling results to {local_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to transfer profiling results: {e}")
            return False

    def disconnect(self):
        """
        Disconnect from the remote machine.
        """
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
            logger.info("Disconnected from remote host")

    def cleanup_remote(self) -> bool:
        """
        Clean up temporary files on the remote machine.

        Returns:
            bool: True if cleanup successful, False otherwise.
        """
        if not self.ssh_client:
            logger.error("Not connected to remote host. Call connect() first.")
            return False

        # Remove the remote output directory if configured to do so
        if self.config.get("cleanup_remote", True):
            _, stdout, stderr = self.ssh_client.exec_command(
                f"rm -rf {self.remote_output_dir}"
            )
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                logger.error(
                    f"Failed to clean up remote files: {stderr.read().decode()}"
                )
                return False

            logger.info("Remote cleanup completed successfully")
        return True


def remote(config_path: str = None, verbose: bool = False):
    """
    Main entry point for the remote profiling service.

    Args:
        config_path (str, optional): Path to the configuration file. Defaults to None.
        verbose (bool, optional): Enable verbose logging. Defaults to False.

    Returns:
        bool: True if profiling successful, False otherwise.
    """
    import questionary
    from rich import print

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # If config_path is not provided, prompt the user
    if config_path is None:
        config_path = questionary.text(
            "Path to remote profiling configuration file:"
        ).ask()

        if not config_path:
            logger.error("No configuration file provided. Exiting.")
            return False

    try:
        # Initialize the remote profiler
        profiler = RemoteProfiler(config_path)

        # Connect to the remote host
        if not profiler.connect():
            logger.error(
                "Failed to connect to remote host. Check your SSH credentials."
            )
            return False

        # Check for available tools
        tools = profiler.check_remote_tools()
        if not tools["connected"]:
            logger.error("Not connected to remote host.")
            return False

        if profiler.profiling_mode == "sar" and not tools["sar"]:
            logger.error(
                "'sar' tool not found on remote host but sar profiling mode is selected."
            )
            return False

        if (
            profiler.profiling_mode in ["perf_stat", "perf_record"]
            and not tools["perf"]
        ):
            logger.error(
                "'perf' tool not found on remote host but perf profiling mode is selected."
            )
            return False

        print(f"[green]✓[/green] Remote profiling tools availability: {tools}")

        # Run the profiling
        success = profiler.run_profiling()

        if success:
            print("[green]✓[/green] Remote profiling completed successfully.")
        else:
            print("[red]✗[/red] Remote profiling failed.")

        # Clean up
        profiler.cleanup_remote()
        profiler.disconnect()

        return success

    except Exception as e:
        logger.error(f"Error during remote profiling: {e}")
        return False
