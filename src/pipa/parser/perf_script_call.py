import re
from multiprocessing import Pool
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL


class PerfScriptCall:
    """
    Represents a single performance script call.

    Attributes:
        addr (str): The address of the call.
        symbol (str): The symbol associated with the call.
        caller (str): The caller of the call.
    """

    def __init__(self, addr, symbol, caller):
        self.addr: str = addr
        self.symbol: str = symbol
        self.caller: str = caller

    def __str__(self):
        return f"{self.addr} {self.symbol} ({self.caller})"

    @staticmethod
    def parse_one_call(line: str):
        """
        Parses a single line of a performance script call and returns the parsed values.

        Args:
            line (str): The line to parse.

        Returns:
            list: A list containing the parsed values [addr, symbol, caller], or None if parsing fails.
        """
        try:
            pattern = re.compile(r"([0-9a-f]+)\s+(.+?)\s+\((.+)\)")
            matches = pattern.findall(line)
            addr, symbol, caller = matches[0]
        except Exception as e:
            print(e)
            return None
        return [addr, symbol, caller]

    @classmethod
    def from_line(cls, line: str):
        """
        Creates a PerfScriptCall instance from a single line of a performance script call.

        Args:
            line (str): The line to create the instance from.

        Returns:
            PerfScriptCall: The created PerfScriptCall instance.
        """
        return cls(*cls.parse_one_call(line))


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

    def __init__(self, command, pid, cpu, time, value, event):
        self.command: str = command
        self.pid: int = pid
        self.cpu: int = cpu
        self.time: str = time
        self.value: int = value
        self.event: str = event

    def __str__(self):
        return f"{self.command} {self.pid} {self.cpu} {self.time} {self.value} {self.event}"

    @staticmethod
    def parse_one_header(line: str):
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
            except Exception as e:
                pattern = r"(\d+|-\d+)\s+\[(\d+)]\s+(\d+\.\d+):\s+(\d+)\s+(\S+):"
                (pid, cpu, time, value, event) = re.match(
                    pattern, line[15:].strip()
                ).groups()

                command = line[:15].strip()

        except Exception as e:
            print(e)
            return None

        return [
            command,
            int(pid),
            int(cpu),
            time,
            int(value),
            event,
        ]

    @classmethod
    def from_line(cls, line):
        """
        Creates a PerfScriptHeader object from a header line.

        Args:
            line (str): The header line.

        Returns:
            PerfScriptHeader: The created PerfScriptHeader object.
        """
        return cls(*cls.parse_one_header(line))


class PerfScriptBlock:
    """
    Represents a block of performance script.

    Attributes:
        header (PerfScriptHeader): The header of the performance script block.
        calls (list[PerfScriptCall]): The list of performance script calls.

    Methods:
        __str__(): Returns a string representation of the PerfScriptBlock object.
        parse_block(lines: list): Parses the lines of the performance script block.
        from_lines(lines: list): Creates a PerfScriptBlock object from the lines of the performance script block.
    """

    def __init__(self, header: PerfScriptHeader, calls: list[PerfScriptCall]):
        self.header: PerfScriptHeader = header
        self.calls: list[PerfScriptCall] = calls

    def __str__(self):
        return f"{self.header}\n{self.calls}"

    @staticmethod
    def parse_block(lines: list):
        """
        Parses the lines of the performance script block.

        Args:
            lines (list): The lines of the performance script block.

        Returns:
            tuple: A tuple containing the parsed header and calls.
        """
        header = PerfScriptHeader.from_line(lines[0])
        calls = [PerfScriptCall.from_line(line) for line in lines[1:]]
        return header, calls

    @classmethod
    def from_lines(cls, lines: list):
        """
        Creates a PerfScriptBlock object from the lines of the performance script block.

        Args:
            lines (list): The lines of the performance script block.

        Returns:
            PerfScriptBlock: The created PerfScriptBlock object.
        """
        return cls(*cls.parse_block(lines))


class PerfScriptData:
    """
    Represents a collection of performance script blocks.
    It represents the data obtained from a perf script file.

    Args:
        blocks (list[PerfScriptBlock]): The list of PerfScriptBlock objects.

    Attributes:
        blocks (list[PerfScriptBlock]): The list of PerfScriptBlock objects.

    Methods:
        __str__(): Returns a string representation of the PerfScriptData object.
        __iter__(): Returns an iterator for iterating over the PerfScriptData object.
        __getitem__(index): Returns the PerfScriptBlock object at the specified index.
        __len__(): Returns the number of PerfScriptBlock objects in the PerfScriptData object.
        filter_by_pid(pid, cpu=None): Filters the PerfScriptData object by process ID and CPU.
        divid_into_blocks(lines): Divides the lines into blocks based on empty lines.
        from_file(file_path, processes_num=NUM_CORES_PHYSICAL): Creates a PerfScriptData object from a file.

    """

    def __init__(self, blocks: list[PerfScriptBlock]):
        self.blocks: PerfScriptBlock = blocks

    def __str__(self):
        return f"{self.blocks}"

    def __iter__(self):
        return iter(self.blocks)

    def __getitem__(self, index):
        return self.blocks[index]

    def __len__(self):
        return len(self.blocks)

    def filter_by_pid(self, pid: int):
        """
        Filters the PerfScriptData object by process ID.

        Args:
            pid (int): The process ID to filter by.

        Returns:
            PerfScriptData: A new PerfScriptData object containing the filtered blocks.

        """
        return PerfScriptData([b for b in self.blocks if b.header.pid == pid])

    def filter_by_pids(self, pids: list[int]):
        """
        Filters the PerfScriptData object by a list of process IDs (pids).

        Args:
            pids (list[int]): A list of process IDs to filter by.

        Returns:
            PerfScriptData: A new PerfScriptData object containing only the blocks with matching pids.
        """
        return PerfScriptData([b for b in self.blocks if b.header.pid in pids])

    def filter_by_cpu(self, cpu: int):
        """
        Filters the PerfScriptData object by CPU.

        Args:
            cpu (int): The CPU to filter by.

        Returns:
            PerfScriptData: A new PerfScriptData object containing the filtered blocks.

        """
        return PerfScriptData([b for b in self.blocks if b.header.cpu == cpu])

    def filter_by_cpus(self, cpus: list[int]):
        """
        Filters the PerfScriptData object by the given list of CPUs.

        Args:
            cpus (list[int]): A list of CPUs to filter by.

        Returns:
            PerfScriptData: A new PerfScriptData object containing only the blocks
            that match the specified CPUs.
        """
        return PerfScriptData([b for b in self.blocks if b.header.cpu in cpus])

    @staticmethod
    def divid_into_blocks(lines: list):
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

    @classmethod
    def from_file(cls, file_path: str, processes_num=NUM_CORES_PHYSICAL):
        """
        Creates a PerfScriptData object from a file.

        Args:
            file_path (str): The path to the file.
            processes_num (int, optional): The number of processes to use for parallel processing. Defaults to NUM_CORES_PHYSICAL.

        Returns:
            PerfScriptData: A new PerfScriptData object created from the file.

        """
        with open(file_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith("#")]

        with Pool(processes=processes_num) as pool:
            blocks = pool.map(PerfScriptBlock.from_lines, cls.divid_into_blocks(lines))

        return cls(blocks)
