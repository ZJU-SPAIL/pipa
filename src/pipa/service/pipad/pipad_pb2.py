# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pipad.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0bpipad.proto\x12\x04pipa\"\xa1\x03\n\rDeployRequest\x12\x10\n\x08workload\x18\x01 \x01(\t\x12\x12\n\ntransction\x18\x02 \x01(\x04\x12\x0f\n\x07latency\x18\x03 \x01(\x01\x12\x12\n\ntotal_time\x18\x04 \x01(\x01\x12\x18\n\x10trans_per_second\x18\x05 \x01(\x01\x12\x19\n\x11\x63ycles_per_second\x18\x06 \x01(\x01\x12\x1f\n\x17instructions_per_second\x18\x07 \x01(\x01\x12\x19\n\x11\x63pu_frequency_mhz\x18\x08 \x01(\x01\x12\x1e\n\x16\x63ycles_per_instruction\x18\t \x01(\x01\x12\x13\n\x0bpath_length\x18\n \x01(\x01\x12\x10\n\x08\x63pu_util\x18\x0b \x01(\x01\x12\x0f\n\x07\x63pu_usr\x18\x0c \x01(\x01\x12\x0f\n\x07\x63pu_sys\x18\r \x01(\x01\x12\x10\n\x08\x63pu_soft\x18\x0e \x01(\x01\x12\x10\n\x08\x63pu_nice\x18\x0f \x01(\x01\x12\x10\n\x08platform\x18\x10 \x01(\t\x12\x0b\n\x03\x63pu\x18\x11 \x01(\t\x12\x17\n\x0fworkload_config\x18\x12 \x01(\t\x12\x0f\n\x07\x63omment\x18\x13 \x01(\t\"\x1d\n\nDeployResp\x12\x0f\n\x07message\x18\x01 \x01(\t2\xbb\x01\n\x05PIPAD\x12\x31\n\x06\x44\x65ploy\x12\x13.pipa.DeployRequest\x1a\x10.pipa.DeployResp\"\x00\x12>\n\x11\x44\x65ployStreamReply\x12\x13.pipa.DeployRequest\x1a\x10.pipa.DeployResp\"\x00\x30\x01\x12?\n\x10\x44\x65ployBidiStream\x12\x13.pipa.DeployRequest\x1a\x10.pipa.DeployResp\"\x00(\x01\x30\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pipad_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_DEPLOYREQUEST']._serialized_start=22
  _globals['_DEPLOYREQUEST']._serialized_end=439
  _globals['_DEPLOYRESP']._serialized_start=441
  _globals['_DEPLOYRESP']._serialized_end=470
  _globals['_PIPAD']._serialized_start=473
  _globals['_PIPAD']._serialized_end=660
# @@protoc_insertion_point(module_scope)
