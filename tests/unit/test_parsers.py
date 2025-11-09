from pathlib import Path

import pandas as pd
import pytest

from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries


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
        assert df.shape == (6, 5)
        assert list(df.columns) == ["timestamp", "cpu", "value", "unit", "event_name"]

        assert (df["cpu"] == "all").all()

        cycles_row = df[df["event_name"] == "cycles"].iloc[0]
        assert cycles_row["value"] == 36416323183
        assert cycles_row["unit"] == ""

        cache_miss_row = df[df["event_name"] == "cache-misses"].iloc[0]
        assert pd.isna(cache_miss_row["value"])
        assert cache_miss_row["unit"] == ""

        energy_row = df[df["event_name"] == "power/energy-cores/"].iloc[0]
        assert energy_row["value"] == 12345
        assert energy_row["unit"] == "Joules"

        l1_row = df[df["event_name"] == "L1-dcache-loads"].iloc[0]
        assert l1_row["value"] == 59861356776
        assert l1_row["unit"] == ""

        ghz_rows = df[df["unit"] == "GHz"]
        assert len(ghz_rows) > 0
        ghz_row = ghz_rows.iloc[0]
        assert ghz_row["value"] == pytest.approx(2.430)
        assert ghz_row["unit"] == "GHz"

        branch_miss_row = df[df["event_name"] == "branch-misses"].iloc[0]
        assert branch_miss_row["value"] == pytest.approx(2.00)
        assert branch_miss_row["unit"] == ""

    @pytest.mark.parametrize("bad_content", ["", "# Just a comment"])
    def test_parse_perf_empty_and_malformed(self, bad_content):
        df = parse_perf_stat_timeseries(bad_content)
        assert df.empty
