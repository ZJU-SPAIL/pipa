from pathlib import Path

import pandas as pd
import pytest

from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.parsers.sar_timeseries_parser import parse_sar_timeseries


# --- Test Assets ---
# Define a fixture to load the comprehensive sar data from the asset file
@pytest.fixture
def comprehensive_sar_content() -> str:
    # Assuming the script runs from the project root
    asset_path = Path("tests/assets/sar_A_comprehensive.txt")
    if not asset_path.exists():
        pytest.fail(f"Test asset not found: {asset_path}")
    return asset_path.read_text()


@pytest.fixture
def complex_perf_content() -> str:
    """Fixture to load the complex perf stat data from the asset file."""
    asset_path = Path("tests/assets/perf_stat_complex.txt")
    if not asset_path.exists():
        pytest.fail(f"Test asset not found: {asset_path}")
    return asset_path.read_text()


class TestPerfStatParser:
    def test_parse_perf_complex_from_asset(self, complex_perf_content):
        """
        Tests the hardened parser against a comprehensive asset file, verifying
        all critical edge cases including floats and percentages are handled.
        """
        df = parse_perf_stat_timeseries(complex_perf_content)

        assert not df.empty
        assert df.shape == (6, 4)  # 6 rows, 4 columns
        assert list(df.columns) == ["timestamp", "value", "unit", "event_name"]

        # 1. Test standard line
        cycles_row = df[df["event_name"] == "cycles"].iloc[0]
        assert cycles_row["value"] == 36416323183
        assert cycles_row["unit"] == ""

        # 2. Test '<not counted>' case
        cache_miss_row = df[df["event_name"] == "cache-misses"].iloc[0]
        assert pd.isna(cache_miss_row["value"])  # Value should be NaN
        assert cache_miss_row["unit"] == ""

        # 3. Test complex name and unit case
        energy_row = df[df["event_name"] == "power/energy-cores/"].iloc[0]
        assert energy_row["value"] == 12345
        assert energy_row["unit"] == "Joules"

        # 4. Test event name with a dash
        l1_row = df[df["event_name"] == "L1-dcache-loads"].iloc[0]
        assert l1_row["value"] == 59861356776
        assert l1_row["unit"] == ""

        # 5. NEW: Test floating point value with GHz unit
        ghz_row = df[df["event_name"] == ""].iloc[0]  # GHz line has empty event_name
        # Find the row with GHz unit
        ghz_rows = df[df["unit"] == "GHz"]
        assert len(ghz_rows) > 0
        ghz_row = ghz_rows.iloc[0]
        assert ghz_row["value"] == pytest.approx(2.430)
        assert ghz_row["unit"] == "GHz"

        # 6. NEW: Test percentage value
        branch_miss_row = df[df["event_name"] == "branch-misses"].iloc[0]
        assert branch_miss_row["value"] == pytest.approx(2.00)
        # Percentage symbol is part of value, not unit
        assert branch_miss_row["unit"] == ""

    @pytest.mark.parametrize("bad_content", ["", "# Just a comment"])
    def test_parse_perf_empty_and_malformed(self, bad_content):
        df = parse_perf_stat_timeseries(bad_content)
        assert df.empty


class TestSarParser:
    def test_parse_sar_a_comprehensive_from_asset(self, comprehensive_sar_content):
        """
        Tests that the parser correctly handles the full, real-world sar -A asset file,
        extracting all defined blocks in one go.
        """
        results = parse_sar_timeseries(comprehensive_sar_content)

        # 1. Assert that all expected blocks are present and not empty
        expected_blocks = [
            "cpu",
            "proc_cswch",
            "paging",
            "io",
            "memory_util",
            "swap_util",
            "load_queue",
            "device_io",
            "network_dev",
            "network_err",
            "tcp_stats",
        ]
        for block in expected_blocks:
            assert block in results, f"Block '{block}' is missing from parse results"
            assert isinstance(results[block], pd.DataFrame), f"Block '{block}' is not a DataFrame"
            assert not results[block].empty, f"Block '{block}' DataFrame is empty"

        # 2. Deep dive validation on key DataFrames
        # Validate CPU block (only 'all' rows are parsed by current logic, let's verify)
        df_cpu = results["cpu"]
        assert df_cpu[df_cpu["CPU"] == "all"].shape[0] > 0
        assert pd.api.types.is_numeric_dtype(df_cpu["pct_usr"])

        # Validate Memory block
        df_mem = results["memory_util"]
        assert "kbmemused" in df_mem.columns
        assert pd.api.types.is_numeric_dtype(df_mem["kbmemused"])

        # Validate Device I/O block
        df_dev = results["device_io"]
        assert "DEV" in df_dev.columns
        assert pd.api.types.is_numeric_dtype(df_dev["tps"])
        assert "sda" in df_dev["DEV"].unique()
        assert "zram0" in df_dev["DEV"].unique()

        # Validate Network block
        df_net = results["network_dev"]
        assert "IFACE" in df_net.columns
        assert pd.api.types.is_numeric_dtype(df_net["rxpck_per_s"])
        assert "lo" in df_net["IFACE"].unique()
        assert "eth0" in df_net["IFACE"].unique()

    def test_parse_sar_empty_input_returns_empty_dict(self):
        results = parse_sar_timeseries("")
        assert isinstance(results, dict)
        assert not results
