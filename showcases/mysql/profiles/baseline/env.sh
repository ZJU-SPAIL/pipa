# Profile: Baseline (高性能基准 - 狂暴模式)
export DESCRIPTION="Baseline: MAX Performance. Relaxed ACID, Big Memory, Big Logs."

# --- 关键配置：内存与日志 ---
export MYSQL_BUFF_POOL="16G"       # 给足内存！数据才 1.2G，这足够完全缓存
export MYSQL_IO_CAPACITY="20000"   # 告诉 MySQL 磁盘很快，别流控

# --- 关键配置：解除 I/O 枷锁 (非双一) ---
export INNODB_FLUSH_TRX="0"        # 0: 每秒刷一次 (性能最好，崩溃丢1秒数据)
export INNODB_SYNC_BINLOG="0"      # 0: 操作系统决定何时刷 (性能起飞)
export INNODB_FLUSH_METHOD="O_DIRECT"

# --- 资源绑定 ---
export MYSQL_MAX_CONNECTIONS="4000"
# MySQL 占前 64 核
export MYSQL_CPU_AFFINITY="0-63"
# Sysbench 占后 64 核
export SYSBENCH_CPU_AFFINITY="64-127"

# --- 压测负载 ---
export SYSBENCH_THREADS=128        # 加大并发，喂饱 64 个核
export SYSBENCH_LUA="oltp_read_write"
