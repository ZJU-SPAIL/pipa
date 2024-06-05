import questionary

from pipa.service.gengerate.run_by_pipa import main as run_by_pipa
from pipa.service.gengerate.run_by_user import main as run_by_user


def quest_summary():
    how_to_run = questionary.select(
        "Please select the way of workload you want to run.",
        choices=[
            "Build a script that collects performance data and start the workload by perf.",
            "Build a script that collects global performance data.",
        ],
    ).ask()
    if (
        how_to_run
        == "Build a script that collects performance data and start the workload by perf."
    ):
        run_by_pipa()
    elif (
        how_to_run
        == "Build a script that collects performance data and start the workload by user."
    ):
        run_by_user()
