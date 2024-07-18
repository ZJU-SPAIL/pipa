import questionary

from .run_by_pipa import main as run_by_pipa
from .run_by_user import main as run_by_user
from .export_pipashu_config_template import generate_pipashu_template
from .parse_pipashu_config import main as parse_pipashu_config
from .export_pipashu_config_template import generate_upload_template


def quest_summary(config_path: str = None):
    """
    Displays a menu to the user and performs different actions based on their selection.

    Args:
        config_path (str, optional): Path to the configuration file. Defaults to None.

    Returns:
        None
    """

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
            "Generate a configuration template configuration of pipa-upload.",
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
        generate_pipashu_template()
    elif how_to_run == "Build scripts based on the configuration file of PIPA-SHU.":
        parse_pipashu_config()
    elif (
        how_to_run == "Generate a configuration template configuration of pipa-upload."
    ):
        generate_upload_template()
    else:
        exit(0)
