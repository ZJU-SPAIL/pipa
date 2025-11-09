"""
单元测试：配置加载器的变量解析系统

测试 config_loader.py 中的变量声明、解析和替换功能。
"""

import subprocess

import pytest

from src.config_loader import ConfigError, _resolve_variables_and_commands, load_workload_config


class TestVariableResolution:
    """测试变量解析的核心逻辑"""

    def test_simple_variable_definition(self):
        """测试简单的变量定义"""
        config = {
            "variables": [
                {"VAR1": "value1"},
                {"VAR2": "value2"},
            ],
            "command": "${VAR1} and ${VAR2}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["command"] == "value1 and value2"

    def test_variable_with_shell_command(self):
        """测试包含 shell 命令的变量"""
        config = {
            "variables": [
                {"HOSTNAME": "$(hostname)"},
            ],
            "result": "Host is ${HOSTNAME}",
        }

        result = _resolve_variables_and_commands(config)

        assert "Host is " in result["result"]
        assert len(result["result"]) > len("Host is ")

    def test_variable_with_arithmetic_expression(self):
        """测试算术表达式变量"""
        config = {
            "variables": [
                {"BASE": "10"},
                {"DOUBLE": "$((${BASE} * 2))"},
                {"HALF": "$((${BASE} / 2))"},
            ],
            "double": "${DOUBLE}",
            "half": "${HALF}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["double"] == "20"
        assert result["half"] == "5"

    def test_sequential_variable_dependency(self):
        """测试变量的顺序依赖"""
        config = {
            "variables": [
                {"VAR1": "hello"},
                {"VAR2": "${VAR1}_world"},
                {"VAR3": "${VAR2}!"},
            ],
            "message": "${VAR3}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["message"] == "hello_world!"

    def test_variable_in_nested_structure(self):
        """测试嵌套结构中的变量替换"""
        config = {
            "variables": [
                {"PORT": "3306"},
                {"HOST": "localhost"},
            ],
            "database": {
                "connection": {
                    "host": "${HOST}",
                    "port": "${PORT}",
                },
            },
        }

        result = _resolve_variables_and_commands(config)

        assert result["database"]["connection"]["host"] == "localhost"
        assert result["database"]["connection"]["port"] == "3306"

    def test_variable_in_list(self):
        """测试列表中的变量替换"""
        config = {
            "variables": [
                {"BASE_DIR": "/opt/app"},
            ],
            "paths": [
                "${BASE_DIR}/bin",
                "${BASE_DIR}/lib",
                "${BASE_DIR}/data",
            ],
        }

        result = _resolve_variables_and_commands(config)

        assert result["paths"][0] == "/opt/app/bin"
        assert result["paths"][1] == "/opt/app/lib"
        assert result["paths"][2] == "/opt/app/data"

    def test_complex_shell_expression(self):
        """测试复杂的 shell 表达式"""
        config = {
            "variables": [
                {"NPROC": "$(nproc)"},
                {"HALF": "$((${NPROC} / 2))"},
                {"RANGE": "0-$((${HALF} - 1))"},
            ],
            "cpu_range": "${RANGE}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["cpu_range"].startswith("0-")
        assert result["cpu_range"].split("-")[1].isdigit()

    def test_multiple_variables_in_one_string(self):
        """测试一个字符串中包含多个变量"""
        config = {
            "variables": [
                {"USER": "admin"},
                {"HOST": "localhost"},
                {"PORT": "3306"},
            ],
            "connection_string": "mysql://${USER}@${HOST}:${PORT}/db",
        }

        result = _resolve_variables_and_commands(config)

        assert result["connection_string"] == "mysql://admin@localhost:3306/db"

    def test_empty_variables_block(self):
        """测试空的 variables 块"""
        config = {
            "variables": [],
            "command": "echo hello",
        }

        result = _resolve_variables_and_commands(config)

        assert result["command"] == "echo hello"

    def test_no_variables_block(self):
        """测试没有 variables 块的配置"""
        config = {
            "command": "echo hello",
        }

        result = _resolve_variables_and_commands(config)

        assert result["command"] == "echo hello"

    def test_undefined_variable_reference(self):
        """测试引用未定义的变量（保持原样）"""
        config = {
            "variables": [
                {"VAR1": "value1"},
            ],
            "command": "${VAR1} and ${UNDEFINED}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["command"] == "value1 and ${UNDEFINED}"

    def test_variable_with_special_characters(self):
        """测试包含特殊字符的变量值"""
        config = {
            "variables": [
                {"PASSWORD": "p@ssw0rd!"},
                {"PATH": "/opt/app-v1.0"},
            ],
            "config": {
                "password": "${PASSWORD}",
                "path": "${PATH}",
            },
        }

        result = _resolve_variables_and_commands(config)

        assert result["config"]["password"] == "p@ssw0rd!"
        assert result["config"]["path"] == "/opt/app-v1.0"

    def test_shell_command_in_config_body(self):
        """测试配置主体中直接使用 shell 命令"""
        config = {
            "variables": [
                {"BASE": "10"},
            ],
            "computed": "$((${BASE} + 5))",
        }

        result = _resolve_variables_and_commands(config)

        assert result["computed"] == "15"


class TestErrorHandling:
    """测试错误处理"""

    def test_invalid_shell_command_in_variable(self):
        """测试变量中的无效 shell 命令会产生空结果"""
        config = {
            "variables": [
                {"BAD_CMD": "$(nonexistent_command_xyz 2>/dev/null)"},
            ],
            "result": "${BAD_CMD}",
        }

        result = _resolve_variables_and_commands(config)
        assert result["result"] == ""

    def test_invalid_shell_command_in_config(self):
        """测试配置主体中的无效 shell 命令会产生空结果"""
        config = {
            "command": "$(nonexistent_command_xyz 2>/dev/null)",
        }

        result = _resolve_variables_and_commands(config)
        assert result["command"] == ""

    def test_malformed_variable_definition(self):
        """测试格式错误的变量定义（会被忽略）"""
        config = {
            "variables": [
                {"VAR1": "value1"},
                {"KEY1": "value1", "KEY2": "value2"},
                {"VAR2": "value2"},
            ],
            "result": "${VAR1}-${VAR2}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["result"] == "value1-value2"


class TestRealWorldScenarios:
    """测试真实世界的使用场景"""

    def test_dynamic_cpu_allocation(self):
        """测试动态 CPU 分配（类似 MySQL showcase）"""
        config = {
            "variables": [
                {"NPROC": "$(nproc)"},
                {"HALF_PROC": "$((${NPROC} / 2))"},
                {"MYSQL_CPUS": "0-$((${HALF_PROC} - 1))"},
                {"SYSBENCH_CPUS": "${HALF_PROC}-$((${NPROC} - 1))"},
            ],
            "commands": {
                "start": "taskset -c ${MYSQL_CPUS} mysqld &",
                "benchmark": "taskset -c ${SYSBENCH_CPUS} sysbench run",
            },
        }

        result = _resolve_variables_and_commands(config)

        assert "taskset -c" in result["commands"]["start"]
        assert "mysqld" in result["commands"]["start"]
        assert "taskset -c" in result["commands"]["benchmark"]
        assert "sysbench" in result["commands"]["benchmark"]

    def test_path_construction(self):
        """测试路径构建场景"""
        config = {
            "variables": [
                {"BASE_DIR": "/opt/mysql"},
                {"BIN_DIR": "${BASE_DIR}/bin"},
                {"DATA_DIR": "${BASE_DIR}/data"},
                {"LOG_DIR": "${BASE_DIR}/logs"},
            ],
            "paths": {
                "mysqld": "${BIN_DIR}/mysqld",
                "mysql": "${BIN_DIR}/mysql",
                "datadir": "${DATA_DIR}",
                "error_log": "${LOG_DIR}/error.log",
            },
        }

        result = _resolve_variables_and_commands(config)

        assert result["paths"]["mysqld"] == "/opt/mysql/bin/mysqld"
        assert result["paths"]["mysql"] == "/opt/mysql/bin/mysql"
        assert result["paths"]["datadir"] == "/opt/mysql/data"
        assert result["paths"]["error_log"] == "/opt/mysql/logs/error.log"

    def test_intensity_calculation(self):
        """测试强度计算场景"""
        config = {
            "variables": [
                {"NPROC": "$(nproc)"},
            ],
            "benchmark_driver": {
                "intensity_variable": {
                    "name": "threads",
                    "min": 8,
                    "max": "$((${NPROC} * 2))",
                },
            },
        }

        result = _resolve_variables_and_commands(config)

        max_threads = int(result["benchmark_driver"]["intensity_variable"]["max"])
        nproc = int(subprocess.check_output("nproc", shell=True, text=True).strip())
        assert max_threads == nproc * 2


class TestLoadWorkloadConfig:
    """测试 load_workload_config 函数的集成"""

    def test_load_yaml_with_variables(self, tmp_path):
        """测试从 YAML 文件加载带变量的配置"""
        config_content = """
workload_name: test_workload

variables:
  - BASE_VALUE: "100"
  - DOUBLE_VALUE: "$((${BASE_VALUE} * 2))"

commands:
  start: "echo ${DOUBLE_VALUE}"
  stop: "echo stop"

benchmark_driver:
  command_template: "benchmark --value=${DOUBLE_VALUE}"
  intensity_variable:
    name: threads
    min: 1
    max: 10
"""
        config_file = tmp_path / "test_workload.yaml"
        config_file.write_text(config_content)

        result = load_workload_config(str(config_file))

        assert result["workload_name"] == "test_workload"
        assert result["commands"]["start"] == "echo 200"
        assert "benchmark --value=200" in result["benchmark_driver"]["command_template"]

    def test_load_config_without_variables(self, tmp_path):
        """测试加载不包含变量的配置"""
        config_content = """
workload_name: simple_workload

commands:
  start: "service start"
  stop: "service stop"
"""
        config_file = tmp_path / "simple_workload.yaml"
        config_file.write_text(config_content)

        result = load_workload_config(str(config_file))

        assert result["workload_name"] == "simple_workload"
        assert result["commands"]["start"] == "service start"

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        with pytest.raises(ConfigError) as exc_info:
            load_workload_config("nonexistent_file.yaml")

        assert "未找到" in str(exc_info.value)

    def test_load_invalid_yaml(self, tmp_path):
        """测试加载无效的 YAML 文件"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigError) as exc_info:
            load_workload_config(str(config_file))

        assert "解析 YAML" in str(exc_info.value)


class TestEdgeCases:
    """测试边界情况"""

    def test_numeric_variable_values(self):
        """测试数字类型的变量值"""
        config = {
            "variables": [
                {"PORT": 3306},
                {"TIMEOUT": 30},
            ],
            "config": {
                "port": "${PORT}",
                "timeout": "${TIMEOUT}",
            },
        }

        result = _resolve_variables_and_commands(config)

        assert result["config"]["port"] == "3306"
        assert result["config"]["timeout"] == "30"

    def test_variable_with_quotes(self):
        """测试包含引号的变量值"""
        config = {
            "variables": [
                {"RANGE": '"0-15"'},
            ],
            "command": "taskset -c ${RANGE}",
        }

        result = _resolve_variables_and_commands(config)

        assert '"0-15"' in result["command"]

    def test_variable_with_dollar_sign(self):
        """测试包含美元符号的变量值（不是变量引用）"""
        config = {
            "variables": [
                {"PRICE": "100"},
            ],
            "message": "Price is $${PRICE}",
        }

        result = _resolve_variables_and_commands(config)

        assert "PRICE" in result["message"] or "100" in result["message"]

    def test_empty_variable_value(self):
        """测试空字符串变量值"""
        config = {
            "variables": [
                {"EMPTY_VAR": ""},
            ],
            "command": "echo '${EMPTY_VAR}'",
        }

        result = _resolve_variables_and_commands(config)

        assert result["command"] == "echo ''"

    def test_very_long_variable_chain(self):
        """测试很长的变量依赖链"""
        config = {
            "variables": [
                {"VAR1": "a"},
                {"VAR2": "${VAR1}b"},
                {"VAR3": "${VAR2}c"},
                {"VAR4": "${VAR3}d"},
                {"VAR5": "${VAR4}e"},
            ],
            "result": "${VAR5}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["result"] == "abcde"

    def test_variable_in_complex_command(self):
        """测试复杂命令中的变量"""
        config = {
            "variables": [
                {"HOST": "localhost"},
                {"PORT": "3306"},
                {"USER": "root"},
            ],
            "command": ("mysql -h ${HOST} -P ${PORT} -u ${USER} " "-e 'SELECT * FROM table' | grep -v ^$ | wc -l"),
        }

        result = _resolve_variables_and_commands(config)

        assert "localhost" in result["command"]
        assert "3306" in result["command"]
        assert "root" in result["command"]


class TestPerformance:
    """测试性能相关场景"""

    def test_large_config_with_many_variables(self):
        """测试包含大量变量的配置"""
        variables = [{"VAR" + str(i): f"value{i}"} for i in range(100)]
        config = {
            "variables": variables,
            "command": "${VAR50}",
        }

        result = _resolve_variables_and_commands(config)

        assert result["command"] == "value50"

    def test_deeply_nested_structure(self):
        """测试深度嵌套的数据结构"""
        config = {
            "variables": [
                {"VALUE": "deep"},
            ],
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {"value": "${VALUE}"},
                        },
                    },
                },
            },
        }

        result = _resolve_variables_and_commands(config)

        assert result["level1"]["level2"]["level3"]["level4"]["level5"]["value"] == "deep"


if __name__ == "__main__":
    # 允许直接运行此文件进行测试
    pytest.main([__file__, "-v"])
