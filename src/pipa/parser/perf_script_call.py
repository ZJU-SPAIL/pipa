import re
from multiprocessing import Pool
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL


class PerfScriptCall:
    def __init__(self, addr, symbol, caller):
        self.addr: str = addr
        self.symbol: str = symbol
        self.caller: str = caller

    def __str__(self):
        return f"{self.addr} {self.symbol} ({self.caller})"

    @staticmethod
    def parse_one_call(line: str):
        try:
            addr, symbol, caller = re.match(r"(\S+)\s+(.*?)\s+\((\S+)\)", line).groups()
        except Exception as e:
            print(e)
            return None
        return [addr, symbol, caller]

    @classmethod
    def from_line(cls, line: str):
        return cls(*cls.parse_one_call(line))


class PerfScriptHeader:
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
        return cls(*cls.parse_one_header(line))


class PerfScriptBlock:
    def __init__(self, header: PerfScriptHeader, calls: list[PerfScriptCall]):
        self.header: PerfScriptHeader = header
        self.calls: list[PerfScriptCall] = calls

    def __str__(self):
        return f"{self.header}\n{self.calls}"

    @staticmethod
    def parse_block(lines: list):
        header = PerfScriptHeader.from_line(lines[0])
        calls = [PerfScriptCall.from_line(line) for line in lines[1:]]
        return header, calls

    @classmethod
    def from_lines(cls, lines: list):
        return cls(*cls.parse_block(lines))


class PerfScriptData:
    def __init__(self, blocks: list):
        self.blocks = blocks

    def __str__(self):
        return f"{self.blocks}"

    @staticmethod
    def divid_into_blocks(lines: list):
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
        with open(file_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith("#")]

        with Pool(processes=processes_num) as pool:
            blocks = pool.map(PerfScriptBlock.from_lines, cls.divid_into_blocks(lines))

        return cls(blocks)
