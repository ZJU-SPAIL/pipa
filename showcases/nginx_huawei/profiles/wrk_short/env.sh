export PROFILE_NAME="wrk_short"
export TOOL="wrk"
export MODE="short"

# --- 华为官方调优参数引用 ---
# [引用依据] 《Nginx 移植&调优指南》
# 1. 3.4.2 配置 Nginx 应用绑核 (Page 59-60):
#    表 3-5 列举了 HTTP 短连接场景下的最佳绑核比例 (Nginx:中断 = 1:1 或 2:1)
#    (本脚本在 run_load.sh 中通过 taskset 实现物理隔离，符合此原则)

# 2. 短连接特性配置:
#    短连接场景下，不仅不需要 keepalive，反而需要尽快释放连接以应对高并发握手。
#    虽然指南未显式规定设为 0，但这是业界标准做法，且不违反指南关于长连接的建议。
export KEEPALIVE_REQUESTS=100  # 默认值，不强制长连接
export KEEPALIVE_TIMEOUT=0     # 强制关闭 Keepalive，模拟真实短连接
