import keyword
import logging
import re
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


def _format_rule_to_html_list(
    rule_node: Dict[str, Any],
    df_dict: Dict[str, pd.DataFrame],
    context: Dict[str, Any],
    md: MarkdownIt,
    parent_is_active: bool = True,
    depth: int = 0,  # [DEBUG] 增加深度用于日志缩进
) -> tuple[str, str]:
    """
    递归地将节点转换为HTML <li>，并单独返回其finding HTML。
    [DEBUG] 增加了详细的日志记录。
    """
    indent = "  " * depth
    rule_name = rule_node.get("name", "Unnamed")
    precondition = rule_node.get("precondition", "True")

    # === [DEBUG] 打印当前节点信息 ===
    log.debug(f"{indent}🔎 Evaluating Node: '{rule_name}'")
    log.debug(f"{indent}   Condition: {precondition}")

    is_self_condition_met = False
    try:
        # 在 eval 之前，打印出所有相关变量的值
        # 为了避免刷屏，只打印 precondition 中出现的变量

        variables_in_precondition = re.findall(r"\b([a-zA-Z_]\w*)\b", precondition)
        # 过滤掉 Python 关键字，只保留实际的上下文变量
        actual_variables = [v for v in variables_in_precondition if v not in keyword.kwlist]
        relevant_context = {k: context.get(k, "Not Found") for k in set(actual_variables)}
        log.debug(f"{indent}   Context Vars: {relevant_context}")

        result = eval(precondition, {"pd": pd}, {"df": df_dict, **context})
        if result:
            is_self_condition_met = True

        # === [DEBUG] 打印评估结果 ===
        log.debug(f"{indent}   ▶️ Result: {is_self_condition_met}")

    except Exception as e:
        log.debug(f"{indent}   ❌ Error evaluating condition: {e}")

    is_truly_active = parent_is_active and is_self_condition_met

    # === 核心修改：剪枝逻辑 (Pruning) ===
    # 规则：如果节点未激活，且不是根节点，则直接丢弃，不生成 HTML。
    # 这样前端树形图将只包含红色的、被触发的路径。
    is_root = rule_node.get("name") == "PIPA 根因分析"

    if not is_truly_active and not is_root:
        log.debug(f"{indent}   ✂️ Pruning branch (inactive).")
        return "", ""

    # 2. 生成 Finding HTML (结论文本框)
    finding_html = ""
    if is_truly_active and (finding_template := rule_node.get("finding")):
        try:
            formatted_finding = finding_template.format(**context)
            if formatted_finding.strip():
                log.info(f"{indent}✅ FINDING TRIGGERED: '{rule_name}'")  # 用 INFO 级别高亮显示命中的结论
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
        log.debug(f"{indent}   Descending into sub-rules...")
        for sub_rule in sub_rules:
            sub_li_html, sub_finding_html = _format_rule_to_html_list(
                sub_rule, df_dict, context, md, parent_is_active=is_truly_active, depth=depth + 1
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
) -> tuple[str, str, str]:
    """
    将规则转换为 HTML。
    返回三个部分: (audit_html, tree_html, findings_html)
    """
    if not rules_config:
        return "", "", ""

    audit_html_parts = []
    tree_html_parts = []
    findings_html_parts = []

    for rule_node in rules_config:
        # 复用之前的递归生成逻辑
        li_html, finding_html = _format_rule_to_html_list(rule_node, df_dict, context, md)

        # 收集所有的 findings (不管是审计还是诊断，结论都放在下面的大框里)
        if finding_html:
            findings_html_parts.append(finding_html)

        # 分离 UI 展示逻辑
        if rule_node.get("name") == "配置合规性检查":
            # 审计模块：如果激活了（生成了内容），就单独存起来
            # 我们去掉外层的 li 包装，直接取内部信息，或者重新包装成一个独立的 div
            if li_html:
                # 这里的 li_html 是 <li>...</li>。我们为了 UI 自由度，简单清洗一下
                # 或者直接原样返回，在模板里用 ul 包裹
                audit_html_parts.append(li_html)
        else:
            # 其他模块（根因分析）：放入决策树
            if li_html:
                tree_html_parts.append(li_html)

    # 组装
    audit_section_html = ""
    if audit_html_parts:
        # 给审计模块一个独立的 CSS 类，方便不想显示树状连线时隐藏
        audit_section_html = f'<div class="audit-panel"><ul>{"".join(audit_html_parts)}</ul></div>'

    tree_section_html = ""
    if tree_html_parts:
        tree_section_html = f'<div class="tree"><ul>{"".join(tree_html_parts)}</ul></div>'

    full_findings_html = "".join(findings_html_parts)

    return audit_section_html, tree_section_html, full_findings_html
