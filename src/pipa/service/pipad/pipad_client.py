"""
pipad_client.py

send performance data to server:

```python
from pipa.service.pipad.pipad_client import PIPADClient
client = PIPADClient(port, address)
client.deploy(data=pipadlib.DeployRequest(
    workload="Test DB",
    transction=1000,
    latency=0.2,
    total_time=23.23,
    trans_per_second=32.3,
    cycles_per_second=3.4,
    instructions_per_second=3.44,
    cpu_frequency_mhz=3.2,
    cycles_per_instruction=3.3,
    path_length=2423,
    cpu_util=22,
    cpu_usr=3,
    cpu_sys=3,
    cpu_soft=4,
    cpu_nice=4,
    platform="X86",
    cpu="Intel IceLake",
    workload_config="Test",
    comment="Other"
))
```
"""

from __future__ import print_function
from typing import Optional
from pipa.common.logger import logger, stream_handler
import logging
import argparse
import grpc
import pipad_pb2 as pipadlib
import pipad_pb2_grpc as pipadgrpc


class PIPADClient():
    def __init__(self, port: Optional[int] = 5051, address: Optional[str] = "[::]") -> None:
        self._port = port
        self._address = address
    
    def deploy(self, data: pipadlib.DeployRequest) -> None:
        """
        Deploys the performance data using the PIPADClient to server, will store them to specified database.

        Args:
            data (pipadlib.DeployRequest): The performance data to deploy.

        Returns:
            None
        """
        server = f"{self._address}:{self._port}"
        logger.info("try to deploy ...")
        with grpc.insecure_channel(server) as channel:
            stub = pipadgrpc.PIPADStub(channel)
            response = stub.Deploy(data)
        logger.info(f"PIPAD client received: {response.message}")


if __name__ == "__main__":
    logger.setLevel(level=logging.DEBUG)
    stream_handler.setLevel(level=logging.DEBUG)
    argp = argparse.ArgumentParser()
    argp.add_argument("-a", "--address", type=str, default="127.0.0.1", help="Specify address binding")
    argp.add_argument("-p", "--port", type=int, default=50051, help="Specify metrics port")
    args = argp.parse_args()
    address = getattr(args, "address")
    port = getattr(args, "port")
    client = PIPADClient(port, address)
    client.deploy(data=pipadlib.DeployRequest(
        workload="Test DB",
        transction=1000,
        latency=0.2,
        total_time=23.23,
        trans_per_second=32.3,
        cycles_per_second=3.4,
        instructions_per_second=3.44,
        cpu_frequency_mhz=3.2,
        cycles_per_instruction=3.3,
        path_length=2423,
        cpu_util=22,
        cpu_usr=3,
        cpu_sys=3,
        cpu_soft=4,
        cpu_nice=4,
        platform="X86",
        cpu="Intel IceLake",
        workload_config="Test",
        comment="Other"
    ))
