export PROFILE_NAME="httpress_long"
export TOOL="httpress"
export MODE="long"

# --- 华为官方调优参数引用 ---
# [引用依据] 《Nginx 移植&调优指南》
# 1. 3.4.4 keepalive_requests 优化 (Page 61):
#    "建议设置为 20000" 以避免重复建立连接
export KEEPALIVE_REQUESTS=20000

# 2. 3.4.6 配置示例 (Page 62):
#    keepalive_timeout 65
export KEEPALIVE_TIMEOUT=65
