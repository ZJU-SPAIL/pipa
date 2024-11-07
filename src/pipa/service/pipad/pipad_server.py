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
from pipa.common.export import SQLiteConnector
from pipa.common.utils import get_timestamp
from datetime import datetime
import time
import os
import requests
import json
import logging
import sqlite3
import grpc
import argparse
import uuid
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
        v = v.replace("'", "''")
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
            uid = uuid.uuid4()
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
                    record_prefix = f"{value}"
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
            hasht = f"'{hash(tuple(kvpairs))}'"
            upload_datetime = datetime.fromtimestamp(upload_time).strftime(
                r"%Y-%m-%d %H:%M:%S.%f"
            )
            record = f"{record_prefix} {upload_datetime} {uid}"
            kvs = ",".join(params)
            kss = ",".join(ks)
            vss = ",".join(vs)
            create_table_comm = f"CREATE TABLE IF NOT EXISTS {self._outer._table} (hash TEXT PRIMARY KEY,upload_time INTEGER,record TEXT,{kvs})"
            insert_table_comm = f"INSERT INTO {self._outer._table} (hash,upload_time,record,{kss}) VALUES ({hasht},{upload_time},{value_to_sqlite_str(record)},{vss})"
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
                return pipadlib.DeployResp(
                    message=f"deploy failed. Contact admin. {e}", status_code=500
                )
            return pipadlib.DeployResp(
                message="deploy success",
                username=request.username,
                hash=hasht,
                time=f"{upload_time}",
                upload_datetime=upload_datetime,
                status_code=200,
            )

        def DownloadFullTable(
            self, request: pipadlib.DownloadFullTableRequest, context
        ) -> pipadlib.DownloadFullTableResp:
            """
            Download the full table from the SQLite database.

            Args:
                request (pipadlib.DownloadFullTableRequest): The request containing the table name and file options.

            Returns:
                pipadlib.DownloadFullTableResp: The response containing the file content.
            """
            table_name = request.table_name
            file_option = request.file_option
            try:
                if file_option == "csv":
                    dst = f"/tmp/{table_name}_{get_timestamp()}.csv"
                    SQLiteConnector(self._outer._database_loc).export_table_to_csv(
                        table_name, dst
                    )
                elif file_option == "xlsx":
                    dst = f"/tmp/{table_name}_{get_timestamp()}.xlsx"
                    SQLiteConnector(self._outer._database_loc).export_table_to_excel(
                        table_name, dst
                    )
                else:
                    raise NotImplementedError(
                        f"File option {file_option} not supported"
                    )
                with open(dst, "rb") as f:
                    file_content = f.read()
                logger.info(f"Downloaded table {table_name} to {dst}")
            except sqlite3.Error as e:
                logger.error(f"Database Error: {e}")
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Database error: {e}")
                return pipadlib.DownloadFullTableResp(file_content=b"")

            return pipadlib.DownloadFullTableResp(file_content=file_content)

    def __init__(
        self,
        data_location: Optional[str] = "./",
        port: Optional[int] = 5051,
        address: Optional[str] = "[::]",
        database_name: str = "example.db",
        table_name: str = "example",
        grafana_api_k: Optional[str] = None,
        grafana_url: Optional[str] = None,
        grafana_path: Optional[str] = None,
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
            grafana_path (str, optional): Replace the exact path name in grafana's database connection settings. Usefule for service in container.
        """
        self._dlocation = data_location
        self._port = port
        self._address = address
        self._database = database_name
        self._table = table_name
        self._database_loc = os.path.join(data_location, database_name)
        try:
            with sqlite3.connect(self._database_loc) as conn:
                logger.info(f"Use SQLite3: {sqlite3.sqlite_version}")
        except sqlite3.Error as e:
            logger.debug(
                f"Encounting problems when creating {self._database_loc}: {e}."
            )
            return
        if grafana_api_k is not None and grafana_url is not None:
            if grafana_path is not None:
                exact_path = f"{grafana_path}/{database_name}"
            else:
                exact_path = self._database_loc
            self._grafana = {"api_key": grafana_api_k, "url": grafana_url}
            new_conn = {
                "name": database_name,
                "type": "frser-sqlite-datasource",
                "access": "proxy",
                "jsonData": {"path": exact_path},
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
        try:
            server.wait_for_termination()
        except KeyboardInterrupt as e:
            logger.info("Server stop")
            server.stop(5)


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
    argp.add_argument(
        "--grafana-key",
        type=str,
        default=None,
        help="Specify grafana api key for connection",
    )
    argp.add_argument(
        "--grafana-url", type=str, default=None, help="Specify grafana url"
    )
    argp.add_argument(
        "--grafana-path",
        type=str,
        default=None,
        help="Specify grafana's exact data store path mapping with data-location",
    )
    args = argp.parse_args()
    address = getattr(args, "address")
    port = getattr(args, "port")
    database = getattr(args, "database")
    table = getattr(args, "table")
    dlocation = getattr(args, "data_location")
    gkey = getattr(args, "grafana_key")
    gurl = getattr(args, "grafana_url")
    gpath = getattr(args, "grafana_path")
    server = PIPADServer(
        data_location=dlocation,
        port=port,
        address=address,
        database_name=database,
        table_name=table,
        grafana_api_k=gkey,
        grafana_url=gurl,
        grafana_path=gpath,
    )
    server.serve()


if __name__ == "__main__":
    main()
