# Profile: Sync IO Blocking (内存受限 + 强刷盘)
export DESCRIPTION="Scenario: Low memory + ACID compliance causing IO blocking."
export MYSQL_BUFF_POOL="128M"
export INNODB_FLUSH_TRX="1"
export INNODB_SYNC_BINLOG="1"
export MYSQL_MAX_CONNECTIONS="500"

# 此场景不侧重 NUMA，但为了严谨，我们依然显式隔离
# 由于是低并发，给少点核也没关系，但为了变量控制，保持一致
export MYSQL_CPU_AFFINITY="0-63"
export SYSBENCH_CPU_AFFINITY="64-127"

export SYSBENCH_THREADS=16         # 低并发
export SYSBENCH_LUA="oltp_read_write"
