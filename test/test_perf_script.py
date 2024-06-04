import pytest
from pipa.parser.perf_script import parse_one_line


def test_parse_one_line():
    lines: list = [
        "perf 1585183 [000] 4492421.247039:          1        cpu_core/instructions/:  ffffffff9030a814 perf_ctx_enable+0x24 ([kernel.kallsyms])",
        "perf 1585183 [000] 4492421.247039: 1 cpu_core/instructions/:  ffffffff9030a814 perf_ctx_enable+0x24 ([kernel.kallsyms])",
        " :-1      -1 [001] 4492431.253176:      28168       cpu_core/branch-misses/:  ffffffff90172282 __update_load_avg_se+0xa2 ([kernel.kallsyms])",
        "perf 1097778 [000] 45703.470045:      21326          ref-cycles:      558d5f421ffb  evlist_cpu_iterator__next+0x2b (/usr/lib/linux-tools-5.15.0-89/perf)",
        "perf 1585183 [000] 4492421.247039:    21326          cpu_core/instructions/:  ffffffff9030a814 perf_ctx_enable+0x24 (/kernel/kallsyms)",
        "node 3174706 [028] 1878680.878876:   19098947 branch-instructions:           1e93f03 std::vector<v8::internal::compiler::StateValueDescriptor, v8::internal::ZoneAllocator<v8::internal::compiler::StateValueDescriptor> >::_M_fill_insert+0x113 (/mnt/hdd/users/xyjiang/.vscode-server/bin/0ee08df0cf4527e40edc9aa28f4b5bd38bbff2b2/node)",
    ]

    expected_output_list: list = [
        [
            "perf",
            1585183,
            0,
            "4492421.247039",
            1,
            "cpu_core/instructions/",
            "ffffffff9030a814",
            "perf_ctx_enable+0x24",
            "[kernel.kallsyms]",
        ],
        [
            "perf",
            1585183,
            0,
            "4492421.247039",
            1,
            "cpu_core/instructions/",
            "ffffffff9030a814",
            "perf_ctx_enable+0x24",
            "[kernel.kallsyms]",
        ],
        [
            ":-1",
            -1,
            1,
            "4492431.253176",
            28168,
            "cpu_core/branch-misses/",
            "ffffffff90172282",
            "__update_load_avg_se+0xa2",
            "[kernel.kallsyms]",
        ],
        [
            "perf",
            1097778,
            0,
            "45703.470045",
            21326,
            "ref-cycles",
            "558d5f421ffb",
            "evlist_cpu_iterator__next+0x2b",
            "/usr/lib/linux-tools-5.15.0-89/perf",
        ],
        [
            "perf",
            1585183,
            0,
            "4492421.247039",
            21326,
            "cpu_core/instructions/",
            "ffffffff9030a814",
            "perf_ctx_enable+0x24",
            "/kernel/kallsyms",
        ],
        [
            "node",
            3174706,
            28,
            "1878680.878876",
            19098947,
            "branch-instructions",
            "1e93f03",
            "std::vector<v8::internal::compiler::StateValueDescriptor, v8::internal::ZoneAllocator<v8::internal::compiler::StateValueDescriptor> >::_M_fill_insert+0x113",
            "/mnt/hdd/users/xyjiang/.vscode-server/bin/0ee08df0cf4527e40edc9aa28f4b5bd38bbff2b2/node",
        ],
    ]
    for i, line in enumerate(lines):
        assert parse_one_line(line) == expected_output_list[i]


if __name__ == "__main__":
    pytest.main([__file__])
