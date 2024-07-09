import questionary
from rich import print
import os
from pipa.service.pipashu import PIPAShuData
from pipa.common.logger import logger
from pipa.service.pipad.pipad_client import PIPADClient


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
    data_dir = config["data_location"]
    perf_stat_path = os.path.join(data_dir, "perf-stat.csv")
    sar_path = os.path.join(data_dir, "sar.txt")
    perf_script_path = os.path.exists(os.path.join(data_dir, "perf.script"))

    if not os.path.exists(perf_stat_path):
        logger.error("perf-stat.csv does not exist.")
        raise "perf-stat.csv does not exist."
    elif not os.path.exists(sar_path):
        logger.error("sar.txt does not exist.")
        raise "sar.txt does not exist."
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


def send(data: dict):
    address = data.pop("pipad_addr")
    port = data.pop("pipad_port")

    client = PIPADClient(port, address)
    client.deploy(
        # TODO: Fix the data format
    )


def main():
    config = quest()
    data = build(config)
    send(data)


if __name__ == "__main__":
    main()
