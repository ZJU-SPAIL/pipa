from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class DeployRequest(_message.Message):
    __slots__ = ("workload", "transction", "latency", "total_time", "trans_per_second", "cycles_per_second", "instructions_per_second", "cpu_frequency_mhz", "cycles_per_instruction", "path_length", "cpu_util", "cpu_usr", "cpu_sys", "cpu_soft", "cpu_nice", "platform", "cpu", "workload_config", "comment")
    WORKLOAD_FIELD_NUMBER: _ClassVar[int]
    TRANSCTION_FIELD_NUMBER: _ClassVar[int]
    LATENCY_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TIME_FIELD_NUMBER: _ClassVar[int]
    TRANS_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    CYCLES_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTIONS_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    CPU_FREQUENCY_MHZ_FIELD_NUMBER: _ClassVar[int]
    CYCLES_PER_INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    PATH_LENGTH_FIELD_NUMBER: _ClassVar[int]
    CPU_UTIL_FIELD_NUMBER: _ClassVar[int]
    CPU_USR_FIELD_NUMBER: _ClassVar[int]
    CPU_SYS_FIELD_NUMBER: _ClassVar[int]
    CPU_SOFT_FIELD_NUMBER: _ClassVar[int]
    CPU_NICE_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    CPU_FIELD_NUMBER: _ClassVar[int]
    WORKLOAD_CONFIG_FIELD_NUMBER: _ClassVar[int]
    COMMENT_FIELD_NUMBER: _ClassVar[int]
    workload: str
    transction: int
    latency: float
    total_time: float
    trans_per_second: float
    cycles_per_second: float
    instructions_per_second: float
    cpu_frequency_mhz: float
    cycles_per_instruction: float
    path_length: float
    cpu_util: float
    cpu_usr: float
    cpu_sys: float
    cpu_soft: float
    cpu_nice: float
    platform: str
    cpu: str
    workload_config: str
    comment: str
    def __init__(self, workload: _Optional[str] = ..., transction: _Optional[int] = ..., latency: _Optional[float] = ..., total_time: _Optional[float] = ..., trans_per_second: _Optional[float] = ..., cycles_per_second: _Optional[float] = ..., instructions_per_second: _Optional[float] = ..., cpu_frequency_mhz: _Optional[float] = ..., cycles_per_instruction: _Optional[float] = ..., path_length: _Optional[float] = ..., cpu_util: _Optional[float] = ..., cpu_usr: _Optional[float] = ..., cpu_sys: _Optional[float] = ..., cpu_soft: _Optional[float] = ..., cpu_nice: _Optional[float] = ..., platform: _Optional[str] = ..., cpu: _Optional[str] = ..., workload_config: _Optional[str] = ..., comment: _Optional[str] = ...) -> None: ...

class DeployResp(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...
