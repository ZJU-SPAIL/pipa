class sadf:
    """sadf 数据模型基类，封装所有监控指标的表头结构"""

    class CpuUsage:
        """CPU 使用率统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC）
        cpu: str  # CPU 编号（-1 表示总计）
        user_percent: float  # 用户态使用率 (%usr)
        nice_percent: float  # Nice 进程使用率 (%nice)
        system_percent: float  # 内核态使用率 (%sys)
        iowait_percent: float  # I/O 等待时间 (%iowait)
        steal_percent: float  # 被其他虚拟机偷走的时间 (%steal)
        irq_percent: float  # 硬中断时间 (%irq)
        soft_percent: float  # 软中断时间 (%soft)
        guest_percent: float  # 虚拟机运行时间 (%guest)
        gnice_percent: float  # 调整过优先级的虚拟机时间 (%gnice)
        idle_percent: float  # 空闲时间 (%idle)

    class ProcessStats:
        """进程与上下文切换统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC）
        processes_per_second: float  # 每秒进程调度数 (proc/s)
        context_switches_per_second: float  # 每秒上下文切换次数 (cswch/s)

    class Interrupts:
        """中断统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC）
        interrupt_id: str  # 中断编号 (INTR)
        interrupts_per_second: float  # 每秒中断次数 (intr/s)

    class SwapStats:
        """交换分区统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        pswpin_per_second: float  # 每秒从交换区读取页数 (pswpin/s)
        pswpout_per_second: float  # 每秒写入交换区页数 (pswpout/s)

    class MemoryPageStats:
        """内存页统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        pgpgin_per_second: float  # 每秒从磁盘读取页数 (pgpgin/s)
        pgpgout_per_second: float  # 每秒写入磁盘页数 (pgpgout/s)
        faults_per_second: float  # 每秒页面错误数 (fault/s)
        majflt_per_second: float  # 每秒重大页面错误数 (majflt/s)
        pgfree_per_second: float  # 每秒释放页数 (pgfree/s)
        pgscank_per_second: float  # 每秒扫描页数 (pgscank/s)
        pgscand_per_second: float  # 每秒直接扫描页数 (pgscand/s)
        pgsteal_per_second: float  # 每秒偷取页数 (pgsteal/s)
        vmeff_percent: float  # 虚拟内存效率 (%vmeff)

    class DiskIoStats:
        """磁盘 I/O 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        tps: float  # 每秒传输次数 (tps)
        rtps: float  # 每秒读取次数 (rtps)
        wtps: float  # 每秒写入次数 (wtps)
        dtps: float  # 每秒删除次数 (dtps)
        bread_per_second: float  # 每秒读取块数 (bread/s)
        bwrtn_per_second: float  # 每秒写入块数 (bwrtn/s)
        bdscd_per_second: float  # 每秒丢弃块数 (bdscd/s)

    class MemoryUsage:
        """内存使用统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        kbmemfree: int  # 空闲内存大小 (kbmemfree)
        kbavail: int  # 可用内存大小 (kbavail)
        kbmemused: int  # 已用内存大小 (kbmemused)
        memused_percent: float  # 内存使用率 (%memused)
        kbbuffers: int  # 缓冲区大小 (kbbuffers)
        kbcached: int  # 缓存大小 (kbcached)
        kbcommit: int  # 提交的内存量 (kbcommit)
        commit_percent: float  # 提交内存使用率 (%commit)
        kbactive: int  # 活跃内存大小 (kbactive)
        kbinact: int  # 非活跃内存大小 (kbinact)
        kbdirty: int  # 脏页大小 (kbdirty)
        kbanonpg: int  # 匿名页大小 (kbanonpg)
        kbslab: int  # Slab 分配器大小 (kbslab)
        kbkstack: int  # 内核栈大小 (kbkstack)
        kbpgtbl: int  # 页表大小 (kbpgtbl)
        kbvmused: int  # 虚拟内存使用量 (kbvmused)

    class SwapUsage:
        """交换分区使用统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        kbswpfree: int  # 空闲交换分区大小 (kbswpfree)
        kbswpused: int  # 已用交换分区大小 (kbswpused)
        swpused_percent: float  # 交换分区使用率 (%swpused)
        kbswpcad: int  # 压缩交换分区大小 (kbswpcad)
        swpcad_percent: float  # 压缩交换分区使用率 (%swpcad)

    class HugePages:
        """大页内存统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        kbhugfree: int  # 空闲大页内存大小 (kbhugfree)
        kbhugused: int  # 已用大页内存大小 (kbhugused)
        hugused_percent: float  # 大页内存使用率 (%hugused)
        kbhugrsvd: int  # 预留大页内存大小 (kbhugrsvd)
        kbhugsurp: int  # 超出预留的大页内存大小 (kbhugsurp)

    class FileDescriptors:
        """文件描述符统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        dentunusd: int  # 未使用的目录项 (dentunusd)
        file_nr: int  # 文件描述符总数 (file-nr)
        inode_nr: int  # inode 数量 (inode-nr)
        pty_nr: int  # 伪终端数量 (pty-nr)

    class LoadAverage:
        """系统负载统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        runq_sz: int  # 运行队列长度 (runq-sz)
        plist_sz: int  # 进程列表大小 (plist-sz)
        ldavg_1: float  # 1 分钟负载平均值 (ldavg-1)
        ldavg_5: float  # 5 分钟负载平均值 (ldavg-5)
        ldavg_15: float  # 15 分钟负载平均值 (ldavg-15)
        blocked: int  # 被阻塞的进程数 (blocked)

    class DiskDeviceStats:
        """磁盘设备统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        dev: str  # 设备名称 (DEV)
        tps: float  # 每秒传输次数 (tps)
        rkB_per_second: float  # 每秒读取千字节数 (rkB/s)
        wkB_per_second: float  # 每秒写入千字节数 (wkB/s)
        dkB_per_second: float  # 每秒删除千字节数 (dkB/s)
        areq_sz: float  # 平均请求大小 (areq-sz)
        aqu_sz: float  # 平均队列长度 (aqu-sz)
        await_time: float  # 平均等待时间 (await)
        util_percent: float  # 设备利用率 (%util)

    class NetworkInterfaceStats:
        """网络接口统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        iface: str  # 接口名称 (IFACE)
        rxpck_per_second: float  # 每秒接收数据包数 (rxpck/s)
        txpck_per_second: float  # 每秒发送数据包数 (txpck/s)
        rxkB_per_second: float  # 每秒接收千字节数 (rxkB/s)
        txkB_per_second: float  # 每秒发送千字节数 (txkB/s)
        rxcmp_per_second: float  # 每秒接收压缩包数 (rxcmp/s)
        txcmp_per_second: float  # 每秒发送压缩包数 (txcmp/s)
        rxmcst_per_second: float  # 每秒接收多播包数 (rxmcst/s)
        ifutil_percent: float  # 接口利用率 (%ifutil)

    class NetworkErrors:
        """网络错误统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        iface: str  # 接口名称 (IFACE)
        rxerr_per_second: float  # 每秒接收错误数 (rxerr/s)
        txerr_per_second: float  # 每秒发送错误数 (txerr/s)
        coll_per_second: float  # 每秒冲突数 (coll/s)
        rxdrop_per_second: float  # 每秒接收丢弃数 (rxdrop/s)
        txdrop_per_second: float  # 每秒发送丢弃数 (txdrop/s)
        txcarr_per_second: float  # 每秒发送载波错误数 (txcarr/s)
        rxfram_per_second: float  # 每秒接收帧错误数 (rxfram/s)
        rxfifo_per_second: float  # 每秒接收 FIFO 错误数 (rxfifo/s)
        txfifo_per_second: float  # 每秒发送 FIFO 错误数 (txfifo/s)

    class NfsStats:
        """NFS 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        call_per_second: float  # 每秒调用次数 (call/s)
        retrans_per_second: float  # 每秒重传次数 (retrans/s)
        read_per_second: float  # 每秒读取次数 (read/s)
        write_per_second: float  # 每秒写入次数 (write/s)
        access_per_second: float  # 每秒访问次数 (access/s)
        getatt_per_second: float  # 每秒获取属性次数 (getatt/s)

    class SocketsStats:
        """套接字统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        scall_per_second: float  # 每秒系统调用次数 (scall/s)
        badcall_per_second: float  # 每秒错误调用次数 (badcall/s)
        packet_per_second: float  # 每秒数据包数 (packet/s)
        udp_per_second: float  # 每秒 UDP 包数 (udp/s)
        tcp_per_second: float  # 每秒 TCP 包数 (tcp/s)
        hit_per_second: float  # 每秒命中次数 (hit/s)
        miss_per_second: float  # 每秒未命中次数 (miss/s)
        sread_per_second: float  # 每秒读取次数 (sread/s)
        swrite_per_second: float  # 每秒写入次数 (swrite/s)
        saccess_per_second: float  # 每秒访问次数 (saccess/s)
        sgetatt_per_second: float  # 每秒获取属性次数 (sgetatt/s)

    class TcpUdpStats:
        """TCP/UDP 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        totsck: int  # 总套接字数 (totsck)
        tcpsck: int  # TCP 套接字数 (tcpsck)
        udpsck: int  # UDP 套接字数 (udpsck)
        rawsck: int  # RAW 套接字数 (rawsck)
        ip_frag: int  # IP 分片数 (ip-frag)
        tcp_tw: int  # TCP TIME-WAIT 状态数 (tcp-tw)

    class IcmpStats:
        """ICMP 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        irec_per_second: float  # 每秒接收 ICMP 包数 (irec/s)
        fwddgm_per_second: float  # 每秒转发数据报数 (fwddgm/s)
        idel_per_second: float  # 每秒删除数据报数 (idel/s)
        orq_per_second: float  # 每秒输出请求数 (orq/s)
        asmrq_per_second: float  # 每秒组装请求数 (asmrq/s)
        asmok_per_second: float  # 每秒成功组装数 (asmok/s)
        fragok_per_second: float  # 每秒成功分片数 (fragok/s)
        fragcrt_per_second: float  # 每秒创建分片数 (fragcrt/s)

    class IcmpErrors:
        """ICMP 错误统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        ihdrerr_per_second: float  # 每秒头部错误数 (ihdrerr/s)
        iadrerr_per_second: float  # 每秒地址错误数 (iadrerr/s)
        iukwnpr_per_second: float  # 每秒未知协议错误数 (iukwnpr/s)
        idisc_per_second: float  # 每秒丢弃数 (idisc/s)
        odisc_per_second: float  # 每秒输出丢弃数 (odisc/s)
        onort_per_second: float  # 每秒无路由错误数 (onort/s)
        asmf_per_second: float  # 每秒组装失败数 (asmf/s)
        fragf_per_second: float  # 每秒分片失败数 (fragf/s)

    class IcmpMessages:
        """ICMP 消息统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        imsg_per_second: float  # 每秒接收消息数 (imsg/s)
        omsg_per_second: float  # 每秒发送消息数 (omsg/s)
        iech_per_second: float  # 每秒接收回声请求数 (iech/s)
        iechr_per_second: float  # 每秒接收回声应答数 (iechr/s)
        oech_per_second: float  # 每秒发送回声请求数 (oech/s)
        oechr_per_second: float  # 每秒发送回声应答数 (oechr/s)
        itm_per_second: float  # 每秒接收时间戳请求数 (itm/s)
        itmr_per_second: float  # 每秒接收时间戳应答数 (itmr/s)
        otm_per_second: float  # 每秒发送时间戳请求数 (otm/s)
        otmr_per_second: float  # 每秒发送时间戳应答数 (otmr/s)
        iadrmk_per_second: float  # 每秒接收地址掩码请求数 (iadrmk/s)
        iadrmkr_per_second: float  # 每秒接收地址掩码应答数 (iadrmkr/s)
        oadrmk_per_second: float  # 每秒发送地址掩码请求数 (oadrmk/s)
        oadrmkr_per_second: float  # 每秒发送地址掩码应答数 (oadrmkr/s)

    class IcmpRedirects:
        """ICMP 重定向统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        ierr_per_second: float  # 每秒错误数 (ierr/s)
        oerr_per_second: float  # 每秒输出错误数 (oerr/s)
        idstunr_per_second: float  # 每秒目标不可达错误数 (idstunr/s)
        odstunr_per_second: float  # 每秒输出目标不可达错误数 (odstunr/s)
        itmex_per_second: float  # 每秒超时错误数 (itmex/s)
        otmex_per_second: float  # 每秒输出超时错误数 (otmex/s)
        iparmpb_per_second: float  # 每秒参数错误数 (iparmpb/s)
        oparmpb_per_second: float  # 每秒输出参数错误数 (oparmpb/s)
        isrcq_per_second: float  # 每秒源抑制请求数 (isrcq/s)
        osrcq_per_second: float  # 每秒输出源抑制请求数 (osrcq/s)
        iredir_per_second: float  # 每秒重定向请求数 (iredir/s)
        oredir_per_second: float  # 每秒输出重定向请求数 (oredir/s)

    class TcpStats:
        """TCP 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        active_per_second: float  # 每秒主动连接数 (active/s)
        passive_per_second: float  # 每秒被动连接数 (passive/s)
        iseg_per_second: float  # 每秒接收段数 (iseg/s)
        oseg_per_second: float  # 每秒发送段数 (oseg/s)

    class TcpErrors:
        """TCP 错误统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        atmptf_per_second: float  # 每秒尝试失败连接数 (atmptf/s)
        estres_per_second: float  # 每秒建立连接数 (estres/s)
        retrans_per_second: float  # 每秒重传次数 (retrans/s)
        isegerr_per_second: float  # 每秒接收错误段数 (isegerr/s)
        orsts_per_second: float  # 每秒输出重置数 (orsts/s)

    class UdpStats:
        """UDP 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        idgm_per_second: float  # 每秒接收数据报数 (idgm/s)
        odgm_per_second: float  # 每秒发送数据报数 (odgm/s)
        noport_per_second: float  # 每秒无端口数据报数 (noport/s)
        idgmerr_per_second: float  # 每秒接收错误数据报数 (idgmerr/s)

    class IPv6Stats:
        """IPv6 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        tcp6sck: int  # IPv6 TCP 套接字数 (tcp6sck)
        udp6sck: int  # IPv6 UDP 套接字数 (udp6sck)
        raw6sck: int  # IPv6 RAW 套接字数 (raw6sck)
        ip6_frag: int  # IPv6 分片数 (ip6-frag)

    class IPv6IcmpStats:
        """IPv6 ICMP 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        irec6_per_second: float  # 每秒接收 ICMPv6 包数 (irec6/s)
        fwddgm6_per_second: float  # 每秒转发数据报数 (fwddgm6/s)
        idel6_per_second: float  # 每秒删除数据报数 (idel6/s)
        orq6_per_second: float  # 每秒输出请求数 (orq6/s)
        asmrq6_per_second: float  # 每秒组装请求数 (asmrq6/s)
        asmok6_per_second: float  # 每秒成功组装数 (asmok6/s)
        imcpck6_per_second: float  # 每秒接收 MIB ICMP 包数 (imcpck6/s)
        omcpck6_per_second: float  # 每秒发送 MIB ICMP 包数 (omcpck6/s)
        fragok6_per_second: float  # 每秒成功分片数 (fragok6/s)
        fragcr6_per_second: float  # 每秒创建分片数 (fragcr6/s)

    class IPv6IcmpErrors:
        """IPv6 ICMP 错误统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        ihdrer6_per_second: float  # 每秒头部错误数 (ihdrer6/s)
        iadrer6_per_second: float  # 每秒地址错误数 (iadrer6/s)
        iukwnp6_per_second: float  # 每秒未知协议错误数 (iukwnp6/s)
        i2big6_per_second: float  # 每秒过大包错误数 (i2big6/s)
        idisc6_per_second: float  # 每秒丢弃数 (idisc6/s)
        odisc6_per_second: float  # 每秒输出丢弃数 (odisc6/s)
        inort6_per_second: float  # 每秒无路由错误数 (inort6/s)
        onort6_per_second: float  # 每秒输出无路由错误数 (onort6/s)
        asmf6_per_second: float  # 每秒组装失败数 (asmf6/s)
        fragf6_per_second: float  # 每秒分片失败数 (fragf6/s)
        itrpck6_per_second: float  # 每秒陷阱包数 (itrpck6/s)

    class IPv6IcmpMessages:
        """IPv6 ICMP 消息统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        imsg6_per_second: float  # 每秒接收消息数 (imsg6/s)
        omsg6_per_second: float  # 每秒发送消息数 (omsg6/s)
        iech6_per_second: float  # 每秒接收回声请求数 (iech6/s)
        iechr6_per_second: float  # 每秒接收回声应答数 (iechr6/s)
        oechr6_per_second: float  # 每秒发送回声应答数 (oechr6/s)
        igmbq6_per_second: float  # 每秒接收组播查询数 (igmbq6/s)
        igmbr6_per_second: float  # 每秒接收组播报告数 (igmbr6/s)
        ogmbr6_per_second: float  # 每秒发送组播报告数 (ogmbr6/s)
        igmbrd6_per_second: float  # 每秒接收组播离开数 (igmbrd6/s)
        ogmbrd6_per_second: float  # 每秒发送组播离开数 (ogmbrd6/s)
        irtsol6_per_second: float  # 每秒接收路由器求解数 (irtsol6/s)
        ortsol6_per_second: float  # 每秒发送路由器求解数 (ortsol6/s)
        irtad6_per_second: float  # 每秒接收路由器通告数 (irtad6/s)
        inbsol6_per_second: float  # 每秒接收邻居求解数 (inbsol6/s)
        onbsol6_per_second: float  # 每秒发送邻居求解数 (onbsol6/s)
        inbad6_per_second: float  # 每秒接收邻居通告数 (inbad6/s)
        onbad6_per_second: float  # 每秒发送邻居通告数 (onbad6/s)

    class IPv6IcmpRedirects:
        """IPv6 ICMP 重定向统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        ierr6_per_second: float  # 每秒错误数 (ierr6/s)
        idtunr6_per_second: float  # 每秒目标不可达错误数 (idtunr6/s)
        odtunr6_per_second: float  # 每秒输出目标不可达错误数 (odtunr6/s)
        itmex6_per_second: float  # 每秒超时错误数 (itmex6/s)
        otmex6_per_second: float  # 每秒输出超时错误数 (otmex6/s)
        iprmpb6_per_second: float  # 每秒参数错误数 (iprmpb6/s)
        oprmpb6_per_second: float  # 每秒输出参数错误数 (oprmpb6/s)
        iredir6_per_second: float  # 每秒重定向请求数 (iredir6/s)
        oredir6_per_second: float  # 每秒输出重定向请求数 (oredir6/s)
        ipck2b6_per_second: float  # 每秒包过大错误数 (ipck2b6/s)
        opck2b6_per_second: float  # 每秒输出包过大错误数 (opck2b6/s)

    class IPv6UdpStats:
        """IPv6 UDP 统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        idgm6_per_second: float  # 每秒接收数据报数 (idgm6/s)
        odgm6_per_second: float  # 每秒发送数据报数 (odgm6/s)
        noport6_per_second: float  # 每秒无端口数据报数 (noport6/s)
        idgmer6_per_second: float  # 每秒接收错误数据报数 (idgmer6/s)

    class CpuFrequency:
        """CPU 频率统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        cpu: str  # CPU 编号 (CPU)
        mhz: float  # CPU 当前频率 (MHz)

    class CpuTemperature:
        """CPU 温度统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        temp: str  # 温度编号 (TEMP)
        device: str  # 温度传感器设备 (DEVICE)
        degc: float  # 温度 (degC)
        temp_percent: float  # 温度百分比 (%temp)

    class UsbDevices:
        """USB 设备统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        manufact: str  # 制造商 (manufact)
        product: str  # 产品 (product)
        bus: str  # 总线 (BUS)
        idvendor: str  # 供应商 ID (idvendor)
        idprod: str  # 产品 ID (idprod)
        maxpower: str  # 最大功率 (maxpower)

    class FilesystemUsage:
        """文件系统使用统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        filesystem: str  # 文件系统 (FILESYSTEM)
        mbfsfree: int  # 空闲空间大小 (MBfsfree)
        mbfsused: int  # 已用空间大小 (MBfsused)
        fsused_percent: float  # 空间使用率 (%fsused)
        ufsused_percent: float  # 用户空间使用率 (%ufsused)
        ifree: int  # 空闲 inode 数 (Ifree)
        iused: int  # 已用 inode 数 (Iused)
        iused_percent: float  # inode 使用率 (%Iused)

    class CpuQueueStats:
        """CPU 队列统计"""

        hostname: str  # 主机名
        interval: str  # 监控间隔时间（秒）
        timestamp: str  # 时间戳（UTC)
        cpu: str  # CPU 编号 (CPU)
        total_per_second: float  # 每秒总流量 (total/s)
        dropd_per_second: float  # 每秒丢包数 (dropd/s)
        squeezd_per_second: float  # 每秒压缩包数 (squeezd/s)
        rx_rps_per_second: float  # 每秒 RPS 接收数 (rx_rps/s)
        flw_lim_per_second: float  # 每秒流量限制数 (flw_lim/s)


def parse_sadf_data(file_path):
    """
    解析 sadf 生成的文本数据，返回结构化的字典列表。

    Args:
        file_path (str): 要解析的文件路径。

    Returns:
        list: 每个元素是一个字典，包含 'header'（表头）和 'rows'（数据行）。
    """
    result = []
    current_block = None

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 判断是否为表头行（以 # 开头）
            if line.startswith("#"):
                if current_block:
                    result.append(current_block)  # 保存上一个数据块
                # 提取表头字段
                header = [field.strip() for field in line[1:].split(";")]
                current_block = {"header": header, "rows": []}
            else:
                # 解析数据行
                fields = [field.strip() for field in line.split(";")]
                if len(fields) != len(current_block["header"]):
                    raise ValueError(
                        f"字段数不匹配: 表头有 {len(current_block['header'])} 字段，数据行有 {len(fields)} 字段"
                    )
                current_block["rows"].append(dict(zip(current_block["header"], fields)))

        # 添加最后一个块
        if current_block:
            result.append(current_block)

    return result


if __name__ == "__main__":
    data_blocks = parse_sadf_data("sadf.csv")

    for block in data_blocks:
        print("表头:", block["header"])
        print("前3行数据:")
        for row in block["rows"][:3]:
            print(row)
        print("\n---")

    print(len(data_blocks))  # 输出数据块的数量
