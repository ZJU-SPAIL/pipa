export PROFILE_NAME="wrk_long"
export TOOL="wrk"
export MODE="long"

# --- 华为官方调优参数引用 ---
# [引用依据] 《Nginx 移植&调优指南》
# 1. 3.4.4 keepalive_requests 优化 (Page 61):
#    "keepalive_requests参数限制了一个长连接最多可以处理完成的最大请求数... 建议设置为 20000"
export KEEPALIVE_REQUESTS=20000

# 2. 3.4.6 Nginx 配置示例 (Page 62):
#    示例中 keepalive_timeout 设置为 65
export KEEPALIVE_TIMEOUT=65
