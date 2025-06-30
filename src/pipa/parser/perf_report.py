import pandas as pd
import re
from pipa.common.logger import logger


def parse_one_line(s, lr):
    """
    Parse a single line of a performance report.

    Args:
        s (str): The input line to parse.
        lr (list): A list of tuples representing the start and end indices of each field in the line.

    Returns:
        tuple: A tuple containing the parsed values from the line in the following order:
            - overhead_cycles (float): The number of overhead cycles.
            - overhead_insns (float): The number of overhead instructions.
            - command (str): The command associated with the line.
            - shared_object (str): The shared object associated with the line.
            - execution_mode (str): The execution mode associated with the line.
            - symbol (str): The symbol associated with the line.
    """
    try:
        # TODO support more than two columns for the overhead percentage
        (
            overhead,
            command,
            shared_object,
            symbol,
        ) = (
            s[lr[0][0] : lr[0][1]],
            s[lr[1][0] : lr[1][1]],
            s[lr[2][0] : lr[2][1]],
            s[lr[3][0] :],
        )
        overhead_cycles, overhead_insns = overhead.split()
        execution_mode = symbol.split()[0]
        symbol = " ".join(symbol.split()[1:])
        execution_mode = execution_mode[1]
    except Exception as e:
        logger.warning("parse failed for line: " + s + "\n with error: " + str(e))
        return None
    return (
        float(overhead_cycles[:-1]),
        float(overhead_insns[:-1]),
        command.strip(),
        shared_object.strip(),
        execution_mode,
        symbol.strip(),
    )


def parse_perf_report_file(parsed_report_path):
    """
    Parses a performance report file and returns the parsed data as a pandas DataFrame.

    Args:
        parsed_report_path (str): The path to the parsed report file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame with the following columns:
            - overhead_cycles: The number of overhead cycles.
            - overhead_insns: The number of overhead instructions.
            - command: The command associated with the performance data.
            - shared_object: The shared object associated with the performance data.
            - execution_mode: The execution mode associated with the performance data.
            - symbol: The symbol associated with the performance data.
    """
    lr = []
    with open(parsed_report_path, "r") as file:
        lines = file.readlines()
        for line in lines:
            if "......." in line:
                a = line.strip().removeprefix("#").split()
                for x in a:
                    if not lr:
                        l = line.index(x)
                        lr.append((l, l + len(x)))
                    else:
                        l = line.index(x, lr[-1][1])
                        lr.append((l, l + len(x)))
                break

    content = [l for l in lines if not l.startswith("#") and l.strip() != ""]

    if content is None:
        logger.info("content is None")
        return None

    data = [parse_one_line(l, lr) for l in content]

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
columns_type = {
    "Overhead": float,
    "Period": int,
    "Samples": int,
    "Pid":int,
    "Command": str,
    "Shared Object": str,
    "Execution Mode": str,
    "Symbol": str,
}
multi_columns = ['Overhead','Period','Samples']     # TODO more lines need to be splited


def parse_one_line_2(s, lr, header):
    """
    Parse a single line of a performance report.

    Args:
        s (str): The input line to parse.
        lr (list): A list of tuples representing the start and end indices of each field in the line. As long as header.
        header (list): A list of header names for the line. As long as lr.

    Returns:
        list: A list containing the parsed values from the line:
            - overhead_cycles (float): The number of overhead cycles.
            - overhead_insns (float): The number of overhead instructions.
            - command (str): The command associated with the line.
            - shared_object (str): The shared object associated with the line.
            - execution_mode (str): The execution mode associated with the line.
            - symbol (str): The symbol associated with the line.
            ...
    """
    res = []
    try:
        for i in range(len(lr)):
            res.append(columns_type[header[i].split("_")[0]](s[lr[i][0]:lr[i][1]].strip().strip('%')))
    except Exception as e:
        logger.warning("parse failed for line: " + s + "\n with error: " + str(e))
        return None
    return res

def parse_perf_report_file_2(parsed_report_path, events=None):
    """
    Parses a performance report file and returns the parsed data as a pandas DataFrame.

    Args:
        parsed_report_path_2 (str): The path to the parsed report file.
        events (list, optional): A list of events to include in the parsed data. If default to None, get events from report file header.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame with columns extracted from report file:
            - overhead_cycles: The number of overhead cycles.
            - overhead_insns: The number of overhead instructions.
            - command: The command associated with the performance data.
            - shared_object: The shared object associated with the performance data.
            - execution_mode: The execution mode associated with the performance data.
            - symbol: The symbol associated with the performance data.
            ...
    """
    content = []
    headers = None
    colspecs = []

    with open(parsed_report_path, "r") as file:
        pre_line = None

        for line in file.readlines():
            if headers is None and line.startswith("# ."):
                # get column width from perf.report
                splits = line.strip()[1:].split()
                last = 2
                for sp in splits:
                    colspecs.append((last, last+len(sp)))
                    last += len(sp)+2

                # get header from perf.report
                headers = [pre_line[col[0]:col[1]] for col in colspecs]           
                headers2 = [x.strip() for x in headers if x]
                headers = [x for x in headers if x]
                pid_idx = headers[headers2.index('Pid:Command')].index(':')
                headers = headers2

                # separate Pid:Command column
                if 'Pid:Command' in headers:
                    modi_indx = headers.index('Pid:Command')

                    headers[modi_indx] = 'Pid'
                    headers.insert(modi_indx+1, 'Command')

                    beg_old = colspecs[modi_indx][0]
                    end_old = colspecs[modi_indx][1]
                    colspecs[modi_indx] = (beg_old, beg_old+pid_idx)
                    colspecs.insert(modi_indx+1, ((beg_old+pid_idx+1), end_old))

                # separate execution mode column
                if 'Symbol' in headers:
                    modi_indx = headers.index('Symbol')

                    headers[modi_indx] = 'Execution Mode'
                    headers.insert(modi_indx+1, 'Symbol')

                    beg_old = colspecs[modi_indx][0]
                    end_old = colspecs[modi_indx][1]
                    colspecs[modi_indx] = (beg_old, beg_old+3)
                    colspecs.insert(modi_indx+1, ((beg_old+4), end_old))

                # separate columns for events
                for modi_column in multi_columns:
                    if modi_column in headers:
                        modi_indx = headers.index(modi_column)
                    else:
                        continue
                    beg_old = colspecs[modi_indx][0]
                    end_old = colspecs[modi_indx][1]
                    
                    i = 0
                    for event in events:
                        if i == 0:
                            headers[modi_indx] = modi_column+'_'+event
                            colspecs[modi_indx] = (beg_old, (beg_old * (len(events)-1)+ end_old)//len(events))
                        else:
                            headers.insert(modi_indx+i, modi_column+'_'+event)
                            colspecs.insert(modi_indx+i, ((beg_old * (len(events)-i)+ end_old * i)//len(events), ((beg_old * (len(events)-(i+1))+ end_old * (i+1))//len(events))))
                        i += 1

            elif events is None and line.startswith('# Samples'):  # get events
                try:
                    events_str = re.search(r"'(.*?)'", line).group(0).strip('\'')
                    events_str_2 = re.search(r"{(.*?)}", events_str)
                    if events_str_2:
                        events = events_str_2.group(0).strip('{}').split(',')
                    else:
                        events = events_str.strip('\'').split(',')
                    events = [e.strip() for e in events]
                    logger.info("get events "+str(events)+" from report file")
                except Exception as e:
                    logger.warning("get events failed for line: " + line + "\n with error: " + str(e))
            elif not line.startswith('#') and line!='\n':
                content.append(line)
            pre_line = line
    data = [parse_one_line_2(l, colspecs,headers) for l in content]

    data = [d for d in data if d is not None]
        
    logger.info("Successfully parsed data")
    logger.info("parsed data length: " + str(len(data)))

    return pd.DataFrame(
        data,
        columns=headers
    )
