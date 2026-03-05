"""Primary CLI entrypoint for the supported PIPA commands."""

from __future__ import annotations

import logging

import fire
from rich import print

from pipa.__about__ import __version__
from pipa.commands.analyze import analyze_archive
from pipa.common.logger import set_level
from pipa.common.utils import handle_user_cancelled


class PipaCLI:
    """Lightweight CLI exposing the maintained PIPA commands."""

    def __init__(self, debug: bool = False, log_level: str | None = None) -> None:
        if debug:
            set_level(logging.DEBUG, logging.DEBUG)
        if log_level:
            set_level(log_level.upper(), log_level.upper())

    @handle_user_cancelled
    def analyze(
        self,
        archive_path: str,
        output_path: str | None = None,
        expected_cpus: str | None = None,
        symfs: str | None = None,
        kallsyms: str | None = None,
    ) -> None:
        """Analyze a pipa-tree archive and emit an HTML report."""

        report_path = analyze_archive(
            archive_path,
            output_path=output_path,
            expected_cpus=expected_cpus,
            symfs=symfs,
            kallsyms=kallsyms,
        )
        print(f"Analysis complete. Report saved to: {report_path}")

    def version(self) -> None:
        """Print the current PIPA version."""

        print(f"PIPA (Platform Integrated Performance Analytics) version {__version__}")
        print("Developed by: SPAIL, ZJU https://github.com/ZJU-SPAIL/pipa")
        print("All rights reserved.")
        print("Licensed under the MIT License")
        print("https://github.com/ZJU-SPAIL/pipa")


def main() -> None:
    """Entry-point used by the ``pipa`` console script."""

    fire.Fire(PipaCLI)
