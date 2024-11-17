from typing import Dict
import pandas as pd


class PerfBuildidData:
    """
    Represents a collection of buildid.
    """

    def __init__(self, buildid_lists: Dict[str, str]):
        self.buildid_lists = buildid_lists
        """The buildid_lists are dict, key is module name while value is buildid"""

    def __str__(self):
        return f"{self.buildid_lists}"

    def __iter__(self):
        return iter(self.buildid_lists)

    def __getitem__(self, key: str):
        return self.buildid_lists[key]

    def __len__(self):
        return len(self.buildid_lists)

    @classmethod
    def from_file(cls, file_path: str):
        """
        Creates a PerfBuildidData object from a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            PerfBuildidData: A new PerfBuildidData object created from the file.
        """
        buildid_lists = {}
        with open(file_path, "r") as f:
            for l in f.readlines():
                # buildid : module name
                l = l.strip().split(" ", maxsplit=1)
                # module name : buildid
                try:
                    buildid_lists[str(l[1])] = l[0]
                except IndexError:
                    continue

        return cls(buildid_lists)

    def to_raw_dataframe(self):
        """
        Converts the buildid_lists to a raw dataframe.
        Returns:
            pd.DataFrame: A pandas DataFrame containing module name -> buildid.
        """
        mname = "module name"
        bid = "buildid"
        data = {mname: [], bid: []}
        for m, b in self.buildid_lists.items():
            data[mname].append(m)
            data[bid].append(b)
        return pd.DataFrame(data)
