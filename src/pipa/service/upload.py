import questionary
from rich import print
import os
from pipa.service.pipashu import PIPAShuData
from pipa.common.logger import logger
from pipa.service.pipad.pipad_client import PIPADClient
import pipa.service.pipad.pipad_pb2 as pipadlib


def check_workload(workload):
    if workload == "":
        print("Please input a valid workload name.")
        exit(1)


def check_transaction(transaction):
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
    if data_location == "":
        print("Please input a valid data location.")
        exit(1)
    elif not os.path.exists(data_location):
        print("The folder does not exist.")
        exit(1)


def check_cores(cores):
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
        "comment": comment,
        "pipad_addr": pipad_server,
        "pipad_port": pipad_port,
    }


def build(config: dict):
    """
    Builds the data for upload based on the given configuration.

    Args:
        config (dict): A dictionary containing the configuration parameters.

    Returns:
        dict: A dictionary containing the built data for upload.

    Raises:
        Exception: If the required files are missing.

    """
    data_dir = config["data_location"]
    perf_stat_path = os.path.join(data_dir, "perf-stat.csv")
    sar_path = os.path.join(data_dir, "sar.txt")
    perf_script_path = os.path.exists(os.path.join(data_dir, "perf.script"))

    if not os.path.exists(perf_stat_path):
        logger.error("perf-stat.csv does not exist.")
        raise Exception("perf-stat.csv does not exist.")
    elif not os.path.exists(sar_path):
        logger.error("sar.txt does not exist.")
        raise Exception("sar.txt does not exist.")
    elif not perf_script_path:
        logger.warning("perf-record.txt does not exist.")
        perf_script_path = None

    data = PIPAShuData(perf_stat_path, sar_path, perf_script_path).get_metrics(
        config["transaction"], config["cores"], dev=config["dev"]
    )
    config.pop("transaction")
    config.pop("cores")
    config.pop("dev")
    return {**data, **config}


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
        address = data["pipad_addr"]
    if not port:
        port = data["pipad_port"]

    return PIPADClient(port, address).deploy(
        pipadlib.DeployRequest(
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
            disk_await=data["await"],
            percent_disk_util=data[r"%disk_util"],
            workload=data["workload"],
            data_location=data["data_location"],
            dev=data["DEV"],
            hw_info=data["hw_info"],
            sw_info=data["sw_info"],
            platform=data["platform"],
            comment=data["comment"],
        )
    )


def main(config=quest()):
    """
    This is the main function for the upload service in the pipa project.

    Args:
        config: The configuration for the upload service. Defaults to the result of the `quest` function.

    Returns:
        None
    """
    data = build(config)
    send(data)


if __name__ == "__main__":
    main()
