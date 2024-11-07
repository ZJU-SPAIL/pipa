from .pipad.pipad_client import PIPADClient
from pipa.common.utils import get_timestamp
from pipa.common.logger import logger
import questionary
import os
import argparse


def download(ip, port, table_name: str, file_format: str, dirs: str = "."):
    file_rcv: bytes = PIPADClient.download_full_table(ip, port, table_name, file_format)
    table_path = os.path.join(dirs, f"{table_name}_{get_timestamp()}.{file_format}")
    try:
        with open(table_path, "wb") as f:
            f.write(file_rcv)
        print(f"Table {table_name} downloaded successfully to {table_path}")
    except Exception as e:
        logger.error(f"Failed to download table {table_name}: {e}")


def prompt_user_for_details():
    ip = questionary.text("What's PIPAD IP address?").ask()
    port = questionary.text("What's PIPAD port?").ask()
    table_name = questionary.text("What's table name?").ask()
    file_format = questionary.select(
        "Which file format do you want to download?",
        choices=["xlsx", "csv"],
    ).ask()
    return ip, port, table_name, file_format


def main():
    parser = argparse.ArgumentParser(description="Download table from PIPAD")
    parser.add_argument("--ip", type=str, help="PIPAD IP address")
    parser.add_argument("--port", type=str, help="PIPAD port")
    parser.add_argument("--table", type=str, help="Table name")
    parser.add_argument(
        "--format", type=str, choices=["xlsx", "csv"], help="File format"
    )
    args = parser.parse_args()

    if args.ip and args.port and args.table and args.format:
        ip, port, table_name, file_format = (
            args.ip,
            args.port,
            args.table,
            args.format,
        )
    else:
        ip, port, table_name, file_format = prompt_user_for_details()
    download(ip, port, table_name, file_format)
