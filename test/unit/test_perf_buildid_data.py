import pandas as pd

from pipa.parser.perf_buildid import PerfBuildidData


def test_perf_buildid_from_file_and_access(tmp_path):
    content = """
1234 moduleA
5678 moduleB
malformed_line_without_space
"""
    path = tmp_path / "buildid.txt"
    path.write_text(content)

    data = PerfBuildidData.from_file(str(path))

    assert len(data) == 2
    assert data["moduleA"] == "1234"
    assert set(data.get_modules()) == {"moduleA", "moduleB"}
    assert set(data.get_buildids()) == {"1234", "5678"}
    assert set(iter(data)) == {"moduleA", "moduleB"}
    assert "moduleA" in str(data)

    df = data.to_raw_dataframe()
    assert list(df.columns) == ["module name", "buildid"]
    assert df.shape == (2, 2)
    assert dict(zip(df["module name"], df["buildid"])) == {
        "moduleA": "1234",
        "moduleB": "5678",
    }
