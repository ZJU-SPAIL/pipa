import re, multiprocessing
import pandas as pd
from pipa.common.logger import logger
from pipa.export_config.cpu_config import NB_PHYSICAL_CORES


def parse_one_line(s):
    try:
        # TODO support more than two columns for the overhead percentage
        (
            overhead_cycles,
            overhead_insns,
            command,
            shared_object,
            execution_mode,
            symbol,
        ) = re.match(
            r"\s*(\d+\.\d+)%\s+(\d+\.\d+)%\s+(.+?)\s+(.+?)\s+\[(\S+)\]\s+(.*)", s
        ).groups()
    except Exception as e:
        logger.warning("parse failed for line: " + s + "\n with error: " + str(e))
        return None
    return (
        float(overhead_cycles),
        float(overhead_insns),
        command,
        shared_object,
        execution_mode,
        symbol,
    )


def parse_perf_report_file(parsed_report_path, processes_num=NB_PHYSICAL_CORES // 2):
    with open(parsed_report_path, "r") as file:
        content = [l.strip() for l in file.readlines()]
    if content is None:
        logger.info("content is None")
        return None

    content = [l for l in content if not l.startswith("#") and l.strip() != ""]

    if len(content) > 10**6:
        logger.info("content is too large, will use multiprocessing")
        pool = multiprocessing.Pool(processes=processes_num)
        data = pool.map(parse_one_line, content)
        pool.close()
        pool.join()
    else:
        data = [parse_one_line(l) for l in content]

    data = [d for d in data if d is not None]

    logger.info("Successfully parsed data")
    logger.info("parsed data length: " + str(len(data)))

    return pd.DataFrame(
        data,
        columns=[
            "overhead_cycles",
            "overhead_insns",
            "command",
            "shared_object",
            "execution_mode",
            "symbol",
        ],
    )


# TODO move this to a test file
def test_parse_line():
    s = "    14.09%  14.18%  db_bench         db_bench                                       [.] rocksdb::DBImpl::GetImpl"
    assert parse_one_line(s) == (
        "14.09",
        "14.18",
        "db_bench",
        "db_bench",
        ".",
        "rocksdb::DBImpl::GetImpl",
    )
