# Profile: Concurrent Congestion (NUMA Imbalance + Queue Buildup)
export DESCRIPTION="Scenario: High concurrency reading across NUMA nodes."
export MYSQL_BUFF_POOL="2G"
export INNODB_FLUSH_METHOD="O_DIRECT"
export MYSQL_MAX_CONNECTIONS="4000" # 高并发需要更多连接

# 显式制造冲突：
# MySQL 绑定在 0-63
# Sysbench 绑定在 64-127
# 这样 Sysbench (Node 2-3) 访问 MySQL (Node 0-1) 必须跨 NUMA 访问内存
export MYSQL_CPU_AFFINITY="0-63"
export SYSBENCH_CPU_AFFINITY="64-127"

export SYSBENCH_THREADS=1024       # 1024 线程轰炸
export SYSBENCH_LUA="oltp_read_only"
