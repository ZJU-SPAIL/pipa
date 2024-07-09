"""
pipad_server.py

start pipa grpc server:

```python
from pipa.service.pipad.pipad_server import PIPADServer
server = PIPADServer(data_location=dlocation, port=port, address=address, database=database, table=table)
server.serve()
```

you can specify the grafana url and api, PIPAD will automatically add a new connection of SQLite with path: data_location/database

```python
server = PIPADServer(data_location=dlocation, port=port, address=address, database=database, table=table, grafana_api_k=xxx, grafana_url=xxx)
```
"""

from concurrent import futures
from typing import Optional, Any
from pipa.common.logger import logger, stream_handler
import time
import os
import requests
import json
import logging
import sqlite3
import grpc
import argparse
from . import pipad_pb2 as pipadlib
from . import pipad_pb2_grpc as pipadgrpc


def type_proto_to_sqlite(proto: type) -> str:
    """
    Convert a request params' type to its corresponding SQLite type.

    Args:
        proto (type): The request params' type to be converted.

    Returns:
        str: The SQLite type corresponding to proto.

    Raises:
        NotImplementedError: If the request params's type has no corresbonding type in SQLite.

    """
    if proto is int:
        return "INTEGER"
    elif proto is str:
        return "TEXT"
    elif proto is float:
        return "REAL"
    else:
        raise NotImplementedError(f"{proto}'s type can't be converted to sqlite type")


def value_to_sqlite_str(v: Any) -> str:
    """
    A function that converts a value got from request to a SQLite value str representation.

    Args:
        v (Any): The value to be converted.

    Returns:
        str: The SQLite str representation of the value.
    """
    t = type(v)
    if t is str:
        return f"'{v}'"
    elif t is int or t is float:
        return f"{v}"
    else:
        raise NotImplementedError(f"{v} has type {t}, can't be converted to sqlite str")


class PIPADServer:
    class PIPAService(pipadgrpc.PIPADServicer):
        def __init__(self, outer: "PIPADServer") -> None:
            """
            Initializes a new instance of the PIPADServer.PIPAService class.

            Args:
                outer ('PIPADServer'): The outer object that this instance belongs to. Should be PIPADServer.

            Returns:
                None
            """
            self._outer = outer
            super().__init__()

        def Deploy(
            self, request: pipadlib.DeployRequest, context
        ) -> pipadlib.DeployResp:
            """
            Deploy api, send your data and store it in sqlite file

            Args:
                request (pipadlib.DeployRequest): Your request, contains performance metrics

            Returns:
                pipadlib.DeployResp: Response to client
            """
            upload_time = time.time()
            kvpairs = []
            logger.debug(f"Received request: {request}")
            params = []
            ks = []
            vs = []
            for i, param in enumerate(request.ListFields()):
                name = param[0].name
                value = param[1]
                try:
                    t = type_proto_to_sqlite(type(value))
                except NotImplementedError as e:
                    logger.debug(f"{e}")
                    t = "TEXT"
                if i == 0:
                    hs_prefix = f"{value}"
                try:
                    vtsqlites = value_to_sqlite_str(value)
                except NotImplementedError as e:
                    logger.debug(f"{e}")
                    vtsqlites = f"'{value}'"
                kvpairs.append(f"{name}{vtsqlites}")
                params.append(f"{name} {t}")
                ks.append(f"{name}")
                vs.append(f"{vtsqlites}")
            kvpairs.append(f"upload_time{upload_time}")
            hs_txt = f"'{hs_prefix}-{hash(tuple(kvpairs))}'"
            kvs = ",".join(params)
            kss = ",".join(ks)
            vss = ",".join(vs)
            create_table_comm = f"CREATE TABLE IF NOT EXISTS {self._outer._table} (hash TEXT PRIMARY KEY,upload_time INTEGER,{kvs})"
            insert_table_comm = f"INSERT INTO {self._outer._table} (hash,upload_time,{kss}) VALUES ({hs_txt},{upload_time},{vss})"
            logger.debug(f"Request to Table component: {kvs}")
            logger.debug(f"Request's Keys: {kss}")
            logger.debug(f"Request's Values: {vss}")
            logger.debug(f"Create table SQL: {create_table_comm}")
            logger.debug(f"Insert value SQL: {insert_table_comm}")
            try:
                with sqlite3.connect(self._outer._database_loc) as conn:
                    cursor = conn.cursor()
                    cursor.execute(create_table_comm)
                    cursor.execute(insert_table_comm)
                    conn.commit()
            except sqlite3.Error as e:
                logger.debug(f"Database Error: {e}")
                return pipadlib.DeployResp(message=f"deploy failed. Contact admin. {e}")
            return pipadlib.DeployResp(message="deploy success")

    def __init__(
        self,
        data_location: Optional[str] = "./",
        port: Optional[int] = 5051,
        address: Optional[str] = "[::]",
        database: str = "example.db",
        table: str = "example",
        grafana_api_k: Optional[str] = None,
        grafana_url: Optional[str] = None,
    ) -> None:
        """
        Initialize the PIPADServer.

        Args:
            data_location (str, optional): The location to store the database files. Defaults to "./".
            port (int, optional): The port to bind to. Defaults to 5051.
            address (str, optional): The IP address to bind to. Defaults to "[::]".
            database (str, optional): The name of the database to store the results. Defaults to "example.db".
            table (str, optional): The name of the table in the database to store the results. Defaults to "example".
            grafana_api_k (str, optional): The API key for Grafana. Required if grafana_url is provided.
            grafana_url (str, optional): The URL for Grafana. Required if grafana_api_k is provided.
        """
        self._dlocation = data_location
        self._port = port
        self._address = address
        self._database = database
        self._table = table
        self._database_loc = os.path.join(data_location, database)
        if grafana_api_k is not None and grafana_url is not None:
            self._grafana = {"api_key": grafana_api_k, "url": grafana_url}
            new_conn = {
                "name": database,
                "type": "frser-sqlite-datasource",
                "access": "proxy",
                "jsonData": {"path": self._database_loc},
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {grafana_api_k}",
            }

            response = requests.post(
                f"{grafana_url}/api/datasources",
                headers=headers,
                data=json.dumps(new_conn),
            )

            if response.status_code == 200:
                logger.info(f"New connection {self._database_loc} added successfully")
            elif response.status_code == 409:
                logger.debug(f"connection {self._database_loc} exists")
            else:
                logger.error(
                    f"Failed to add new connection {self._database_loc}: {response.status_code}"
                )
                logger.error(response.json())

    def serve(self) -> None:
        """
        Initiate the server, add the PIPAD service to the server, start the server, and wait for termination.
        """
        binding = f"{self._address}:{self._port}"
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
        pipadgrpc.add_PIPADServicer_to_server(self.PIPAService(self), server)
        server.add_insecure_port(binding)
        server.start()
        logger.info(f"Server started, listening on {binding}")
        server.wait_for_termination()


def main():
    logger.setLevel(level=logging.DEBUG)
    stream_handler.setLevel(level=logging.DEBUG)
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-a", "--address", type=str, default="127.0.0.1", help="Specify address binding"
    )
    argp.add_argument(
        "-p", "--port", type=int, default=50051, help="Specify metrics port"
    )
    argp.add_argument(
        "-d",
        "--database",
        type=str,
        default="example.db",
        help="Specify which database to store data",
    )
    argp.add_argument(
        "-t", "--table", type=str, default="example", help="Specify table name"
    )
    argp.add_argument(
        "-l", "--data-location", type=str, default="./", help="Specify data location"
    )
    args = argp.parse_args()
    address = getattr(args, "address")
    port = getattr(args, "port")
    database = getattr(args, "database")
    table = getattr(args, "table")
    dlocation = getattr(args, "data_location")
    server = PIPADServer(
        data_location=dlocation,
        port=port,
        address=address,
        database=database,
        table=table,
    )
    server.serve()


if __name__ == "__main__":
    main()
