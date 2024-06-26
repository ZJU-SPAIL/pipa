from pipa.service.gengerate.common import (
    load_yaml_config,
    parse_run_by_pipa,
    parse_run_by_user,
    parse_basic,
)
from pipa.service.gengerate.run_by_pipa import generate as generate_pipa
from pipa.service.gengerate.run_by_user import generate as generate_user
from pipa.export_config.cpu_config import get_cpu_cores

import questionary


def build_command(use_taskset: bool, core_range, command):
    if use_taskset:
        CORES_ALL = get_cpu_cores()
        if core_range.isdigit():
            core_list = core_range.strip()
        elif core_range.split("-").__len__() != 2:
            raise ("Please input cores as a valid range, split by '-'.")
        else:
            left, right = core_range.split("-")

            left, right = left.strip(), right.strip()
            if not left.isdigit() or not right.isdigit():
                raise ("Please input cores as a valid range, non-digit char detected.")
            left, right = int(left), int(right)
            if left < CORES_ALL[0] or right > CORES_ALL[-1] or left > right:
                raise ("Please input cores as a valid range.")
            core_list = ",".join([str(i) for i in list(range(left, right + 1))])

        command = f"/usr/bin/taskset -c {core_list} {command}"
    return command


def quest():
    config_yaml = questionary.text(
        "Where is the configuration file of PIPA-SHU?\n", "./config-pipa-shu.yaml"
    ).ask()
    return config_yaml


def build(path: str):
    data = load_yaml_config(path)
    (
        workspace,
        freq_record,
        events_record,
        freq_stat,
        events_stat,
        annotete,
        run_by_perf,
    ) = parse_basic(data)

    events_stat = ",".join(events_stat)

    if run_by_perf:
        use_taskset, core_range, command = parse_run_by_pipa(data)
        generate_pipa(
            workspace,
            freq_record,
            events_record,
            freq_stat,
            events_stat,
            annotete,
            build_command(use_taskset, core_range, command),
        )
    else:
        duration_record, duration_stat = parse_run_by_user(data)
        generate_user(
            workspace,
            freq_record,
            events_record,
            freq_stat,
            events_stat,
            annotete,
            duration_record,
            duration_stat,
        )


def main():
    build(quest())
