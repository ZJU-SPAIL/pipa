import questionary
from rich import print
import os
from pipa.service.pipashu import PIPAShuData
from pipa.common.logger import logger
from pipa.service.pipad.pipad_client import PIPADClient
import pipa.service.pipad.pipad_pb2 as pipadlib
import getpass
import yaml


def check_workload(workload):
    """
    Check if the workload name is valid.

    Args:
        workload (str): The name of the workload.

    Returns:
        None

    Raises:
        SystemExit: If the workload name is empty.

    """
    if workload == "":
        print("Please input a valid workload name.")
        exit(1)


def check_transaction(transaction):
    """
    Check if the given transaction is a valid number.

    Args:
        transaction (str): The transaction to be checked.

    Returns:
        int: The transaction converted to an integer if it is a valid number.

    Raises:
        ValueError: If the transaction is not a valid number.

    """
    if not transaction.isdigit():
        print("Please input a valid number.")
        exit(1)
    try:
        transaction = int(transaction)
    except ValueError:
        print("Please input a valid number.")
        raise ValueError
    return transaction


def check_path(data_location):
    """
    Check if the specified data location is valid.

    Args:
        data_location (str): The path to the data location.

    Raises:
        SystemExit: If the data location is empty or does not exist.

    """
    if data_location == "":
        print("Please input a valid data location.")
        exit(1)
    elif not os.path.exists(data_location):
        print("The folder does not exist.")
        exit(1)


def check_cores(cores):
    """
    Check if the given cores are valid.

    Args:
        cores (str): A string representing the core numbers separated by commas.

    Returns:
        list: A list of integers representing the valid core numbers.

    Raises:
        ValueError: If the input is not a valid core number.

    """
    if cores == "":
        print("Please input a valid core number.")
        exit(1)
    try:
        cores = cores.split(",")
        cores = list(map(int, cores))
    except ValueError:
        print("Please input a valid core number.")
        raise ValueError
    except Exception as e:
        raise e

    return cores


def quest():
    """
    Collects information from the user and returns a dictionary containing the collected data.

    Returns:
        dict: A dictionary containing the collected information with the following keys:
            - 'workload': The name of the workload.
            - 'transaction': The number of transactions.
            - 'data_location': The location of the data collected by PIPAShu.
            - 'cores': The threads used in the workload.
            - 'dev': The used disk device name.
            - 'hw_info': The hardware configuration (sockets*cores*SMT).
            - 'sw_info': The software configuration.
            - 'platform': The platform.
            - 'comment': Any comments.
            - 'pipad_addr': The PIPAD server address.
            - 'pipad_port': The PIPAD server port.
    """
    workload = questionary.text("What's the name of workload?").ask()
    check_workload(workload)

    transaction = questionary.text("What's the number of transaction?").ask()
    transaction = check_transaction(transaction)

    data_location = questionary.text("Where's the data collected by PIPAShu?").ask()
    check_path(data_location)

    cores = questionary.text(
        "What are the threads used in the workload? Split by ,", default="0,1,2,3"
    ).ask()
    cores = check_cores(cores)

    dev = questionary.text("What's the used disk device name?").ask()
    if dev == "":
        dev = None

    hw_info = questionary.text(
        "What's the hardware configuration (sockets*cores*SMT)?", default="1*1*1"
    ).ask()

    sw_info = questionary.text("What's the software configuration?").ask()

    platform = questionary.text("What's the platform?", default="IceLake 8383C").ask()

    cpu_frequency_mhz = None
    if "huawei" in platform.lower():
        cpu_frequency_mhz = questionary.text(
            "What's the CPU frequency in MHz?", default="2600"
        ).ask()
        cpu_frequency_mhz = int(cpu_frequency_mhz)

    comment = questionary.text("Any comments?").ask()

    pipad_server = questionary.text("What's the PIPAD server address?").ask()

    pipad_port = questionary.text("What's the PIPAD server port?").ask()

    return {
        "workload": workload,
        "transaction": transaction,
        "data_location": data_location,
        "cores": cores,
        "dev": dev,
        "hw_info": hw_info,
        "sw_info": sw_info,
        "platform": platform,
        "cpu_frequency_mhz": cpu_frequency_mhz,
        "comment": comment,
        "pipad_addr": pipad_server,
        "pipad_port": pipad_port,
    }


def build_with_config_path(config_path: str):
    """
    Build with a configuration file path.

    Args:
        config_path (str): The path to the configuration file.

    Returns:
        The result of the build process.
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return build(config)


def build(config: dict):
    """
    Builds the data for upload based on the given configuration.

    Args:
        config (dict): A dictionary containing the configuration parameters.

    Returns:
        dict: A dictionary containing the built data for upload.
            - workload: The name of the workload.
            - transaction: The number of transactions.
            - data_location: The location of the data collected by PIPAShu.
            - cores: The hardware cores used in the workload.
            - dev: The used disk device name.
            - hw_info: The hardware configuration.
            - sw_info: The software configuration.
            - platform: The platform used.
            - comment: Any comments.
            - pipad_addr: The PIPAD server address. Optional.
            - pipad_port: The PIPAD server port. Optional.
            - perf_stat_path: The path to the perf-stat.csv file. Only required if data_location is not provided.
            - sar_path: The path to the sar.txt file. Only required if data_location is not provided.
            - perf_script_path: The path to the perf.script file. Only required if data_location is not provided.


    Raises:
        Exception: If the required files are missing.

    """
    data_dir = config.get("data_location", None)
    if data_dir:
        perf_stat_path = os.path.join(data_dir, "perf-stat.csv")
        sar_path = os.path.join(data_dir, "sar.txt")
        perf_script_path = os.path.join(data_dir, "perf.script")
    else:
        perf_stat_path = config.get("perf_stat_path", None)
        sar_path = config.get("sar_path", None)
        perf_script_path = config.get("perf_script_path", None)

        config["data_location"] = perf_stat_path.rsplit("/", 1)[0]

    if not os.path.exists(perf_stat_path):
        logger.error("perf-stat.csv does not exist.")
        raise Exception("perf-stat.csv does not exist.")
    elif not os.path.exists(sar_path):
        logger.error("sar.txt does not exist.")
        raise Exception("sar.txt does not exist.")
    elif not perf_script_path or not os.path.exists(perf_script_path):
        logger.warning("perf.script does not exist.")
        perf_script_path = None

    cpu_frequency_mhz = config.get("cpu_frequency_mhz", None)

    data = PIPAShuData(perf_stat_path, sar_path, perf_script_path).get_metrics(
        config["transaction"],
        config["cores"],
        dev=config.get("dev", None),
        freq_MHz=cpu_frequency_mhz,
    )

    config.pop("transaction")
    config.pop("cores")
    if "dev" in config:
        config.pop("dev")

    config["username"] = getpass.getuser()

    result = {**data, **config}
    logger.info("Data built successfully.")
    logger.info(str(result))
    return result


def send(data: dict, addr: str = None, port: int = 50051):
    """
    Sends the provided data to the specified address and port using the PIPADClient.

    Args:
        data (dict): The data to be sent.
        addr (str, optional): The address to send the data to. If not provided, the address will be retrieved from the data dictionary.
        port (int, optional): The port to send the data to. If not provided, the default port 50051 will be used.

    Returns:
        The result of the PIPADClient's deploy method.

    """
    if not addr:
        addr = data["pipad_addr"]
    if not port:
        port = data["pipad_port"]
    req = pipadlib.DeployRequest(
        transactions=data["transactions"],
        throughput=data["throughput"],
        used_threads=data["used_threads"],
        run_time=data["run_time"],
        cycles=data["cycles"],
        instructions=data["instructions"],
        cycles_per_second=data["cycles_per_second"],
        instructions_per_second=data["instructions_per_second"],
        CPI=data["CPI"],
        cycles_per_requests=data["cycles_per_requests"],
        path_length=data["path_length"],
        cpu_frequency_mhz=data["cpu_frequency_mhz"],
        cpu_usr=data[r"%usr"],
        cpu_nice=data[r"%nice"],
        cpu_sys=data[r"%sys"],
        cpu_iowait=data[r"%iowait"],
        cpu_steal=data[r"%steal"],
        cpu_irq=data[r"%irq"],
        cpu_soft=data[r"%soft"],
        cpu_guest=data[r"%guest"],
        cpu_gnice=data[r"%gnice"],
        cpu_idle=data[r"%idle"],
        cpu_util=data[r"%util"],
        kbmemfree=data["kbmemfree"],
        kbavail=data["kbavail"],
        kbmemused=data["kbmemused"],
        percent_memused=data[r"%memused"],
        kbbuffers=data["kbbuffers"],
        kbcached=data["kbcached"],
        kbcommit=data["kbcommit"],
        percent_commit=data[r"%commit"],
        kbactive=data["kbactive"],
        kbinact=data["kbinact"],
        kbdirty=data["kbdirty"],
        kbanonpg=data["kbanonpg"],
        kbslab=data["kbslab"],
        kbkstack=data["kbkstack"],
        kbpgtbl=data["kbpgtbl"],
        kbvmused=data["kbvmused"],
        tps=data["tps"],
        rkB_s=data[r"rkB/s"],
        wkB_s=data[r"wkB/s"],
        dkB_s=data[r"dkB/s"],
        areq_sz=data["areq-sz"],
        aqu_sz=data["aqu-sz"],
        disk_await=data["disk_await"],
        percent_disk_util=data[r"%disk_util"],
        workload=data["workload"],
        data_location=data["data_location"],
        dev=data["DEV"],
        hw_info=data["hw_info"],
        sw_info=data["sw_info"],
        platform=data["platform"],
        comment=data["comment"],
        username=data["username"],
    )

    logger.info(f"Sending data to {addr}:{port}")

    resp = PIPADClient(port, addr).deploy(req)

    if resp is not None:
        if resp.status_code == 200:
            logger.info("Upload success.")
            logger.info(
                f"Message: {resp.message}, Username: {resp.username}, Hash: {resp.hash}, Time: {resp.time}"
            )
        else:
            logger.warning(
                f"Upload failed: {resp.message} Status: {resp.status_code} time: {resp.time}"
            )
    return resp


def load(config_path: str = None, verbose: bool = False):
    """
    Load the configuration from a YAML file or prompt the user for configuration.

    Args:
        config_path (str, optional): Path to the YAML configuration file. Defaults to None.
        verbose (bool, optional): Flag indicating whether to enable verbose mode. Defaults to False.

    Returns:
        dict: The loaded configuration.

    """
    if config_path:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = quest()

    if verbose:
        print("Verbose mode enabled.")
        print("Configuration:", str(config))
    return config


def main(config_path: str = None, verbose: bool = False):
    """
    This is the main function for the upload service in the pipa project.

    Args:
        config_path (str, optional): The path to the configuration file. If not provided, the user will be prompted to enter the configuration.
        verbose (bool, optional): If True, the function will print additional information.

    Returns:
        None
    """

    data = build(load(config_path, verbose))

    if verbose:
        print("Data:", str(data))

    return send(data)


if __name__ == "__main__":
    main()
