"""HTML report rendering utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, PackageLoader
from markdown_it import MarkdownIt

log = logging.getLogger(__name__)


def generate_html_report(
    output_path: Path,
    md_instance: MarkdownIt,
    warnings: List[str],
    plots: Dict[str, str],
    tables_json: Dict[str, str],
    decision_tree_html: str,
    findings_for_tree_html: str,
    static_info_data: Dict[str, Any],
    static_info_str: str,
    context: Dict[str, Any],
    audit_html: str = "",
):
    """Render the full HTML report using Jinja templates."""

    log.info("Generating HTML report at: %s", output_path)
    env = Environment(loader=PackageLoader("pipa", "templates"))
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
        audit_html=audit_html,
    )

    try:
        with open(output_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(html_content)
        log.info("HTML report generation complete.")
    except IOError as exc:
        log.error("Failed to write HTML report to %s: %s", output_path, exc)
        raise
