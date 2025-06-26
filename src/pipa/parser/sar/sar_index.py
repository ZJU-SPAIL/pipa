from enum import Enum, unique
from typing import Optional


@unique
class SarDataIndex(Enum):
    Timestamp = "timestamp"
    Average = "Average:"
    CPUUtilsMetrics = {
        r"%usr": "float64",
        r"%nice": "float64",
        r"%sys": "float64",
        r"%iowait": "float64",
        r"%steal": "float64",
        r"%irq": "float64",
        r"%soft": "float64",
        r"%guest": "float64",
        r"%gnice": "float64",
        r"%idle": "float64",
    }
    CPUUtils = [Timestamp, "CPU", *CPUUtilsMetrics.keys()]
    AvgCPUUtils = [Average, "CPU", *CPUUtilsMetrics.keys()]
    CPUPressureStatsMetrics = {
        r"%scpu-10": "float64",
        r"%scpu-60": "float64",
        r"%scpu-300": "float64",
        r"%scpu": "float64",
    }
    CPUPressureStats = [Timestamp, *CPUPressureStatsMetrics.keys()]
    ProcessStatsMetrics = {"proc/s": "float64", "cswch/s": "float64"}
    ProcessStats = [Timestamp, *ProcessStatsMetrics.keys()]
    InterruptStatsMetrics = {"intr/s": "float64"}
    InterruptStats = [Timestamp, "INTR", *InterruptStatsMetrics.keys()]
    AvgInterruptStats = [Average, "INTR", *InterruptStatsMetrics.keys()]
    SwapStatsMetrics = {"pswpin/s": "float64", "pswpout/s": "float64"}
    SwapStats = [Timestamp, *SwapStatsMetrics.keys()]
    PagingStatsMetrics = {
        "pgpgin/s": "float64",
        "pgpgout/s": "float64",
        "fault/s": "float64",
        "majflt/s": "float64",
        "pgfree/s": "float64",
        "pgscank/s": "float64",
        "pgscand/s": "float64",
        "pgsteal/s": "float64",
        r"%vmeff": "float64",
    }
    PagingStats = [Timestamp, *PagingStatsMetrics.keys()]
    DiskIOStatsMetrics = {
        "tps": "float64",
        "rtps": "float64",
        "wtps": "float64",
        "dtps": "float64",
        "bread/s": "float64",
        "bwrtn/s": "float64",
        "bdscd/s": "float64",
    }
    DiskIOStats = [Timestamp, *DiskIOStatsMetrics.keys()]
    MemPressureStatsMetrics = {
        r"%smem-10": "float64",
        r"%smem-60": "float64",
        r"%smem-300": "float64",
        r"%smem": "float64",
        r"%fmem-10": "float64",
        r"%fmem-60": "float64",
        r"%fmem-300": "float64",
        r"%fmem": "float64",
    }
    MemPressureStats = [Timestamp, *MemPressureStatsMetrics.keys()]
    MemoryStatsMetrics = {
        "kbmemfree": "int",
        "kbavail": "int",
        "kbmemused": "int",
        r"%memused": "float64",
        "kbbuffers": "int",
        "kbcached": "int",
        "kbcommit": "int",
        r"%commit": "float64",
        "kbactive": "int",
        "kbinact": "int",
        "kbdirty": "int",
        "kbanonpg": "int",
        "kbslab": "int",
        "kbkstack": "int",
        "kbpgtbl": "int",
        "kbvmused": "int",
    }
    MemoryStats = [Timestamp, *MemoryStatsMetrics.keys()]
    SwapMemoryStatsMetrics = {
        "kbswpfree": "int",
        "kbswpused": "int",
        r"%swpused": "float",
        "kbswpcad": "int",
        r"%swpcad": "float",
    }
    SwapMemoryStats = [Timestamp, *SwapMemoryStatsMetrics.keys()]
    HugePagesStatsMetrics = {
        "kbhugfree": "int",
        "kbhugused": "int",
        r"%hugused": "float64",
        "kbhugrsvd": "int",
        "kbhugsurp": "int",
    }
    HugePagesStats = [Timestamp, *HugePagesStatsMetrics.keys()]
    FileSystemStatsMetrics = {
        "dentunusd": "int",
        "file-nr": "int",
        "inode-nr": "int",
        "pty-nr": "int",
    }
    FileSystemStats = [Timestamp, *FileSystemStatsMetrics.keys()]
    LoadStatsMetrics = {
        "runq-sz": "int",
        "plist-sz": "int",
        "ldavg-1": "float64",
        "ldavg-5": "float64",
        "ldavg-15": "float64",
        "blocked": "int",
    }
    LoadStats = [Timestamp, *LoadStatsMetrics.keys()]
    TTYStatsMetrics = {
        "rcvin/s": "float64",
        "xmtin/s": "float64",
        "framerr/s": "float64",
        "prtyerr/s": "float64",
        "brk/s": "float64",
        "ovrun/s": "float64",
    }
    TTYStats = [Timestamp, "TTY", *TTYStatsMetrics.keys()]
    IOPressureStatsMetrics = {
        r"%sio-10": "float64",
        r"%sio-60": "float64",
        r"%sio-300": "float64",
        r"%sio": "float64",
        r"%fio-10": "float64",
        r"%fio-60": "float64",
        r"%fio-300": "float64",
        r"%fio": "float64",
    }
    IOPressureStats = [Timestamp, *IOPressureStatsMetrics.keys()]
    DeviceIOStatsMetrics = {
        "tps": "float64",
        "rkB/s": "float64",
        "wkB/s": "float64",
        "dkB/s": "float64",
        "areq-sz": "float64",
        "aqu-sz": "float64",
        "await": "float64",
        r"%util": "float64",
    }
    DeviceIOStats = [Timestamp, "DEV", *DeviceIOStatsMetrics.keys()]
    NetUtilsMetrics = {
        "rxpck/s": "float64",
        "txpck/s": "float64",
        "rxkB/s": "float64",
        "txkB/s": "float64",
        "rxcmp/s": "float64",
        "txcmp/s": "float64",
        "rxmcst/s": "float64",
        r"%ifutil": "float64",
    }
    NetUtils = [Timestamp, "IFACE", *NetUtilsMetrics.keys()]
    NetErrorMetrics = {
        "rxerr/s": "float64",
        "txerr/s": "float64",
        "coll/s": "float64",
        "rxdrop/s": "float64",
        "txdrop/s": "float64",
        "txcarr/s": "float64",
        "rxfram/s": "float64",
        "rxfifo/s": "float64",
        "txfifo/s": "float64",
    }
    NetError = [Timestamp, "IFACE", *NetErrorMetrics.keys()]
    NFSClientStatsMetrics = {
        "call/s": "float64",
        "retrans/s": "float64",
        "read/s": "float64",
        "write/s": "float64",
        "access/s": "float64",
        "getatt/s": "float64",
    }
    NFSClientStats = [Timestamp, *NFSClientStatsMetrics.keys()]
    NFSServerStatsMetrics = {
        "scall/s": "float64",
        "badcall/s": "float64",
        "packet/s": "float64",
        "udp/s": "float64",
        "tcp/s": "float64",
        "hit/s": "float64",
        "miss/s": "float64",
        "sread/s": "float64",
        "swrite/s": "float64",
        "saccess/s": "float64",
        "sgetatt/s": "float64",
    }
    NFSServerStats = [Timestamp, *NFSServerStatsMetrics.keys()]
    SocketStatsMetrics = {
        "totsck": "int",
        "tcpsck": "int",
        "udpsck": "int",
        "rawsck": "int",
        "ip-frag": "int",
        "tcp-tw": "int",
    }
    SocketStats = [Timestamp, *SocketStatsMetrics.keys()]
    IPStatsMetrics = {
        "irec/s": "float64",
        "fwddgm/s": "float64",
        "idel/s": "float64",
        "orq/s": "float64",
        "asmrq/s": "float64",
        "asmok/s": "float64",
        "fragok/s": "float64",
        "fragcrt/s": "float64",
    }
    IPStats = [Timestamp, *IPStatsMetrics.keys()]
    IPErrorStatsMetrics = {
        "ihdrerr/s": "float64",
        "iadrerr/s": "float64",
        "iukwnpr/s": "float64",
        "idisc/s": "float64",
        "odisc/s": "float64",
        "onort/s": "float64",
        "asmf/s": "float64",
        "fragf/s": "float64",
    }
    IPErrorStats = [Timestamp, *IPErrorStatsMetrics.keys()]
    ICMPStatsMetrics = {
        "imsg/s": "float64",
        "omsg/s": "float64",
        "iech/s": "float64",
        "iechr/s": "float64",
        "oech/s": "float64",
        "oechr/s": "float64",
        "itm/s": "float64",
        "itmr/s": "float64",
        "otm/s": "float64",
        "otmr/s": "float64",
        "iadrmk/s": "float64",
        "iadrmkr/s": "float64",
        "oadrmk/s": "float64",
        "oadrmkr/s": "float64",
    }
    ICMPStats = [Timestamp, *ICMPStatsMetrics.keys()]
    ICMPErrorStatsMetrics = {
        "ierr/s": "float64",
        "oerr/s": "float64",
        "idstunr/s": "float64",
        "odstunr/s": "float64",
        "itmex/s": "float64",
        "otmex/s": "float64",
        "iparmpb/s": "float64",
        "oparmpb/s": "float64",
        "isrcq/s": "float64",
        "osrcq/s": "float64",
        "iredir/s": "float64",
        "oredir/s": "float64",
    }
    ICMPErrorStats = [Timestamp, *ICMPErrorStatsMetrics.keys()]
    TCPStatsMetrics = {
        "active/s": "float64",
        "passive/s": "float64",
        "iseg/s": "float64",
        "oseg/s": "float64",
    }
    TCPStats = [Timestamp, *TCPStatsMetrics.keys()]
    TCPExtStatsMetrics = {
        "atmptf/s": "float64",
        "estres/s": "float64",
        "retrans/s": "float64",
        "isegerr/s": "float64",
        "orsts/s": "float64",
    }
    TCPExtStats = [Timestamp, *TCPExtStatsMetrics.keys()]
    UDPStatsMetrics = {
        "idgm/s": "float64",
        "odgm/s": "float64",
        "noport/s": "float64",
        "idgmerr/s": "float64",
    }
    UDPStats = [Timestamp, *UDPStatsMetrics.keys()]
    IPv6SocketStatsMetrics = {
        "tcp6sck": "float64",
        "udp6sck": "float64",
        "raw6sck": "float64",
        "ip6-frag": "float64",
    }
    IPv6SocketStats = [Timestamp, *IPv6SocketStatsMetrics.keys()]
    IPv6StatsMetrics = {
        "irec6/s": "float64",
        "fwddgm6/s": "float64",
        "idel6/s": "float64",
        "orq6/s": "float64",
        "asmrq6/s": "float64",
        "asmok6/s": "float64",
        "imcpck6/s": "float64",
        "omcpck6/s": "float64",
        "fragok6/s": "float64",
        "fragcr6/s": "float64",
    }
    IPv6Stats = [Timestamp, *IPv6StatsMetrics.keys()]
    IPv6ErrorStatsMetrics = {
        "ihdrer6/s": "float64",
        "iadrer6/s": "float64",
        "iukwnp6/s": "float64",
        "i2big6/s": "float64",
        "idisc6/s": "float64",
        "odisc6/s": "float64",
        "inort6/s": "float64",
        "onort6/s": "float64",
        "asmf6/s": "float64",
        "fragf6/s": "float64",
        "itrpck6/s": "float64",
    }
    IPv6ErrorStats = [Timestamp, *IPv6ErrorStatsMetrics.keys()]
    ICMPv6StatsMetrics = {
        "imsg6/s": "float64",
        "omsg6/s": "float64",
        "iech6/s": "float64",
        "iechr6/s": "float64",
        "oechr6/s": "float64",
        "igmbq6/s": "float64",
        "igmbr6/s": "float64",
        "ogmbr6/s": "float64",
        "igmbrd6/s": "float64",
        "ogmbrd6/s": "float64",
        "irtsol6/s": "float64",
        "ortsol6/s": "float64",
        "irtad6/s": "float64",
        "inbsol6/s": "float64",
        "onbsol6/s": "float64",
        "inbad6/s": "float64",
        "onbad6/s": "float64",
    }
    ICMPv6Stats = [Timestamp, *ICMPv6StatsMetrics.keys()]
    ICMPv6ErrorStatsMetrics = {
        "ierr6/s": "float64",
        "idtunr6/s": "float64",
        "odtunr6/s": "float64",
        "itmex6/s": "float64",
        "otmex6/s": "float64",
        "iprmpb6/s": "float64",
        "oprmpb6/s": "float64",
        "iredir6/s": "float64",
        "oredir6/s": "float64",
        "ipck2b6/s": "float64",
        "opck2b6/s": "float64",
    }
    ICMPv6ErrorStats = [Timestamp, *ICMPv6ErrorStatsMetrics.keys()]
    UDPv6StatsMetrics = {
        "idgm6/s": "float64",
        "odgm6/s": "float64",
        "noport6/s": "float64",
        "idgmer6/s": "float64",
    }
    UDPv6Stats = [Timestamp, *UDPv6StatsMetrics.keys()]
    SoftNetStatsMetrics = {
        "total/s": "float64",
        "dropd/s": "float64",
        "squeezd/s": "float64",
        "rx_rps/s": "float64",
        "flw_lim/s": "float64",
    }
    SoftNetStats = [Timestamp, "CPU", *SoftNetStatsMetrics.keys()]
    AvgSoftNetStats = [Average, "CPU", *SoftNetStatsMetrics.keys()]
    CPUFreqMetrics = {"MHz": "float64"}
    CPUFreq = [Timestamp, "CPU", *CPUFreqMetrics.keys()]
    AvgCPUFreq = [Average, "CPU", *CPUFreqMetrics.keys()]
    TemperatureStatsMetrics = {"degC": "float64", r"%temp": "float64"}
    TemperatureStats = [Timestamp, "TEMP", *TemperatureStatsMetrics.keys(), "DEVICE"]
    BusStatsMetrics = {"maxpower": "int"}
    BusStats = [
        Timestamp,
        "BUS",
        "idvendor",
        "idprod",
        *BusStatsMetrics.keys(),
        "manufact",
        "product",
    ]
    FileSystemSpaceStatsMetrics = {
        "MBfsfree": "int",
        "MBfsused": "int",
        r"%fsused": "float64",
        r"%ufsused": "float64",
        "Ifree": "int",
        "Iused": "int",
        r"%Iused": "float64",
    }
    FileSystemSpaceStats = [
        Timestamp,
        *FileSystemSpaceStatsMetrics.keys(),
        "FILESYSTEM",
    ]

    @classmethod
    def contains(cls, item) -> Optional[Enum]:
        for k in cls:
            if item == k.value:
                return k
        return None

    @classmethod
    def avg_metric_to_all_metric(cls, item: Enum) -> Optional[Enum]:
        if item.name.startswith("Avg"):
            try:
                n = item.name.replace("Avg", "")
                return cls.__getitem__(n)
            except Exception:
                return None
        return None

    def __eq__(self, value: object) -> bool:
        return self.value == value

    def __hash__(self) -> int:
        return hash(self.name)
