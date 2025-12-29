"""Rule loading and rendering helpers for analysis reports."""

from __future__ import annotations

import keyword
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml
from markdown_it import MarkdownIt

log = logging.getLogger(__name__)


def load_rules(rules_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load decision tree rules and configuration from YAML."""

    if not rules_path.exists():
        log.warning("Rule file %s does not exist; skipping rule engine.", rules_path)
        return [], {}
    with open(rules_path, "r", encoding="utf-8") as file_handle:
        data = yaml.safe_load(file_handle)
    return data.get("rules", []), data.get("config", {})


def _format_rule_to_html_list(
    rule_node: Dict[str, Any],
    df_dict: Dict[str, pd.DataFrame],
    context: Dict[str, Any],
    md: MarkdownIt,
    parent_is_active: bool = True,
    depth: int = 0,
) -> Tuple[str, str]:
    """Recursively convert a rule tree into HTML list entries and findings."""

    indent = "  " * depth
    rule_name = rule_node.get("name", "Unnamed")
    precondition = rule_node.get("precondition", "True")
    log.debug("%s🔎 Evaluating Node: '%s'", indent, rule_name)
    log.debug("%s   Condition: %s", indent, precondition)

    is_self_condition_met = False
    try:
        variables_in_precondition = re.findall(r"\b([a-zA-Z_]\w*)\b", precondition)
        actual_variables = [
            var for var in variables_in_precondition if var not in keyword.kwlist
        ]
        relevant_context = {
            var: context.get(var, "Not Found") for var in set(actual_variables)
        }
        log.debug("%s   Context Vars: %s", indent, relevant_context)
        result = eval(
            precondition, {"pd": pd}, {"df": df_dict, **context}
        )  # noqa: S307
        if result:
            is_self_condition_met = True
        log.debug("%s   ▶️ Result: %s", indent, is_self_condition_met)
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("%s   ❌ Error evaluating condition: %s", indent, exc)

    is_truly_active = parent_is_active and is_self_condition_met
    is_root = rule_node.get("name") == "PIPA 根因分析"
    if not is_truly_active and not is_root:
        log.debug("%s   ✂️ Pruning branch (inactive).", indent)
        return "", ""

    finding_html = ""
    if is_truly_active and (finding_template := rule_node.get("finding")):
        try:
            formatted_finding = finding_template.format(**context)
            if formatted_finding.strip():
                log.info("%s✅ FINDING TRIGGERED: '%s'", indent, rule_name)
                finding_html = (
                    f"<div class='finding-box'>{md.render(formatted_finding)}</div>"
                )
        except KeyError as exc:
            finding_html = f"<div class='finding-box error'>数据缺失: {exc}</div>"

    active_class = "active-node" if is_truly_active else ""
    li_html = f"<li class='{active_class}'><span>{rule_node['name']}</span>"
    all_child_findings: List[str] = []
    child_lis: List[str] = []

    if sub_rules := rule_node.get("sub_rules"):
        log.debug("%s   Descending into sub-rules...", indent)
        for sub_rule in sub_rules:
            sub_li_html, sub_finding_html = _format_rule_to_html_list(
                sub_rule,
                df_dict,
                context,
                md,
                parent_is_active=is_truly_active,
                depth=depth + 1,
            )
            if sub_li_html:
                child_lis.append(sub_li_html)
            if sub_finding_html:
                all_child_findings.append(sub_finding_html)

    if child_lis:
        li_html += "<ul>" + "".join(child_lis) + "</ul>"
    li_html += "</li>"
    final_finding_html = finding_html + "".join(all_child_findings)
    return li_html, final_finding_html


def format_rules_to_html_tree(
    rules_config: List[Dict[str, Any]],
    df_dict: Dict[str, pd.DataFrame],
    context: Dict[str, Any],
    md: MarkdownIt,
) -> Tuple[str, str, str]:
    """Render rule evaluation results into HTML fragments."""

    if not rules_config:
        return "", "", ""

    audit_html_parts: List[str] = []
    tree_html_parts: List[str] = []
    findings_html_parts: List[str] = []

    for rule_node in rules_config:
        li_html, finding_html = _format_rule_to_html_list(
            rule_node, df_dict, context, md
        )
        if finding_html:
            findings_html_parts.append(finding_html)
        if rule_node.get("name") == "配置合规性检查":
            if li_html:
                audit_html_parts.append(li_html)
        else:
            if li_html:
                tree_html_parts.append(li_html)

    audit_section_html = ""
    if audit_html_parts:
        audit_section_html = (
            f"<div class=\"audit-panel\"><ul>{''.join(audit_html_parts)}</ul></div>"
        )

    tree_section_html = ""
    if tree_html_parts:
        tree_section_html = (
            f"<div class=\"tree\"><ul>{''.join(tree_html_parts)}</ul></div>"
        )

    full_findings_html = "".join(findings_html_parts)
    return audit_section_html, tree_section_html, full_findings_html
