import platform
import yaml
from pipa.common.logger import logger
from pipa.common.config import CONFIG_DIR


def get_platform_info():
    info = {
        "architecture": str(platform.architecture()),
        "machine": platform.machine(),
        "node": platform.node(),
        "platform": platform.platform(aliased=False, terse=False),
        "processor": platform.processor(),
        "python_build": str(platform.python_build()),
        "python_compiler": platform.python_compiler(),
        "python_branch": platform.python_branch(),
        "python_implementation": platform.python_implementation(),
        "python_revision": platform.python_revision(),
        "python_version": platform.python_version(),
        "release": platform.release(),
        "system": platform.system(),
        "version": platform.version(),
    }
    logger.info("Platform information: %s", info)
    yaml.dump(info, open(f"{CONFIG_DIR}/python_platform_info.yaml", "w"))
    return info

if __name__ == "__main__":
    get_platform_info()