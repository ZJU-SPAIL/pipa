from pathlib import Path

import pytest

from pipa.parser.perf_stat_timeseries_parser import parse as parse_perf_stat


@pytest.fixture
def complex_perf_content() -> str:
    """Load the complex perf stat data from the local test asset."""

    asset_path = (
        Path(__file__).resolve().parent.parent / "assets" / "perf_stat_complex.txt"
    )
    if not asset_path.exists():
        pytest.fail(f"Test asset not found: {asset_path}")
    return asset_path.read_text(encoding="utf-8")


class TestPerfStatParser:

    def test_parse_perf_complex_from_asset(self, complex_perf_content):
        """Validate parsing of the hardened perf stat format using a fixture asset."""

        result = parse_perf_stat(complex_perf_content)
        df = result["events"]

        assert not df.empty
        assert df.shape == (4, 6)
        assert list(df.columns) == [
            "timestamp",
            "cpu",
            "value",
            "unit",
            "event_name",
            "type",
        ]
        assert (df["cpu"] == "CPU0").all()

        cycles_row = df[df["event_name"] == "cycles"].iloc[0]
        assert cycles_row["value"] == 36416323183
        assert cycles_row["unit"] == ""

        energy_row = df[df["event_name"] == "power/energy-cores/"].iloc[0]
        assert energy_row["value"] == 12345
        assert energy_row["unit"] == "Joules"

        l1_row = df[df["event_name"] == "L1-dcache-loads"].iloc[0]
        assert l1_row["value"] == 59861356776
        assert l1_row["unit"] == ""

        branch_miss_row = df[df["event_name"] == "branch-misses"].iloc[0]
        assert branch_miss_row["value"] == 2.00
        assert branch_miss_row["unit"] == ""

    @pytest.mark.parametrize("bad_content", ["", "# Just a comment"])
    def test_parse_perf_empty_and_malformed(self, bad_content):
        result = parse_perf_stat(bad_content)
        df = result["events"]
        assert df.empty
