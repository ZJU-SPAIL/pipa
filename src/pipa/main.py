import fire
from pipa.service.gengerate.all import quest_summary as generate_sh
from pipa.service.export_sys_config import run_export_config_script
from pipa.__about__ import __version__
from rich import print


class PipaCLI:
    def generate(self):
        # Generate the performance collection scripts
        generate_sh()

    def export(self):
        # Export system configuration
        run_export_config_script()

    def help(self):
        # Show this help message and exit
        print("PIPA (Platform Integrated Performance Analytics)")
        print("Developed by: SPAIL, ZJU https://github.com/ZJU-SPAIL")
        print("Usage:")
        print("  pipa generate")
        print("  pipa export")
        print("  pipa version")
        print("  pipa help")
        print("Options:")
        print("  generate  Generate the performance collection scripts")
        print("  export    Export system configuration")
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
