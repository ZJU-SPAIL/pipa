export DESCRIPTION="Huawei BoostKit Official Baseline (Guide V12)"

# --- 关键配置：内存与日志 (指南 P23) ---
export MYSQL_BUFF_POOL="32G"       # 鲲鹏大内存优势
export MYSQL_LOG_SIZE="4G"         # 维持你原有的大日志策略

# --- 关键配置：解除 I/O 枷锁 (指南 P24) ---
export INNODB_FLUSH_METHOD="O_DIRECT"
# 华为指南未强制要求双一，为了跑分通常宽松处理，或者根据你要测的场景定
export INNODB_FLUSH_TRX="0"
export INNODB_SYNC_BINLOG="0"

# --- [重点] 鲲鹏架构特化参数 (指南 P24 表6-1) ---
# 这是 x86 上没有的优化，必须显式配置！
# export INNODB_SPIN_WAIT_DELAY=20
# export INNODB_SYNC_SPIN_LOOPS=25       # 指南写的是 innodb_sync_spin_loops=25
# export INNODB_SPIN_WAIT_PAUSE_MULTIPLIER=50

# --- 资源绑定 (指南 P13) ---
# 建议：DB 绑 Node 0-1, Sysbench 绑 Node 2-3
export MYSQL_CPU_AFFINITY="0-63"
export SYSBENCH_CPU_AFFINITY="64-95"
export SYSBENCH_THREADS=32
