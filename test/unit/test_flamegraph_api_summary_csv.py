import io
import csv

import pytest

from pipa.analysis.flamegraph import api, summary, csv_export
from pipa.analysis.flamegraph.analyzer import FoldedAnalyzer, SymbolStat, StackStat


def sample_stacks():
    return {
        "proc;foo;bar": 10,
        "proc;foo;baz": 5,
        "proc;other": 1,
    }


def test_api_subset_and_analyze_mapping():
    stacks = sample_stacks()
    subset = api.subset_mapping_by_symbol(stacks, "bar")
    assert subset == {"proc;foo;bar": 10}
    analyzer = api.analyze_mapping(stacks)
    top = analyzer.topk_symbols(1)[0]
    assert top.symbol in {"foo", "bar"}


def test_summary_validate_and_filters():
    analyzer = FoldedAnalyzer(sample_stacks())
    with pytest.raises(ValueError):
        summary.summarize_analyzer(analyzer, topk_symbols=-1)
    with pytest.raises(ValueError):
        summary.summarize_analyzer(analyzer, order="bad")

    res = summary.summarize_analyzer(
        analyzer,
        topk_symbols=2,
        topk_stacks=2,
        symbol_filter=None,
        proc_prefix="proc",
    )
    assert res["top_symbols"]
    assert res["top_stacks"]


def test_summary_subset_and_path_stats(tmp_path):
    stacks = sample_stacks()
    text_path = tmp_path / "folded.txt"
    text_path.write_text("\n".join([f"{k} {v}" for k, v in stacks.items()]))

    subset = summary.subset_summary_from_file(str(text_path), "bar")
    assert subset["top_symbols"]

    paths = summary.path_stats_from_file(str(text_path), limit=1)
    assert paths["paths"] and paths["truncated"] is True

    with pytest.raises(ValueError):
        summary.path_stats_from_file(str(text_path), limit=-1)


def test_csv_export_writes_headers(tmp_path):
    out_sym = tmp_path / "sym.csv"
    out_stack = tmp_path / "stack.csv"

    csv_export.write_symbol_stats_csv(str(out_sym), [], total=None)
    csv_export.write_stack_stats_csv(str(out_stack), [], total=None)

    with out_sym.open() as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == ["symbol", "inclusive", "leaf"]

    with out_stack.open() as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == ["stack", "weight"]


def test_csv_export_with_shares(tmp_path):
    out_sym = tmp_path / "sym.csv"
    out_stack = tmp_path / "stack.csv"

    sym_stats = [SymbolStat("foo", 10, 5)]
    stack_stats = [StackStat("proc;foo", 10)]
    csv_export.write_symbol_stats_csv(str(out_sym), sym_stats, total=20)
    csv_export.write_stack_stats_csv(str(out_stack), stack_stats, total=10)

    assert "%" in out_sym.read_text()
    assert "%" in out_stack.read_text()
