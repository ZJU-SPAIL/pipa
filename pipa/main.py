import fire
from pipa.service.generate_shell_script import generate as generate_sh


class PipaCLI:
    def generate(self):
        generate_sh()


def main():
    fire.Fire(PipaCLI)


if __name__ == "__main__":
    main()
