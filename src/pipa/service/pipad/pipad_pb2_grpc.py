# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from . import pipad_pb2 as pipad__pb2

GRPC_GENERATED_VERSION = "1.67.1"
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower

    _version_not_supported = first_version_is_lower(
        GRPC_VERSION, GRPC_GENERATED_VERSION
    )
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f"The grpc package installed is at version {GRPC_VERSION},"
        + f" but the generated code in pipad_pb2_grpc.py depends on"
        + f" grpcio>={GRPC_GENERATED_VERSION}."
        + f" Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}"
        + f" or downgrade your generated code using grpcio-tools<={GRPC_VERSION}."
    )


class PIPADStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Deploy = channel.unary_unary(
            "/pipa.PIPAD/Deploy",
            request_serializer=pipad__pb2.DeployRequest.SerializeToString,
            response_deserializer=pipad__pb2.DeployResp.FromString,
            _registered_method=True,
        )
        self.DeployStreamReply = channel.unary_stream(
            "/pipa.PIPAD/DeployStreamReply",
            request_serializer=pipad__pb2.DeployRequest.SerializeToString,
            response_deserializer=pipad__pb2.DeployResp.FromString,
            _registered_method=True,
        )
        self.DeployBidiStream = channel.stream_stream(
            "/pipa.PIPAD/DeployBidiStream",
            request_serializer=pipad__pb2.DeployRequest.SerializeToString,
            response_deserializer=pipad__pb2.DeployResp.FromString,
            _registered_method=True,
        )
        self.DownloadFullTable = channel.unary_unary(
            "/pipa.PIPAD/DownloadFullTable",
            request_serializer=pipad__pb2.DownloadFullTableRequest.SerializeToString,
            response_deserializer=pipad__pb2.DownloadFullTableResp.FromString,
            _registered_method=True,
        )


class PIPADServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Deploy(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def DeployStreamReply(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def DeployBidiStream(self, request_iterator, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def DownloadFullTable(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_PIPADServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "Deploy": grpc.unary_unary_rpc_method_handler(
            servicer.Deploy,
            request_deserializer=pipad__pb2.DeployRequest.FromString,
            response_serializer=pipad__pb2.DeployResp.SerializeToString,
        ),
        "DeployStreamReply": grpc.unary_stream_rpc_method_handler(
            servicer.DeployStreamReply,
            request_deserializer=pipad__pb2.DeployRequest.FromString,
            response_serializer=pipad__pb2.DeployResp.SerializeToString,
        ),
        "DeployBidiStream": grpc.stream_stream_rpc_method_handler(
            servicer.DeployBidiStream,
            request_deserializer=pipad__pb2.DeployRequest.FromString,
            response_serializer=pipad__pb2.DeployResp.SerializeToString,
        ),
        "DownloadFullTable": grpc.unary_unary_rpc_method_handler(
            servicer.DownloadFullTable,
            request_deserializer=pipad__pb2.DownloadFullTableRequest.FromString,
            response_serializer=pipad__pb2.DownloadFullTableResp.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "pipa.PIPAD", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers("pipa.PIPAD", rpc_method_handlers)


# This class is part of an EXPERIMENTAL API.
class PIPAD(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Deploy(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/pipa.PIPAD/Deploy",
            pipad__pb2.DeployRequest.SerializeToString,
            pipad__pb2.DeployResp.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )

    @staticmethod
    def DeployStreamReply(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_stream(
            request,
            target,
            "/pipa.PIPAD/DeployStreamReply",
            pipad__pb2.DeployRequest.SerializeToString,
            pipad__pb2.DeployResp.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )

    @staticmethod
    def DeployBidiStream(
        request_iterator,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.stream_stream(
            request_iterator,
            target,
            "/pipa.PIPAD/DeployBidiStream",
            pipad__pb2.DeployRequest.SerializeToString,
            pipad__pb2.DeployResp.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )

    @staticmethod
    def DownloadFullTable(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/pipa.PIPAD/DownloadFullTable",
            pipad__pb2.DownloadFullTableRequest.SerializeToString,
            pipad__pb2.DownloadFullTableResp.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )
