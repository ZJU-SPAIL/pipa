import fire
from pipa.service.gengerate.all import quest_summary as generate_sh
from pipa.__about__ import __version__


class PipaCLI:
    def generate(self):
        generate_sh()

    def version(self):
        print(f"PIPA (Platform Integrated Performance Analytics) v{__version__}")
        print("Developed by: SPAIL, ZJU")
        print("All rights reserved.")
        print("Licensed under the MIT License")


def main():
    fire.Fire(PipaCLI)


if __name__ == "__main__":
    main()
