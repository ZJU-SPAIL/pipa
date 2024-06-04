from pipa.export_config.cpu_config import get_all_cpu_config
from pipa.export_config.py_config import get_platform_info
from pipa.export_config.sys_config import get_all_sys_config


def get_all_config():
    """
    Retrieves all configuration information.

    This function calls several other functions to gather platform information,
    system configuration, and CPU configuration.

    Returns:
        None
    """
    get_platform_info()
    get_all_sys_config()
    get_all_cpu_config()


if __name__ == "__main__":
    get_all_config()
