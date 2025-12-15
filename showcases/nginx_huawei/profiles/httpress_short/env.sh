export PROFILE_NAME="httpress_short"
export TOOL="httpress"
export MODE="short"

# --- 华为官方调优参数引用 ---
# [引用依据] 《Nginx 移植&调优指南》
# 1. 3.4.6 Nginx 配置示例 (Page 62):
#    该示例展示了 HTTP 短连接场景下的基础配置框架。
#    在此场景下，我们侧重于测试每秒新建连接数 (CPS)，故关闭长连接保持。

export KEEPALIVE_REQUESTS=100
export KEEPALIVE_TIMEOUT=0
