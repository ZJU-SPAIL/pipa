import fire
from pipa.service.gengerate.run_by_pipa import main as generate_sh


class PipaCLI:
    def generate(self):
        generate_sh()


def main():
    fire.Fire(PipaCLI)


if __name__ == "__main__":
    main()
