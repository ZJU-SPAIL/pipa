# Pipa 配置变量系统

## 概述

Pipa 的配置加载器现在支持类似 Dockerfile 的变量声明系统，实现了真正的"配置即代码"（Configuration as Code）理念。

## 设计理念

### 灵感来源：Dockerfile

借鉴 Dockerfile 的 `ARG` 和 `ENV` 机制：

- **声明式变量**：在配置文件顶部清晰声明所有变量
- **顺序依赖**：后定义的变量可以引用前面已定义的变量
- **全局替换**：变量在整个配置文件中可被引用和替换

### 架构优势

1. **DRY 原则**：避免重复定义相同的值
2. **动态适配**：支持 shell 命令，在运行时获取系统信息
3. **可维护性**：集中管理配置变量，易于理解和修改
4. **移植性**：同一配置可在不同环境下自动适配

## 语法说明

### 基本格式

```yaml
variables:
  - VAR_NAME1: value1
  - VAR_NAME2: $(shell_command)
  - VAR_NAME3: ${VAR_NAME1}/subpath
  - VAR_NAME4: $((${VAR_NAME2} * 2))
```

### 支持的语法类型

#### 1. 静态值

```yaml
variables:
  - PROJECT_NAME: mysql_showcase
  - VERSION: 8.0.28
```

#### 2. Shell 命令 `$(command)`

```yaml
variables:
  - NPROC: $(nproc)
  - HOSTNAME: $(hostname)
  - DATE: $(date +%Y%m%d)
```

#### 3. 算术表达式 `$((expression))`

```yaml
variables:
  - TOTAL_CORES: $(nproc)
  - HALF_CORES: $((${TOTAL_CORES} / 2))
  - DOUBLE_CORES: $((${TOTAL_CORES} * 2))
```

#### 4. 变量引用 `${VAR_NAME}`

```yaml
variables:
  - BASE_DIR: /opt/mysql
  - DATA_DIR: ${BASE_DIR}/data
  - LOG_DIR: ${BASE_DIR}/logs
```

#### 5. 复合表达式

```yaml
variables:
  - NPROC: $(nproc)
  - HALF: $((${NPROC} / 2))
  - CPU_RANGE: "0-$((${HALF} - 1))"
  - SECOND_HALF: "${HALF}-$((${NPROC} - 1))"
```

### 变量作用域

变量在 `variables` 块中定义后，可在配置文件的**任何位置**使用：

```yaml
variables:
  - DB_PORT: 3306
  - DB_HOST: localhost

commands:
  start: "mysqld --port=${DB_PORT} --bind-address=${DB_HOST}"

benchmark_driver:
  command_template: "sysbench --mysql-port=${DB_PORT} --mysql-host=${DB_HOST} run"
```

## 解析流程

### 两阶段解析

#### 阶段 1：解析 variables 块

1. **按顺序**处理每个变量定义
2. 对每个变量：
   - 用已解析的变量替换 `${...}` 引用
   - 执行 shell 命令 `$(...)` 和算术表达式 `$((...))`
   - 保存解析结果到变量字典

#### 阶段 2：遍历配置文件

1. 递归遍历配置文件的所有节点
2. 对每个字符串值：
   - 替换所有 `${VAR_NAME}` 为对应的值
   - 执行剩余的 shell 命令（如果有）

### 示例解析过程

**输入配置：**

```yaml
variables:
  - NPROC: $(nproc) # 第1步：执行 nproc，假设得到 24
  - HALF: $((${NPROC} / 2)) # 第2步：替换为 $((24 / 2))，得到 12
  - RANGE: "0-$((${HALF} - 1))" # 第3步：替换为 "0-$((12 - 1))"，得到 "0-11"

command: "taskset -c ${RANGE} echo ${NPROC}"
```

**解析结果：**

```yaml
command: "taskset -c 0-11 echo 24"
```

## 实际应用案例

### MySQL Showcase 配置

```yaml
workload_name: mysql_showcase_dynamic

variables:
  - DYNAMIC_NPROC: $(nproc)
  - DYNAMIC_HALF_PROC: $((${DYNAMIC_NPROC} / 2))
  - DYNAMIC_MYSQL_CPUS: "0-$((${DYNAMIC_HALF_PROC} - 1))"
  - DYNAMIC_SYSBENCH_CPUS: "${DYNAMIC_HALF_PROC}-$((${DYNAMIC_NPROC} - 1))"

commands:
  start: "taskset -c ${DYNAMIC_MYSQL_CPUS} mysqld_safe &"

benchmark_driver:
  intensity_variable:
    max: $((${DYNAMIC_NPROC} * 2))
```

**优势：**

- 在 24 核机器上：MySQL 绑定到 0-11，Sysbench 绑定到 12-23
- 在 128 核机器上：MySQL 绑定到 0-63，Sysbench 绑定到 64-127
- **无需修改配置文件！**

## 与环境变量的协同

Pipa 的变量系统可以与 shell 环境变量无缝配合：

```yaml
# 1. 在 env.sh 中定义环境变量
export MYSQL_INSTALL_DIR="/opt/mysql"
export MYSQL_ROOT_PASSWORD="secret"

# 2. 在 workload.yaml 中同时使用
variables:
  - NPROC: $(nproc)

commands:
  start: "${MYSQL_INSTALL_DIR}/bin/mysqld_safe &"
  stop: "${MYSQL_INSTALL_DIR}/bin/mysqladmin -u root -p${MYSQL_ROOT_PASSWORD} shutdown"

benchmark_driver:
  intensity_variable:
    max: ${NPROC}
```

**工作流：**

```bash
# 1. 加载环境变量
source showcases/mysql/env.sh

# 2. Pipa 加载配置时：
#    - Shell 环境变量（如 ${MYSQL_INSTALL_DIR}）由 shell 展开
#    - Pipa 内部变量（如 ${NPROC}）由 config_loader 解析
```

## 最佳实践

### ✅ 推荐做法

1. **变量命名**：使用大写字母和下划线，如 `DYNAMIC_NPROC`
2. **顺序依赖**：先定义基础变量，再定义依赖它的派生变量
3. **注释说明**：为复杂的变量添加注释说明其用途
4. **类型一致**：保持变量类型的一致性（数字、路径、范围等）

```yaml
variables:
  # 基础系统信息
  - NPROC: $(nproc)

  # CPU 核心分配策略
  - HALF_CORES: $((${NPROC} / 2))
  - SERVICE_CPUS: "0-$((${HALF_CORES} - 1))"
  - BENCHMARK_CPUS: "${HALF_CORES}-$((${NPROC} - 1))"
```

### ❌ 避免的做法

1. **循环依赖**：不要让变量相互引用
2. **过度复杂**：避免在一个变量中嵌套太多层表达式
3. **隐式依赖**：不要假设变量的解析顺序

## 错误处理

### Shell 命令执行失败

如果 shell 命令返回非零状态码，会抛出 `ConfigError`：

```python
ConfigError: 变量 'NPROC' 的 shell 命令执行失败: $(nproc)
错误: Command 'nproc' not found
```

### 变量未定义

引用未定义的变量时，会保持原样（不会报错）：

```yaml
variables:
  - VAR1: hello

command: "${VAR1} ${UNDEFINED_VAR}"
# 结果: "hello ${UNDEFINED_VAR}"
```

## 技术实现

### 核心函数

```python
def _resolve_variables_and_commands(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    两阶段解析器：
    1. 解析 variables 块（顺序依赖）
    2. 遍历配置并替换变量
    """
```

### 关键特性

- **顺序解析**：变量按定义顺序逐个解析
- **递归替换**：支持嵌套的数据结构
- **Shell 集成**：通过 `subprocess.check_output` 执行命令
- **错误追踪**：提供详细的错误信息和上下文

## 未来扩展

### 可能的改进方向

1. **类型转换**：自动识别并转换变量类型（int、float、bool）
2. **条件变量**：支持 if-else 条件表达式
3. **内置函数**：提供常用的辅助函数（min、max、range 等）
4. **变量导出**：支持将解析后的变量导出为环境变量

### 示例：类型转换（未来）

```yaml
variables:
  - NPROC: $(nproc) # 自动转换为 int
  - RATIO: 0.75 # 自动识别为 float
  - ENABLED: true # 自动识别为 bool
```

## 总结

Pipa 的变量系统为配置管理带来了革命性的改进：

- 🎯 **目标明确**：像 Dockerfile 一样优雅
- 🔧 **功能强大**：支持 shell 命令和算术表达式
- 📦 **易于维护**：集中管理，DRY 原则
- 🚀 **动态适配**：在不同环境下自动调整

这是 Pipa 架构的又一次伟大飞跃，真正实现了"配置即代码"的理想！

---

**文档版本**: v1.0
**最后更新**: 2025-11-08
**相关功能**: `src/config_loader.py::_resolve_variables_and_commands()`
