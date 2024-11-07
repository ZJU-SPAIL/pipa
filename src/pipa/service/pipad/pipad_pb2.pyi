from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class DeployRequest(_message.Message):
    __slots__ = (
        "workload",
        "transactions",
        "throughput",
        "used_threads",
        "run_time",
        "cycles",
        "instructions",
        "cycles_per_second",
        "instructions_per_second",
        "CPI",
        "cycles_per_requests",
        "path_length",
        "cpu_frequency_mhz",
        "cpu_usr",
        "cpu_nice",
        "cpu_sys",
        "cpu_iowait",
        "cpu_steal",
        "cpu_irq",
        "cpu_soft",
        "cpu_guest",
        "cpu_gnice",
        "cpu_idle",
        "cpu_util",
        "kbmemfree",
        "kbavail",
        "kbmemused",
        "percent_memused",
        "kbbuffers",
        "kbcached",
        "kbcommit",
        "percent_commit",
        "kbactive",
        "kbinact",
        "kbdirty",
        "kbanonpg",
        "kbslab",
        "kbkstack",
        "kbpgtbl",
        "kbvmused",
        "dev",
        "tps",
        "rkB_s",
        "wkB_s",
        "dkB_s",
        "areq_sz",
        "aqu_sz",
        "disk_await",
        "percent_disk_util",
        "data_location",
        "hw_info",
        "sw_info",
        "platform",
        "comment",
        "username",
    )
    WORKLOAD_FIELD_NUMBER: _ClassVar[int]
    TRANSACTIONS_FIELD_NUMBER: _ClassVar[int]
    THROUGHPUT_FIELD_NUMBER: _ClassVar[int]
    USED_THREADS_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    CYCLES_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    CYCLES_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTIONS_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    CPI_FIELD_NUMBER: _ClassVar[int]
    CYCLES_PER_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    PATH_LENGTH_FIELD_NUMBER: _ClassVar[int]
    CPU_FREQUENCY_MHZ_FIELD_NUMBER: _ClassVar[int]
    CPU_USR_FIELD_NUMBER: _ClassVar[int]
    CPU_NICE_FIELD_NUMBER: _ClassVar[int]
    CPU_SYS_FIELD_NUMBER: _ClassVar[int]
    CPU_IOWAIT_FIELD_NUMBER: _ClassVar[int]
    CPU_STEAL_FIELD_NUMBER: _ClassVar[int]
    CPU_IRQ_FIELD_NUMBER: _ClassVar[int]
    CPU_SOFT_FIELD_NUMBER: _ClassVar[int]
    CPU_GUEST_FIELD_NUMBER: _ClassVar[int]
    CPU_GNICE_FIELD_NUMBER: _ClassVar[int]
    CPU_IDLE_FIELD_NUMBER: _ClassVar[int]
    CPU_UTIL_FIELD_NUMBER: _ClassVar[int]
    KBMEMFREE_FIELD_NUMBER: _ClassVar[int]
    KBAVAIL_FIELD_NUMBER: _ClassVar[int]
    KBMEMUSED_FIELD_NUMBER: _ClassVar[int]
    PERCENT_MEMUSED_FIELD_NUMBER: _ClassVar[int]
    KBBUFFERS_FIELD_NUMBER: _ClassVar[int]
    KBCACHED_FIELD_NUMBER: _ClassVar[int]
    KBCOMMIT_FIELD_NUMBER: _ClassVar[int]
    PERCENT_COMMIT_FIELD_NUMBER: _ClassVar[int]
    KBACTIVE_FIELD_NUMBER: _ClassVar[int]
    KBINACT_FIELD_NUMBER: _ClassVar[int]
    KBDIRTY_FIELD_NUMBER: _ClassVar[int]
    KBANONPG_FIELD_NUMBER: _ClassVar[int]
    KBSLAB_FIELD_NUMBER: _ClassVar[int]
    KBKSTACK_FIELD_NUMBER: _ClassVar[int]
    KBPGTBL_FIELD_NUMBER: _ClassVar[int]
    KBVMUSED_FIELD_NUMBER: _ClassVar[int]
    DEV_FIELD_NUMBER: _ClassVar[int]
    TPS_FIELD_NUMBER: _ClassVar[int]
    RKB_S_FIELD_NUMBER: _ClassVar[int]
    WKB_S_FIELD_NUMBER: _ClassVar[int]
    DKB_S_FIELD_NUMBER: _ClassVar[int]
    AREQ_SZ_FIELD_NUMBER: _ClassVar[int]
    AQU_SZ_FIELD_NUMBER: _ClassVar[int]
    DISK_AWAIT_FIELD_NUMBER: _ClassVar[int]
    PERCENT_DISK_UTIL_FIELD_NUMBER: _ClassVar[int]
    DATA_LOCATION_FIELD_NUMBER: _ClassVar[int]
    HW_INFO_FIELD_NUMBER: _ClassVar[int]
    SW_INFO_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    COMMENT_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    workload: str
    transactions: int
    throughput: float
    used_threads: _containers.RepeatedScalarFieldContainer[int]
    run_time: float
    cycles: int
    instructions: int
    cycles_per_second: float
    instructions_per_second: float
    CPI: float
    cycles_per_requests: float
    path_length: float
    cpu_frequency_mhz: float
    cpu_usr: float
    cpu_nice: float
    cpu_sys: float
    cpu_iowait: float
    cpu_steal: float
    cpu_irq: float
    cpu_soft: float
    cpu_guest: float
    cpu_gnice: float
    cpu_idle: float
    cpu_util: float
    kbmemfree: int
    kbavail: int
    kbmemused: int
    percent_memused: float
    kbbuffers: int
    kbcached: int
    kbcommit: int
    percent_commit: float
    kbactive: int
    kbinact: int
    kbdirty: int
    kbanonpg: int
    kbslab: int
    kbkstack: int
    kbpgtbl: int
    kbvmused: int
    dev: str
    tps: float
    rkB_s: float
    wkB_s: float
    dkB_s: float
    areq_sz: float
    aqu_sz: float
    disk_await: float
    percent_disk_util: float
    data_location: str
    hw_info: str
    sw_info: str
    platform: str
    comment: str
    username: str
    def __init__(
        self,
        workload: _Optional[str] = ...,
        transactions: _Optional[int] = ...,
        throughput: _Optional[float] = ...,
        used_threads: _Optional[_Iterable[int]] = ...,
        run_time: _Optional[float] = ...,
        cycles: _Optional[int] = ...,
        instructions: _Optional[int] = ...,
        cycles_per_second: _Optional[float] = ...,
        instructions_per_second: _Optional[float] = ...,
        CPI: _Optional[float] = ...,
        cycles_per_requests: _Optional[float] = ...,
        path_length: _Optional[float] = ...,
        cpu_frequency_mhz: _Optional[float] = ...,
        cpu_usr: _Optional[float] = ...,
        cpu_nice: _Optional[float] = ...,
        cpu_sys: _Optional[float] = ...,
        cpu_iowait: _Optional[float] = ...,
        cpu_steal: _Optional[float] = ...,
        cpu_irq: _Optional[float] = ...,
        cpu_soft: _Optional[float] = ...,
        cpu_guest: _Optional[float] = ...,
        cpu_gnice: _Optional[float] = ...,
        cpu_idle: _Optional[float] = ...,
        cpu_util: _Optional[float] = ...,
        kbmemfree: _Optional[int] = ...,
        kbavail: _Optional[int] = ...,
        kbmemused: _Optional[int] = ...,
        percent_memused: _Optional[float] = ...,
        kbbuffers: _Optional[int] = ...,
        kbcached: _Optional[int] = ...,
        kbcommit: _Optional[int] = ...,
        percent_commit: _Optional[float] = ...,
        kbactive: _Optional[int] = ...,
        kbinact: _Optional[int] = ...,
        kbdirty: _Optional[int] = ...,
        kbanonpg: _Optional[int] = ...,
        kbslab: _Optional[int] = ...,
        kbkstack: _Optional[int] = ...,
        kbpgtbl: _Optional[int] = ...,
        kbvmused: _Optional[int] = ...,
        dev: _Optional[str] = ...,
        tps: _Optional[float] = ...,
        rkB_s: _Optional[float] = ...,
        wkB_s: _Optional[float] = ...,
        dkB_s: _Optional[float] = ...,
        areq_sz: _Optional[float] = ...,
        aqu_sz: _Optional[float] = ...,
        disk_await: _Optional[float] = ...,
        percent_disk_util: _Optional[float] = ...,
        data_location: _Optional[str] = ...,
        hw_info: _Optional[str] = ...,
        sw_info: _Optional[str] = ...,
        platform: _Optional[str] = ...,
        comment: _Optional[str] = ...,
        username: _Optional[str] = ...,
    ) -> None: ...

class DeployResp(_message.Message):
    __slots__ = (
        "message",
        "username",
        "time",
        "hash",
        "upload_datetime",
        "status_code",
    )
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_DATETIME_FIELD_NUMBER: _ClassVar[int]
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    message: str
    username: str
    time: str
    hash: str
    upload_datetime: str
    status_code: int
    def __init__(
        self,
        message: _Optional[str] = ...,
        username: _Optional[str] = ...,
        time: _Optional[str] = ...,
        hash: _Optional[str] = ...,
        upload_datetime: _Optional[str] = ...,
        status_code: _Optional[int] = ...,
    ) -> None: ...

class DownloadFullTableRequest(_message.Message):
    __slots__ = ("pipad_ip_addr", "pipad_port", "table_name", "file_option")
    PIPAD_IP_ADDR_FIELD_NUMBER: _ClassVar[int]
    PIPAD_PORT_FIELD_NUMBER: _ClassVar[int]
    TABLE_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_OPTION_FIELD_NUMBER: _ClassVar[int]
    pipad_ip_addr: str
    pipad_port: int
    table_name: str
    file_option: str
    def __init__(
        self,
        pipad_ip_addr: _Optional[str] = ...,
        pipad_port: _Optional[int] = ...,
        table_name: _Optional[str] = ...,
        file_option: _Optional[str] = ...,
    ) -> None: ...

class DownloadFullTableResp(_message.Message):
    __slots__ = ("file_content",)
    FILE_CONTENT_FIELD_NUMBER: _ClassVar[int]
    file_content: bytes
    def __init__(self, file_content: _Optional[bytes] = ...) -> None: ...
