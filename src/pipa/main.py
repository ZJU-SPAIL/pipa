import fire
from pipa.service.gengerate.all import quest_summary as generate_sh
from pipa.service.export_sys_config import run_export_config_script
from pipa.service.upload import main as pipa_upload
from pipa.service.dump import dump as pipa_dump
from pipa.service.archive import archive as pipa_archive
from pipa.common.utils import handle_user_cancelled
from pipa.__about__ import __version__
from rich import print


class PipaCLI:
    """
    The PipaCLI represents the command-line interface for PIPA (Platform Integrated Performance Analytics).
    It provides methods for generating performance collection scripts, exporting system configuration,
    uploading performance data, and displaying help and version information.
    Developed by: SPAIL, ZJU https://github.com/ZJU-SPAIL

    Usage:
      pipa generate
      pipa export
      pipa upload
      pipa dump
      pipa archive
      pipa version
      pipa help

    Options:
      generate  Generate the performance collection scripts
      export    Export system configuration
      upload    Upload the performance data to PIPAD server
      dump      Dump PIPASHU overview data to a file
      archive   Archive buildid and source files
      version   Show the version of PIPA
      help      Show this help message and exit
    """

    @handle_user_cancelled
    def generate(self, config_path: str = None):
        # Generate the performance collection scripts
        generate_sh(config_path)

    @handle_user_cancelled
    def export(self):
        # Export system configuration
        run_export_config_script()

    @handle_user_cancelled
    def upload(self, config_path: str = None, verbose: bool = False):
        # Upload the performance data
        pipa_upload(config_path, verbose)

    def dump(self, output_path: str, config_path: str = None, verbose: bool = False):
        # Dump PIPASHU overview data to a file
        pipa_dump(output_path, config_path, verbose)

    def archive(self, perf_data: str = "perf.data", output_path: str = "./"):
        # Archive buildid and source files
        pipa_archive(perf_data=perf_data, output_path=output_path)

    def help(self):
        # Show this help message and exit
        print("PIPA (Platform Integrated Performance Analytics)")
        print("Developed by: SPAIL, ZJU https://github.com/ZJU-SPAIL")
        print("Usage:")
        print("  pipa generate")
        print("  pipa export")
        print("  pipa upload")
        print("  pipa dump")
        print("  pipa archive")
        print("  pipa version")
        print("  pipa help")
        print("Options:")
        print("  generate  Generate the performance collection scripts")
        print("  export    Export system configuration")
        print("  upload    Upload the performance data to PIPAD server")
        print("  dump      Dump PIPASHU overview data to a file")
        print("  archive   Archive buildid and source files")
        print("  version   Show the version of PIPA")
        print("  help      Show this help message and exit")

    def version(self):
        # Show the version of PIPA
        print(f"PIPA (Platform Integrated Performance Analytics) version {__version__}")
        print("Developed by: SPAIL, ZJU https://github.com/ZJU-SPAIL")
        print("All rights reserved.")
        print("Licensed under the MIT License")
        print("https://github.com/ZJU-SPAIL/pipa")


def main():
    fire.Fire(PipaCLI)


if __name__ == "__main__":
    main()
