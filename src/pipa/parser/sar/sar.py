from .sar_parser import SarParser
from .sar_processor import SarProcessor
from .sar_plotter import SarPlotter


# Main class, coordinating parser, processor, and plotter
class SarData:
    def __init__(self, sar_string: str):
        """
        Initialize a SAR object with the given SAR string.

        Args:
            sar_string (str): The SAR string to parse.
        """
        parsed_data = SarParser.parse_sar_string(sar_string)
        self.processor = SarProcessor(parsed_data)
        self.plotter = SarPlotter(self.processor)

    def __getattr__(self, name):
        # Delegate methods to the processor or plotter
        if hasattr(self.processor, name):
            return getattr(self.processor, name)
        if hasattr(self.plotter, name):
            return getattr(self.plotter, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    @classmethod
    def init_with_sar_txt(cls, sar_txt_path: str):
        """
        Initializes the SarData object using a SAR text file.

        Args:
            sar_txt_path (str): Path to the SAR text file.

        Returns:
            SarData: Initialized SarData object.
        """
        with open(sar_txt_path, "r") as f:
            sar_content = f.readlines()
        return cls(sar_content)

    @classmethod
    def init_with_sar_bin(cls, sar_bin_path: str):
        """
        Initializes the SarData object using a SAR binary file.

        Args:
            sar_bin_path (str): Path to the SAR binary file.

        Returns:
            SarData: Initialized SarData object.
        """
        sar_content = SarParser.parse_sar_bin_to_txt(sar_bin_path)
        return cls(sar_content)
