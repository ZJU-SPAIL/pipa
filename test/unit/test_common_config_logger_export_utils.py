import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import pipa.common.config as config
from pipa.common import logger as logger_mod
from pipa.common.export import SQLiteConnector, export_dataframe_to_csv
from pipa.utils import get_project_root, p95
from pipa.commands.rules import load_rules


def test_config_constants():
    assert config.LOG_PATH == "./log"
    assert config.CONFIG_DIR == "./data/config"
    assert config.DUMP_DIR == "./data/dump"
    assert config.OUTPUT_DIR == "./data/out"
    assert config.ALL_PATH == [config.LOG_PATH, config.CONFIG_DIR, config.DUMP_DIR, config.OUTPUT_DIR]


def test_logger_set_level_idempotent(monkeypatch):
    # Snapshot handler count to ensure no duplicate handlers created
    handler_count = len(logger_mod.logger.handlers)
    logger_mod.set_level(logging.DEBUG, logging.WARNING)
    assert logger_mod.logger.level == logging.DEBUG
    stream_handler = next((h for h in logger_mod.logger.handlers if isinstance(h, logging.StreamHandler)), None)
    assert stream_handler is not None
    assert stream_handler.level == logging.WARNING
    # Calling again should not add handlers
    logger_mod.set_level(logging.INFO, logging.ERROR)
    assert len(logger_mod.logger.handlers) == handler_count


def test_logger_set_level_bad_input():
    # Should not raise on bad inputs
    logger_mod.set_level(logger_level="NOT_A_LEVEL", print_level=None)


def test_export_dataframe_decorator(tmp_path, monkeypatch):
    @export_dataframe_to_csv(filepath=tmp_path / "out.csv")
    def produce_df():
        return pd.DataFrame({"a": [1, 2]})

    produce_df()
    out_file = tmp_path / "out.csv"
    assert out_file.exists()
    df = pd.read_csv(out_file)
    assert list(df["a"]) == [1, 2]


def test_sqlite_connector_execute_and_export(tmp_path, monkeypatch):
    # Prepare mock connection
    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    conn = DummyConn()
    monkeypatch.setattr(SQLiteConnector, "_connect", lambda self: conn)
    mock_df = pd.DataFrame({"x": [1]})
    with patch("pipa.common.export.pd.read_sql_query", return_value=mock_df) as mock_read:
        connector = SQLiteConnector(str(tmp_path / "db.sqlite"))
        df = connector.execute_query("select 1")
        assert df.equals(mock_df)
        mock_read.assert_called_once()

        out_csv = tmp_path / "table.csv"
        with patch.object(pd.DataFrame, "to_csv") as mock_to_csv:
            connector.export_table_to_csv("table", output_filepath=str(out_csv))
            mock_to_csv.assert_called_once()

        with patch.object(pd.DataFrame, "to_excel") as mock_to_excel:
            connector.export_table_to_excel("table", output_filepath=str(tmp_path / "table.xlsx"))
            mock_to_excel.assert_called_once()


def test_p95_and_project_root(tmp_path, monkeypatch):
    series = pd.Series([1, 2, 3, 4, 5])
    assert p95(series) == pytest.approx(4.8)

    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    p95_df = p95(df)
    assert set(p95_df.index) == {"a", "b"}

    # get_project_root 应返回仓库根目录（包含 pyproject.toml）
    root = get_project_root()
    assert (root / "pyproject.toml").exists()


def test_load_rules_missing_and_valid(tmp_path):
    missing = tmp_path / "none.yaml"
    rules, cfg = load_rules(missing)
    assert rules == [] and cfg == {}

    valid = tmp_path / "rules.yaml"
    valid.write_text(
        """
config:
  expected_cpus_str: "0-1"
rules:
  - name: sample
    precondition: "True"
    finding: "ok"
"""
    )
    rules, cfg = load_rules(valid)
    assert cfg.get("expected_cpus_str") == "0-1"
    assert len(rules) == 1 and rules[0]["name"] == "sample"
