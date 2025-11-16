import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

from src.utils import get_project_root

log = logging.getLogger(__name__)


def generate_html_report(
    output_path: Path,
    md_instance: MarkdownIt,  # <-- 核心修改：接收一个 md 实例
    warnings: List[str],
    plots: Dict[str, str],
    tables_json: Dict[str, str],
    decision_tree_html: str,
    findings_for_tree_html: str,
    static_info_data: Dict,
    static_info_str: str,
    context: Dict[str, Any],
):
    """
    Renders the final HTML report using Jinja2 and writes it to disk.
    This function encapsulates all presentation-layer logic.
    """
    log.info(f"Generating HTML report at: {output_path}")

    templates_dir = get_project_root() / "src/templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    env.filters["markdown"] = lambda text: md_instance.render(text)
    template = env.get_template("report_template.html")

    html_content = template.render(
        warnings=warnings,
        plots=plots,
        tables_json=tables_json,
        decision_tree_html=decision_tree_html,
        findings_for_tree_html=findings_for_tree_html,
        static_info_str=static_info_str,
        static_info_data=static_info_data,
        context=context,
    )

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        log.info("✅ HTML report generation complete.")
    except IOError as e:
        log.error(f"Failed to write HTML report to {output_path}: {e}")
        raise
