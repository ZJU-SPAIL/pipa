import subprocess
from pipa.common.logger import logger


def run_command(command: str, cwd: str = "./", log: bool = False):
    """
    Run a command in the specified directory.

    Args:
        command (str): The command to be executed.
        cwd (str, optional): The current working directory where the command will be executed. Defaults to "./".
        log (bool, optional): Flag indicating whether to log the command output. Defaults to False.

    Returns:
        str: The output of the command.

    Raises:
        Exception: If the command execution fails.
    """
    result = subprocess.run(
        command,
        shell=True,
        close_fds=True,
        cwd=cwd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    suc = result.returncode == 0
    out = result.stdout.decode("UTF-8", "strict").strip()
    error = result.stderr.decode("UTF-8", "strict").strip()

    if not suc:
        logger.warning("'{}' return code = {}".format(command, result.returncode))
        raise Exception(error)
    else:
        if log:
            logger.info("{}: {}".format(command, out))
        else:
            logger.debug("{}: {}".format(command, out))
        return out
