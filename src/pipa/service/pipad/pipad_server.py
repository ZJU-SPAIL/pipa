"""
pipad_server.py

start pipa grpc server:

```python
from pipa.service.pipad.pipad_server import PIPADServer
server = PIPADServer(port, address, database, table)
server.serve()
```
"""

from concurrent import futures
from typing import Optional, Any
from pipa.common.logger import logger, stream_handler
import logging
import sqlite3
import grpc
import argparse
import pipad_pb2 as pipadlib
import pipad_pb2_grpc as pipadgrpc


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
    if type(v) is str:
        return f"'{v}'"
    else:
        return f"{v}"


class PIPADServer:
    class PIPAService(pipadgrpc.PIPADServicer):
        def __init__(self, outer) -> None:
            """
            Initializes a new instance of the PIPADServer.PIPAService class.

            Args:
                outer (object): The outer object that this instance belongs to. Should be PIPADServer.

            Returns:
                None
            """
            self._outer = outer
            super().__init__()
        
        def Deploy(self, request: pipadlib.DeployRequest, context) -> pipadlib.DeployResp:
            """
            Deploy api, send your data and store it in sqlite file

            Args:
                request (pipadlib.DeployRequest: Your request, contains performance metrics

            Returns:
                pipadlib.DeployResp: Response to client
            """
            logger.debug(f"Received request: {request}")
            params = []
            ks = []
            vs = []
            for i, param in enumerate(request.ListFields()):
                name = param[0].name
                value = param[1]
                try:
                    t = type_proto_to_sqlite(type(param[1]))
                except NotImplementedError as e:
                    logger.debug(f"Encounter param named {name}'s type can't be converted to sqlite type")
                    t = "TEXT"
                primary = 'PRIMARY KEY' if i == 0 else ''
                params.append(f"{name} {t} {primary}")
                ks.append(f"{name}")
                vs.append(f"{value_to_sqlite_str(value)}")
            kvs = ','.join(params)
            kss = ','.join(ks)
            vss = ','.join(vs)
            create_table_comm = f"CREATE TABLE IF NOT EXISTS {self._outer._table} ({kvs})"
            insert_table_comm = f"INSERT INTO {self._outer._table} ({kss}) VALUES ({vss})"
            logger.debug(f"Create table component: {kvs}")
            logger.debug(f"Keys: {kss}")
            logger.debug(f"Values: {vss}")
            logger.debug(f"Create table SQL: {create_table_comm}")
            logger.debug(f"Insert value SQL: {insert_table_comm}")
            try:
                conn = sqlite3.connect(self._outer._database)
                cursor = conn.cursor()
                cursor.execute(create_table_comm)
                cursor.execute(insert_table_comm)
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                logger.error(f"Database Error: {e}")
                return pipadlib.DeployResp(message="deploy failed. Contact admin.")
            return pipadlib.DeployResp(message="deploy success")

    def __init__(self, port: Optional[int] = 5051, address: Optional[str] = "[::]", database: str = "example.db", table: str = "example") -> None:
        """
        Init PIPADServer

        Args:
            port (Optional[int], optional): Set binding port. Defaults to 5051.
            address (_type_, optional): Set binding address. Defaults to "[::]".
            database (str, optional): Set database to store the results. Defaults to "example.db".
            table (str, optional): Set which table in database to store the results, will be created if not exits. Defaults to "example".
        """
        self._port = port
        self._address = address
        self._database = database
        self._table = table
    
    def serve(self) -> None:
        """
        Initiate the server, add the PIPAD service to the server, start the server, and wait for termination.
        """
        binding = f"{self._address}:{self._port}"
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        pipadgrpc.add_PIPADServicer_to_server(self.PIPAService(self), server)
        server.add_insecure_port(binding)
        server.start()
        logger.info(f"Server started, listening on {binding}")
        server.wait_for_termination()


if __name__ == "__main__":
    logger.setLevel(level=logging.DEBUG)
    stream_handler.setLevel(level=logging.DEBUG)
    argp = argparse.ArgumentParser()
    argp.add_argument("-a", "--address", type=str, default="127.0.0.1", help="Specify address binding")
    argp.add_argument("-p", "--port", type=int, default=50051, help="Specify metrics port")
    argp.add_argument("-d", "--database", type=str, default="example.db", help="Specify which database to store data")
    argp.add_argument("-t", "--table", type=str, default="example", help="Specify table name")
    args = argp.parse_args()
    address = getattr(args, "address")
    port = getattr(args, "port")
    database = getattr(args, "database")
    table = getattr(args, "table")
    server = PIPADServer(port, address, database, table)
    server.serve()
