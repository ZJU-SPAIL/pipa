"""
pipad_client.py

send performance data to server:

```python
from pipa.service.pipad.pipad_client import PIPADClient
import pipa.service.pipad.pipad_pb2 as pipadlib

client = PIPADClient(port="50051", address="127.0.0.1")
client.deploy(data=pipadlib.DeployRequest(
    transactions=3423523,
    throughput=251.57342,
    used_threads=[36,44],
    run_time=322.4164,
    cycles=1232142629,
    instructions=40847985,
    cycles_per_second=40636919.1644998,
    instructions_per_second=135971.3205,
    CPI=0.29867620232,
    cycles_per_requests=1613.3812311,
    path_length=540178.22362178,
    cpu_frequency_mhz=3435.1,
    cpu_usr=78.33,
    cpu_nice=0.0,
    cpu_sys=0.16,
    cpu_iowait=0.0,
    cpu_steal=0.0,
    cpu_irq=0.13,
    cpu_soft=0.0,
    cpu_guest=0.0,
    cpu_gnice=0.0,
    cpu_idle=0.32,
    cpu_util=99.68,
    kbmemfree=782348669,
    kbavail=7847456900,
    kbmemused=281231,
    percent_memused=0.2,
    kbbuffers=2631,
    kbcached=4323857,
    kbcommit=345630,
    percent_commit=0.43,
    kbactive=15324194,
    kbinact=5223120,
    kbdirty=456,
    kbanonpg=2102529,
    kbslab=556534,
    kbkstack=18573,
    kbpgtbl=39314,
    kbvmused=454329,
    tps=0.75,
    rkB_s=0.0,
    wkB_s=30.27,
    dkB_s=0.0,
    areq_sz=40.32,
    aqu_sz=0.01,
    disk_await=6.18,
    percent_disk_util=0.43,
    workload='rocksdb',
    data_location='xxx',
    dev='sdc',
    hw_info='1*1*1',
    sw_info='xxx',
    platform='xx',
    comment='',
))
```
"""

from typing import Optional
from pipa.common.logger import logger, stream_handler
import logging
import argparse
import grpc
from . import pipad_pb2 as pipadlib
from . import pipad_pb2_grpc as pipadgrpc


class PIPADClient:
    def __init__(
        self, port: Optional[int] = 5051, address: Optional[str] = "[::]"
    ) -> None:
        self._port = port
        self._address = address

    def deploy(self, data: pipadlib.DeployRequest) -> Optional[pipadlib.DeployResp]:
        """
        Deploys the performance data using the PIPADClient to server, will store them to specified database.

        Args:
            data (pipadlib.DeployRequest): The performance data to deploy.

        Returns:
            None
        """
        server = f"{self._address}:{self._port}"
        logger.info("try to deploy ...")
        try:
            with grpc.insecure_channel(server) as channel:
                stub = pipadgrpc.PIPADStub(channel)
                response: pipadlib.DeployResp = stub.Deploy(data)
            return response
        except Exception as e:
            logger.error(f"Client deploy received error: {e}")
            return None

    def download_full_table(
        self, pipad_ip_addr, pipad_port, table_name, file_option="xlsx"
    ):
        """
        Download the full table from the server.

        Args:
            pipad_ip_addr (str): The IP address of the PIPAD server.
            pipad_port (int): The port of the PIPAD server.
            table_name (str): The name of the table to download.
            file_option (str): The file option. Default is "xlsx".

        Returns:
            Optional[bytes]
        """
        server = f"{pipad_ip_addr}:{pipad_port}"
        logger.info("try to download full table ...")
        try:
            with grpc.insecure_channel(server) as channel:
                stub = pipadgrpc.PIPADStub(channel)
                response = stub.DownloadFullTable(
                    pipadlib.DownloadFullTableRequest(
                        pipad_ip_addr=pipad_ip_addr,
                        pipad_port=pipad_port,
                        table_name=table_name,
                        file_option=file_option,
                    )
                )
            return response.file_content
        except Exception as e:
            logger.error(f"Client download full table received error: {e}")
            return None


if __name__ == "__main__":
    logger.setLevel(level=logging.DEBUG)
    stream_handler.setLevel(level=logging.DEBUG)
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-a", "--address", type=str, default="127.0.0.1", help="Specify address binding"
    )
    argp.add_argument(
        "-p", "--port", type=int, default=50051, help="Specify metrics port"
    )
    args = argp.parse_args()
    address = getattr(args, "address")
    port = getattr(args, "port")
    client = PIPADClient(port, address)
    resp = client.deploy(
        data=pipadlib.DeployRequest(
            transactions=7561946,
            throughput=25171.548361957342,
            used_threads=[36],
            run_time=300.416402331,
            cycles=1220032142629,
            instructions=4084798557821,
            cycles_per_second=4061136919.1644998,
            instructions_per_second=13597122281.3605,
            CPI=0.2986762077393152,
            cycles_per_requests=161338.38335119028,
            path_length=540178.2236769478,
            cpu_frequency_mhz=34545.1,
            cpu_usr=99.39,
            cpu_nice=0.0,
            cpu_sys=0.16,
            cpu_iowait=0.0,
            cpu_steal=0.0,
            cpu_irq=0.13,
            cpu_soft=0.0,
            cpu_guest=0.0,
            cpu_gnice=0.0,
            cpu_idle=0.32,
            cpu_util=99.68,
            kbmemfree=783648669,
            kbavail=784724900,
            kbmemused=2875231,
            percent_memused=0.36,
            kbbuffers=268061,
            kbcached=4379857,
            kbcommit=3459630,
            percent_commit=0.43,
            kbactive=1530294,
            kbinact=5261120,
            kbdirty=456,
            kbanonpg=2102529,
            kbslab=556534,
            kbkstack=18573,
            kbpgtbl=39314,
            kbvmused=454329,
            tps=0.75,
            rkB_s=0.0,
            wkB_s=30.27,
            dkB_s=0.0,
            areq_sz=40.32,
            aqu_sz=0.01,
            disk_await=6.18,
            percent_disk_util=0.43,
            workload="rocksdb",
            data_location="/home/xyjiang/project/rocksdb-perf/data/randomread/static/purple-openEuler/t1-rocksdb7.9.2/perf-stat-sar-less/",
            dev="sdc",
            hw_info="1*1*1",
            sw_info="1 thread, RocksDB 7.9.2 build in release mode, debug_level=0, threads_num=1, db_bench with benchmark.sh",
            platform="SPR 4510",
            comment="",
            username="HiAll",
        )
    )
    if resp is not None:
        if resp.status_code == 200:
            logger.info(
                f"Message: {resp.message}, Username: {resp.username}, Hash: {resp.hash}, Time: {resp.time}, Datetime: {resp.upload_datetime}"
            )
        else:
            logger.warning(f"PIPAD server resp faild: {resp.message}")
