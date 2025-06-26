import re
import pandas as pd
from multiprocessing import Pool
from typing import Optional, Dict, Set, List
from decimal import Decimal, InvalidOperation
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.logger import logger
from collections import defaultdict


# Data classes for perf script parsing and processing
class PerfScriptCall:
    """
    Represents a single performance script call.

    Attributes:
        addr (str): The address of the call.
        symbol (str): The symbol associated with the call.
        caller (str): The caller of the call.
    """

    def __init__(self, addr: str, symbol: str, caller: str):
        self.addr: str = addr
        self.symbol: str = symbol
        self.caller: str = caller

    def __str__(self):
        return f"{self.addr} {self.symbol} ({self.caller})"


class PerfScriptHeader:
    """
    Represents a header in a perf script block.

    Attributes:
        command (str): The command associated with the record.
        pid (int): The process ID associated with the record.
        cpu (int): The CPU number associated with the record.
        time (str): The time associated with the record.
        value (int): The value associated with the record.
        event (str): The event associated with the record.
    """

    def __init__(
        self, command: str, pid: int, cpu: int, time: str, value: int, event: str
    ):
        self.command: str = command
        self.pid: int = pid
        self.cpu: int = cpu
        # the perf script time field format is x.y
        # default unit is seconds.microseconds
        # when append --ns param, unit is seconds.nanoseconds
        # when append --reltime param, it starts from 0.0 at the begining
        self.time: str = time
        self.xytime: Decimal = Decimal(time)
        self.value: int = value
        self.event: str = event

    def __str__(self):
        return f"{self.command} {self.pid} {self.cpu} {self.time} {self.value} {self.event}"


class PerfScriptBlock:
    """
    Represents a block of performance script.

    Attributes:
        header (PerfScriptHeader): The header of the performance script block.
        calls (list[PerfScriptCall]): The list of performance script calls.

    Methods:
        __str__(): Returns a string representation of the PerfScriptBlock object.
        to_record(): Converts the PerfScriptBlock object to a record.
    """

    def __init__(self, header: PerfScriptHeader, calls: List[PerfScriptCall]):
        self.header: PerfScriptHeader = header
        self.calls: List[PerfScriptCall] = calls

    def __str__(self):
        return f"{self.header}\n{self.calls}"

    def to_record(self):
        """
        Converts the PerfScriptBlock object to a record.

        Returns:
            dict: A dictionary containing the record data.
        """
        return {
            "command": self.header.command,
            "pid": self.header.pid,
            "cpu": self.header.cpu,
            "time": self.header.time,
            "value": self.header.value,
            "event": self.header.event,
            "calls": [str(c) for c in self.calls],
        }


# Parser class for performance script data
class PerfScriptParser:
    """
    A class responsible for parsing performance script data.
    """

    @staticmethod
    def parse_one_call(line: str) -> Optional[List[str]]:
        """
        Parses a single line of a performance script call and returns the parsed values.

        Args:
            line (str): The line to parse.

        Returns:
            list: A list containing the parsed values [addr, symbol, caller], or None if parsing fails.
        """
        pattern = re.compile(r"([0-9a-f]+)\s+(.+?)\s+\((.+)\)")
        matches = pattern.findall(line)
        if not matches:
            logger.warning(f"script one call '{line}' parse failed")
            return None
        addr, symbol, caller = matches[0]
        return [addr, symbol, caller]

    @staticmethod
    def parse_one_header(line: str) -> Optional[List]:
        """
        Parses a single header line from a perf script block.

        Args:
            line (str): The header line to parse.

        Returns:
            list: A list containing the parsed values [command, pid, cpu, time, value, event].
                  Returns None if the line cannot be parsed.
        """
        try:
            try:
                pattern = r"(\S+|\:-\d+)\s+(\d+|-\d+)\s+\[(\d+)]\s+(\d+\.\d+):\s+(\d+)\s+(\S+):"
                command, pid, cpu, time, value, event = re.match(
                    pattern, line.strip()
                ).groups()
            except Exception:
                try:
                    pattern = r"(\d+|-\d+)\s+\[(\d+)]\s+(\d+\.\d+):\s+(\d+)\s+(\S+):"
                    (pid, cpu, time, value, event) = re.match(
                        pattern, line[15:].strip()
                    ).groups()
                    command = line[:15].strip()
                except Exception:
                    pattern = r"(\d+|-\d+)\s+\[(\d+)]\s+(\d+\.\d+):\s+(\d+)\s+(\S+):"
                    (pid, cpu, time, value, event) = re.match(
                        pattern, line[10:].strip()
                    ).groups()
                    command = line[:10].strip()
        except Exception as e:
            logger.warning(f"script header '{line}' parse failed due to: {e}")
            return None

        return [
            command,
            int(pid),
            int(cpu),
            time,
            int(value),
            event,
        ]

    @staticmethod
    def parse_block(lines: List[str]) -> Optional[tuple]:
        """
        Parses the lines of the performance script block.

        Args:
            lines (list): The lines of the performance script block.

        Returns:
            tuple: A tuple containing the parsed header and calls.
        """
        # TODO: There may be some other info like brstackinsn at first
        # TODO: First we just ignore, need to handle it at further stage
        # perf script -F comm,pid,cpu,time,period,event,ip,sym,dso -I --header
        start_index = -1
        line_len = len(lines)
        header = None
        while header is None:
            start_index += 1
            if start_index >= line_len:
                break
            header_data = PerfScriptParser.parse_one_header(lines[start_index])
            if header_data:
                header = PerfScriptHeader(*header_data)
        if header is None:
            logger.warning(f"{lines} can't be parsed by perf script")
            return None
        calls = []
        for line in lines[start_index + 1 :]:
            call_data = PerfScriptParser.parse_one_call(line)
            if call_data:
                calls.append(PerfScriptCall(*call_data))
        return header, calls

    @staticmethod
    def divid_into_blocks(lines: List[str]) -> List[List[str]]:
        """
        Divides the lines into blocks based on empty lines.

        Args:
            lines (list): The list of lines to divide into blocks.

        Returns:
            list: A list of blocks, where each block is a list of lines.

        """
        blocks, cur = [], []
        for l in lines:
            if l:
                cur.append(l)
            elif cur:
                blocks.append(cur)
                cur = []
        if cur:
            blocks.append(cur)
        return blocks


# Data processor class for performance script data
class PerfScriptDataProcessor:
    """
    A class responsible for processing performance script data.
    """

    def __init__(self, blocks: List[PerfScriptBlock]):
        self.blocks = blocks

    def summary_all_cmds(self) -> Dict[str, Dict[str, Set]]:
        """
        Returns a dictionary of commands, each containing a set of CPUs and modules relative to the command.

        Returns:
            Dict[Dict[Set]]: A dictionary of commands, each command contains a dict of 'cpus' and 'modules'. 'cpus' are the set of CPUs, 'modules' are the set of modules.
        """
        cmds = defaultdict(lambda: defaultdict(lambda: set()))
        for b in self.blocks:
            cmd = b.header.command
            cmds[cmd]["cpus"].add(b.header.cpu)
            for s in b.calls:
                cmds[cmd]["modules"].add(s.caller)
        return cmds

    def filter_by_time_window(
        self,
        start: Optional[Decimal | str | float] = None,
        end: Optional[Decimal | str | float] = None,
        deltatime: Optional[Decimal | str | float] = None,
    ) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by a given time window.

        Will generate start and end time by params start / end / deltatime
        If deltatime is None, start / end will be block start / block end if set to none
        If deltatime not None, following is used:
            If start not None and end is None then start = start; end = start + deltatime;
            If start is None and end not None then end = end; start = end - deltatime;
            If start not None and end not None then start = start; end = start + deltatime;
            If start is None and end is None then start = block start; end = start + deltatime

        Args:
            start (Optional[str | float]): The start time of the window.
            end (Optional[str | float]): The end time of the window.
            deltatime (Optional[str | float]): The time duration of the window.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing only the blocks in given time window.
        """
        if len(self.blocks) < 2:
            return PerfScriptDataProcessor(self.blocks)
        block_start = self.blocks[0].header.xytime
        block_end = self.blocks[-1].header.xytime
        logger.debug(f"Script start time: {block_start}")
        logger.debug(f"Script end time: {block_end}")
        try:
            tstart = Decimal(str(start)) if start else block_start
            tend = Decimal(str(end)) if end else block_end
            if deltatime:
                deltatime = Decimal(str(deltatime))
                if start is None and end:
                    tstart = Decimal(str(end)) - deltatime
                else:
                    tend = tstart + deltatime
        except InvalidOperation:
            logger.warning("The time window should be format of float")
            return PerfScriptDataProcessor(self.blocks)
        return PerfScriptDataProcessor(
            [
                b
                for b in self.blocks
                if b.header.xytime >= tstart and b.header.xytime <= tend
            ]
        )

    def filter_by_command(self, command: str) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by a command.

        Args:
            command (str): The command to filter by.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing only the blocks with matching command.
        """
        return PerfScriptDataProcessor(
            [b for b in self.blocks if b.header.command == command]
        )

    def filter_by_commands(self, commands: List[str]) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by a list of commands.

        Args:
            commands (list[str]): A list of commands to filter by.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing only the blocks with matching commands.
        """
        return PerfScriptDataProcessor(
            [b for b in self.blocks if b.header.command in commands]
        )

    def filter_by_pid(self, pid: int) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by process ID.

        Args:
            pid (int): The process ID to filter by.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing the filtered blocks.

        """
        return PerfScriptDataProcessor([b for b in self.blocks if b.header.pid == pid])

    def filter_by_pids(self, pids: List[int]) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by a list of process IDs (pids).

        Args:
            pids (list[int]): A list of process IDs to filter by.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing only the blocks with matching pids.
        """
        return PerfScriptDataProcessor([b for b in self.blocks if b.header.pid in pids])

    def filter_by_cpu(self, cpu: int) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by CPU.

        Args:
            cpu (int): The CPU to filter by.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing the filtered blocks.

        """
        return PerfScriptDataProcessor([b for b in self.blocks if b.header.cpu == cpu])

    def filter_by_cpus(self, cpus: List[int]) -> "PerfScriptDataProcessor":
        """
        Filters the performance script data by the given list of CPUs.

        Args:
            cpus (list[int]): A list of CPUs to filter by.

        Returns:
            PerfScriptDataProcessor: A new PerfScriptDataProcessor object containing only the blocks
            that match the specified CPUs.
        """
        return PerfScriptDataProcessor([b for b in self.blocks if b.header.cpu in cpus])

    def to_raw_dataframe(self) -> pd.DataFrame:
        """
        Converts the blocks to a raw dataframe.
        Returns:
            pd.DataFrame: A pandas DataFrame containing the records from the blocks.
        """
        return pd.DataFrame([b.to_record() for b in self.blocks])

    def to_flat_dataframe(self) -> pd.DataFrame:
        """
        Converts the blocks to a flat dataframe. Can be used for FlameGraph.
        Returns:
            pd.DataFrame: A pandas DataFrame containing the records from the blocks.
        """
        return self.to_raw_dataframe().explode("calls")

    def to_callee_dataframe(self) -> pd.DataFrame:
        """
        Converts the blocks to a callee dataframe. Can be used for metrics analysis.
        Returns:
            pd.DataFrame: A pandas DataFrame containing the records from the blocks.
        """
        df = self.to_raw_dataframe()
        df["callee"] = df["calls"].apply(lambda x: x[0] if x else None)
        df[["addr", "symbol", "caller"]] = df["callee"].apply(
            lambda callee: pd.Series(PerfScriptParser.parse_one_call(callee))
        )
        df = df.drop(columns=["calls", "callee", "caller"])
        df[["symbol", "offset"]] = df["symbol"].str.rsplit("+", n=1, expand=True)
        return df

    @staticmethod
    def transfer_callee_to_metric_dataframe(
        df: pd.DataFrame,
        numerator: str,
        denominator: str,
        metric_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        This method is a class method that can be used to convert a DataFrame containing perf script data into a metric DataFrame.
        It filters the DataFrame based on the numerator and denominator events, pivots the data to create a metric ratio,
        and returns a new DataFrame with the calculated metric.
        It is recommended to use the filtered DataFrame for metric calculation.
        This method is useful for analyzing performance metrics in a structured way.

        Args:
            df (pd.DataFrame): The DataFrame to use for the metric calculation.
            numerator (str): The numerator of the metric, eg. "ll_cache_miss:S".
            denominator (str): The denominator of the metric, eg. "ll_cache:S".
            metric_name (str): The name of the metric, eg. "ll_cache_miss_ratio".
        Returns:
            pd.DataFrame: A pandas DataFrame containing the records from the blocks.
        """
        df_pivot = (
            df[df["event"].isin([numerator, denominator])]
            .pivot_table(
                index=["time", "symbol", "cpu"],
                columns="event",
                values="value",
            )
            .reset_index()
        )
        df_grouped = (
            df_pivot.drop(columns=["cpu", "time"])
            .groupby(["symbol"])
            .sum()
            .reset_index()
        )
        if metric_name is None:
            metric_name = f"{numerator}_ratio"
        df_grouped[metric_name] = df_grouped[numerator] / df_grouped[denominator]
        return df_grouped.sort_values(by=metric_name, ascending=False)

    def to_metric_dataframe(
        self, numerator: str, denominator: str, metric_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Converts the blocks to a metric dataframe. Can be used for metrics analysis.
        It's recommended to use the filtered DataFrame for metric calculation.

        Args:
            numerator (str): The numerator of the metric, eg. "ll_cache_miss:S".
            denominator (str): The denominator of the metric, eg. "ll_cache:S".
            metric_name (str): The name of the metric, eg. "ll_cache_miss_ratio".
        Returns:
            pd.DataFrame: A pandas DataFrame containing the records from the blocks.
        """
        return self.transfer_callee_to_metric_dataframe(
            self.to_callee_dataframe(), numerator, denominator, metric_name
        )


# Main class for handling perf script data
class PerfScriptData:
    """
    Represents a collection of perf script blocks.
    It represents the data obtained from a perf script file.

    Args:
        blocks (list[PerfScriptBlock]): The list of PerfScriptBlock objects.

    Attributes:
        blocks (list[PerfScriptBlock]): The list of PerfScriptBlock objects.
        processor (PerfScriptDataProcessor): The data processor for the blocks.

    Methods:
        __str__(): Returns a string representation of the PerfScriptData object.
        __iter__(): Returns an iterator for iterating over the PerfScriptData object.
        __getitem__(index): Returns the PerfScriptBlock object at the specified index.
        __len__(): Returns the number of PerfScriptBlock objects in the PerfScriptData object.
        from_file(file_path, processes_num=NUM_CORES_PHYSICAL): Creates a PerfScriptData object from a file.
    """

    def __init__(self, blocks: List[PerfScriptBlock]):
        self.blocks: List[PerfScriptBlock] = blocks
        self.processor = PerfScriptDataProcessor(blocks)

    def __str__(self):
        return f"{self.blocks}"

    def __iter__(self):
        return iter(self.blocks)

    def __getitem__(self, index):
        return self.blocks[index]

    def __len__(self):
        return len(self.blocks)

    def __getattribute__(self, name):
        if hasattr(self.processor, name):
            return getattr(self.processor, name)

    @classmethod
    def from_file(
        cls, file_path: str, processes_num=NUM_CORES_PHYSICAL
    ) -> "PerfScriptData":
        """
        Creates a PerfScriptData object from a file.

        Args:
            file_path (str): The path to the file.
            processes_num (int, optional): The number of processes to use for parallel processing. Defaults to NUM_CORES_PHYSICAL.

        Returns:
            PerfScriptData: A new PerfScriptData object created from the file.

        """
        with open(file_path, "r") as f:
            lines = [
                l.strip()
                for l in f.readlines()
                if not (l.startswith("#") or l.startswith("[") or l.startswith("|"))
            ]

        with Pool(processes=processes_num) as pool:
            blocks = pool.map(
                lambda block_lines: PerfScriptParser.parse_block(block_lines),
                PerfScriptParser.divid_into_blocks(lines),
            )

        # remove None in blocks
        blocks = [block for block in blocks if block is not None]
        blocks = [PerfScriptBlock(*block) for block in blocks]

        return cls(blocks)
