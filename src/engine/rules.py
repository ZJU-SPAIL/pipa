import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml
from markdown_it import MarkdownIt

log = logging.getLogger(__name__)


def load_rules(rules_path: Path) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """从 YAML 文件加载规则和配置。"""
    if not rules_path.exists():
        log.warning(f"规则文件 {rules_path} 不存在，跳过规则引擎。")
        return [], {}
    with open(rules_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("rules", []), data.get("config", {})


def _evaluate_node(
    rule_node: Dict[str, Any], df_dict: Dict[str, pd.DataFrame], context: Dict[str, Any], findings: List[str]
):
    """递归地评估一个规则节点及其子节点。"""
    try:
        precondition_met = eval(rule_node["precondition"], {"pd": pd}, {"df": df_dict, **context})
        if not precondition_met:
            return

        if "finding" in rule_node:
            finding = rule_node["finding"].format(**context)
            findings.append(finding)

        for sub_rule in rule_node.get("sub_rules", []):
            _evaluate_node(sub_rule, df_dict, context, findings)

    except Exception as e:
        log.debug(f"评估规则 '{rule_node.get('name', 'Unnamed')}' 时出错: {e}")


def run_rules_engine(
    df_dict: Dict[str, pd.DataFrame], rules_config: List[Dict[str, Any]], context: Dict[str, Any]
) -> List[str]:
    """在一个 DataFrame 字典上执行一组层次化的规则。"""
    findings: List[str] = []
    if not df_dict or not rules_config:
        return findings

    for root_rule in rules_config:
        _evaluate_node(root_rule, df_dict, context, findings)

    return findings


def _format_rule_to_html_list(
    rule_node: Dict[str, Any],
    df_dict: Dict[str, pd.DataFrame],
    context: Dict[str, Any],
    md: MarkdownIt,
) -> tuple[str, str]:
    """
    递归地将节点转换为HTML <li>，并单独返回其finding HTML。
    返回 (li_html_string, finding_html_string)。
    """
    is_active_node = False
    try:
        if eval(rule_node["precondition"], {"pd": pd}, {"df": df_dict, **context}):
            is_active_node = True
    except Exception:
        is_active_node = False

    finding_html = ""
    if is_active_node and (finding_template := rule_node.get("finding")):
        try:
            formatted_finding = finding_template.format(**context)
            finding_html = f"<div class='finding-box'>{md.render(formatted_finding)}</div>"
        except KeyError as e:
            finding_html = f"<div class='finding-box error'>数据缺失: {e}</div>"

    active_class = "active-node" if is_active_node else ""
    li_html = f"<li class='{active_class}'><span>{rule_node['name']}</span>"

    all_child_findings = []
    if sub_rules := rule_node.get("sub_rules"):
        li_html += "<ul>"
        for sub_rule in sub_rules:
            sub_li_html, sub_finding_html = _format_rule_to_html_list(sub_rule, df_dict, context, md)
            li_html += sub_li_html
            if sub_finding_html:
                all_child_findings.append(sub_finding_html)
        li_html += "</ul>"

    li_html += "</li>"

    final_finding_html = finding_html + "".join(all_child_findings)

    return li_html, final_finding_html


def format_rules_to_html_tree(
    rules_config: List[Dict[str, Any]],
    df_dict: Dict[str, pd.DataFrame],
    context: Dict[str, Any],
    md: MarkdownIt,
) -> tuple[str, str]:
    """将整个规则配置转换为一个树状图HTML和一个结论HTML。"""
    if not rules_config:
        return "", ""

    tree_html_parts = []
    findings_html_parts = []

    for root_rule in rules_config:
        tree_html, findings_html = _format_rule_to_html_list(root_rule, df_dict, context, md)
        tree_html_parts.append(tree_html)
        findings_html_parts.append(findings_html)

    full_tree_html = f'<div class="tree"><ul>{"".join(tree_html_parts)}</ul></div>'
    full_findings_html = "".join(findings_html_parts)

    return full_tree_html, full_findings_html


def calculate_context_metrics(df_dict: Dict[str, pd.DataFrame], static_info: Dict[str, Any]) -> Dict[str, Any]:
    """从 DataFrame 字典和静态信息中预先计算所有衍生指标。"""
    context: Dict[str, Any] = {
        "num_cpu": 1,
        "total_cpu": 0.0,
        "avg_cswch": 0.0,
        "total_tps": 0.0,
        "avg_swaps": 0.0,
        "avg_load1": 0.0,
        "ipc": 0.0,
        "branch_miss_rate": 0.0,
        "l3_cache_miss_rate": 0.0,
    }

    if static_info and (cpu_info := static_info.get("cpu_info")):
        context["num_cpu"] = cpu_info.get("CPUs_Count", 1)

    df_cpu = df_dict.get("cpu")
    if df_cpu is not None and not df_cpu.empty:
        context["total_cpu"] = df_cpu.get("%user", pd.Series(0)).mean() + df_cpu.get("%system", pd.Series(0)).mean()

    df_cswch = df_dict.get("proc_cswch")
    if df_cswch is not None and not df_cswch.empty:
        context["avg_cswch"] = df_cswch.get("cswch_per_s", pd.Series(0)).mean()

    df_io = df_dict.get("device_io")
    if df_io is not None and not df_io.empty:
        context["total_tps"] = df_io.get("tps", pd.Series(0)).sum()

    df_paging = df_dict.get("paging")
    if df_paging is not None and not df_paging.empty:
        context["avg_swaps"] = (
            df_paging.get("pswpin_per_s", pd.Series(0)).mean() + df_paging.get("pswpout_per_s", pd.Series(0)).mean()
        )

    df_load = df_dict.get("load_queue")
    if df_load is not None and not df_load.empty:
        context["avg_load1"] = df_load.get("ldavg-1", pd.Series(0)).mean()

    if (df_perf := df_dict.get("perf")) is not None and not df_perf.empty:
        df_perf_all = df_perf[df_perf["cpu"] == "all"].copy() if "cpu" in df_perf.columns else df_perf

        instructions = df_perf_all[df_perf_all["event_name"].isin(["instructions", "inst_retired.any"])]["value"].sum()
        cycles = df_perf_all[df_perf_all["event_name"].isin(["cycles", "cpu-cycles"])]["value"].sum()
        if cycles > 0:
            context["ipc"] = instructions / cycles

        branch_instructions = df_perf_all[df_perf_all["event_name"] == "branch-instructions"]["value"].sum()
        branch_misses = df_perf_all[df_perf_all["event_name"] == "branch-misses"]["value"].sum()
        if branch_instructions > 0:
            context["branch_miss_rate"] = (branch_misses / branch_instructions) * 100

        llc_loads = df_perf_all[df_perf_all["event_name"].isin(["LLC-loads", "ll_cache_rd"])]["value"].sum()
        llc_misses = df_perf_all[df_perf_all["event_name"].isin(["LLC-load-misses", "ll_cache_miss_rd"])]["value"].sum()
        if llc_loads > 0:
            context["l3_cache_miss_rate"] = (llc_misses / llc_loads) * 100

    return context
