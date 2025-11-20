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
    """递归地评估一个规则节点及其子节点 (用于提取纯文本 findings)。"""
    try:
        precondition_met = eval(rule_node["precondition"], {"pd": pd}, {"df": df_dict, **context})
        if not precondition_met:
            return

        if "finding" in rule_node:
            finding = rule_node["finding"].format(**context)
            # 过滤掉为了结构存在但不需要显示的空 finding
            if finding.strip():
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
    parent_is_active: bool = True,
) -> tuple[str, str]:
    """
    递归地将节点转换为HTML <li>，并单独返回其finding HTML。
    实现了“剪枝”逻辑：未激活的分支将完全不渲染，只展示案发现场。
    """
    # 1. 计算当前节点的激活状态
    is_self_condition_met = False
    try:
        if eval(rule_node["precondition"], {"pd": pd}, {"df": df_dict, **context}):
            is_self_condition_met = True
    except Exception:
        pass

    # 真正的激活状态 = 父节点激活 AND 自己条件满足
    is_truly_active = parent_is_active and is_self_condition_met

    # === 核心修改：剪枝逻辑 (Pruning) ===
    # 规则：如果节点未激活，且不是根节点，则直接丢弃，不生成 HTML。
    # 这样前端树形图将只包含红色的、被触发的路径。
    is_root = rule_node.get("name") == "PIPA 根因分析"

    if not is_truly_active and not is_root:
        return "", ""

    # 2. 生成 Finding HTML (结论文本框)
    finding_html = ""
    if is_truly_active and (finding_template := rule_node.get("finding")):
        try:
            formatted_finding = finding_template.format(**context)
            if formatted_finding.strip():
                finding_html = f"<div class='finding-box'>{md.render(formatted_finding)}</div>"
        except KeyError as e:
            finding_html = f"<div class='finding-box error'>数据缺失: {e}</div>"

    # 3. 生成 Tree HTML (<li>结构)
    # 因为我们已经剪枝了，所以能显示出来的节点肯定都是 Active 的 (除了根节点可能只是容器)
    # 但为了保险，根节点还是给个 CSS 类控制
    active_class = "active-node" if is_truly_active else ""
    li_html = f"<li class='{active_class}'><span>{rule_node['name']}</span>"

    # 4. 递归处理子节点
    all_child_findings = []
    child_lis = []

    if sub_rules := rule_node.get("sub_rules"):
        for sub_rule in sub_rules:
            sub_li_html, sub_finding_html = _format_rule_to_html_list(
                sub_rule, df_dict, context, md, parent_is_active=is_truly_active
            )
            # 只有当子节点有内容（未被剪枝）时才添加
            if sub_li_html:
                child_lis.append(sub_li_html)
            if sub_finding_html:
                all_child_findings.append(sub_finding_html)

    # 只有当存在可见的子节点时，才渲染 <ul>
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
) -> tuple[str, str]:
    """将整个规则配置转换为一个树状图HTML和一个结论HTML。"""
    if not rules_config:
        return "", ""

    tree_html_parts = []
    findings_html_parts = []

    for root_rule in rules_config:
        tree_html, findings_html = _format_rule_to_html_list(root_rule, df_dict, context, md)
        if tree_html:
            tree_html_parts.append(tree_html)
        findings_html_parts.append(findings_html)

    full_tree_html = f'<div class="tree"><ul>{"".join(tree_html_parts)}</ul></div>'
    full_findings_html = "".join(findings_html_parts)

    return full_tree_html, full_findings_html
