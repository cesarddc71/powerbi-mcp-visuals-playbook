"""FastMCP server exposing advanced PBIR visualization capabilities."""

from __future__ import annotations

import json
from typing import Any

from mcp_visuales_avanzado import service

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - depends on optional install
    raise SystemExit(
        "The MCP server requires the optional dependency 'mcp'.\n"
        "Install it with: pip install \"mcp[cli]\"\n"
        "or for local development: pip install -e ."
    ) from exc


mcp = FastMCP(
    "Vicente Antonio Juan Magallanes Power BI Visuals MCP",
    instructions=(
        "Manage Power BI PBIR reports, pages, visuals, filters, formatting, "
        "bookmarks, themes, and embedded custom visuals using local PBIR backends."
    ),
)


def _as_json(data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Serialize resource data as JSON text."""
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.resource("pbivis://context", mime_type="application/json")
def current_context_resource() -> str:
    """Read the current PBIR project context."""
    return _as_json(service.get_project_context())


@mcp.resource("pbivis://supported-visuals", mime_type="application/json")
def supported_visuals_resource() -> str:
    """Read the supported visual type catalog."""
    return _as_json(service.list_supported_visuals())


@mcp.resource("pbivis://templates/{visual_type}.json", mime_type="application/json")
def visual_template_resource(visual_type: str) -> str:
    """Read the raw JSON template for a visual type."""
    return _as_json(service.get_visual_template(visual_type))


@mcp.resource("pbivis://report/summary", mime_type="application/json")
def report_summary_resource() -> str:
    """Read the current report summary."""
    return _as_json(service.describe_report())


@mcp.resource("pbivis://pages/{page_name}", mime_type="application/json")
def page_resource(page_name: str) -> str:
    """Read one page and its visuals."""
    return _as_json(service.describe_page(page_name))


@mcp.resource("pbivis://pages/{page_name}/visuals", mime_type="application/json")
def page_visuals_resource(page_name: str) -> str:
    """Read all visuals on a page."""
    return _as_json(service.list_visuals(page_name))


@mcp.resource("pbivis://visuals/{page_name}/{visual_name}", mime_type="application/json")
def visual_resource(page_name: str, visual_name: str) -> str:
    """Read one visual definition summary."""
    return _as_json(service.describe_visual(page_name, visual_name))


@mcp.resource("pbivis://preview/report.html", mime_type="text/html")
def report_preview_resource() -> str:
    """Read the rendered HTML preview for the active report."""
    return str(service.render_report_preview_html()["html"])


@mcp.resource("pbivis://preview/pages/{page_name}.html", mime_type="text/html")
def page_preview_resource(page_name: str) -> str:
    """Read the rendered HTML preview for one page."""
    return str(service.render_page_preview_html(page_name)["html"])


_TOOL_FUNCTIONS = [
    service.get_project_context,
    service.set_project_context,
    service.list_supported_visuals,
    service.describe_visual_type,
    service.get_visual_template,
    service.create_report_project,
    service.convert_report_project,
    service.describe_report,
    service.validate_report_structure,
    service.render_report_preview_html,
    service.render_page_preview_html,
    service.sync_desktop_project,
    service.list_pages,
    service.describe_page,
    service.create_page,
    service.delete_page,
    service.set_page_background,
    service.set_page_visibility,
    service.set_report_theme,
    service.apply_report_palette,
    service.get_report_theme,
    service.diff_report_theme,
    service.list_visuals,
    service.describe_visual,
    service.get_visual_container_style,
    service.create_visual,
    service.update_visual_layout,
    service.delete_visual,
    service.bind_visual,
    service.query_visuals,
    service.bulk_bind_visuals,
    service.bulk_update_visuals,
    service.bulk_delete_visuals,
    service.set_visual_container,
    service.set_visual_chart_style,
    service.set_visual_series_style,
    service.add_visual_calculation,
    service.list_visual_calculations,
    service.delete_visual_calculation,
    service.list_filters,
    service.add_categorical_filter,
    service.add_topn_filter,
    service.add_relative_date_filter,
    service.remove_filter,
    service.clear_filters,
    service.get_visual_formatting,
    service.clear_visual_formatting,
    service.apply_gradient_background,
    service.apply_conditional_background,
    service.apply_measure_background,
    service.list_bookmarks,
    service.get_bookmark,
    service.create_bookmark,
    service.delete_bookmark,
    service.set_bookmark_visual_visibility,
    service.import_custom_visual,
    service.list_custom_visuals,
    service.remove_custom_visual,
    service.bump_custom_visual_patch_version,
]

for tool_fn in _TOOL_FUNCTIONS:
    mcp.tool()(tool_fn)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
