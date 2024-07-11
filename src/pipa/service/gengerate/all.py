import questionary

from pipa.service.gengerate.run_by_pipa import main as run_by_pipa
from pipa.service.gengerate.run_by_user import main as run_by_user
from pipa.service.gengerate.export_pipashu_config_template import generate_template
from pipa.service.gengerate.parse_pipashu_config import main as parse_pipashu_config


def quest_summary(config_path: str = None):
    # TODO make these code more elegant
    if config_path:
        return parse_pipashu_config(config_path)

    how_to_run = questionary.select(
        "Please select the way of workload you want to run.",
        choices=[
            "Build scripts that collect global performance data.",
            "Build a script that collects performance data and start the workload by perf.",
            "Generate a configuration template configuration of PIPA-SHU.",
            "Build scripts based on the configuration file of PIPA-SHU.",
            "Exit.",
        ],
    ).ask()

    if (
        how_to_run
        == "Build a script that collects performance data and start the workload by perf."
    ):
        run_by_pipa()
    elif how_to_run == "Build scripts that collect global performance data.":
        run_by_user()
    elif how_to_run == "Generate a configuration template configuration of PIPA-SHU.":
        generate_template()
    elif how_to_run == "Build scripts based on the configuration file of PIPA-SHU.":
        parse_pipashu_config()
    else:
        exit(0)
