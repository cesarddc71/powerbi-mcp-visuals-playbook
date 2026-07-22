"""Service layer for a Power BI Visuals MCP server.

Wraps the existing PBIR report/visual backends with a stable, structured API
that can be exposed over MCP without pulling in Click-specific command code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_visuales_avanzado.core.bookmark_backend import (
    bookmark_add,
    bookmark_delete,
    bookmark_get,
    bookmark_list,
    bookmark_set_visibility,
)
from mcp_visuales_avanzado.core.bulk_backend import (
    visual_bulk_bind,
    visual_bulk_delete,
    visual_bulk_update,
    visual_where,
)
from mcp_visuales_avanzado.core.custom_visual_backend import (
    custom_visual_import,
    custom_visual_list,
    custom_visual_remove,
    pbiviz_bump_patch,
)
from mcp_visuales_avanzado.core.errors import ReportNotFoundError
from mcp_visuales_avanzado.core.filter_backend import (
    filter_add_categorical,
    filter_add_relative_date,
    filter_add_topn,
    filter_clear,
    filter_list,
    filter_remove,
)
from mcp_visuales_avanzado.core.format_backend import (
    format_background_conditional,
    format_background_gradient,
    format_background_measure,
    format_clear,
    format_get,
)
from mcp_visuales_avanzado.core.pbir_models import SUPPORTED_VISUAL_TYPES, VISUAL_TYPE_ALIASES
from mcp_visuales_avanzado.core.pbir_path import resolve_report_path
from mcp_visuales_avanzado.core.pbir_validators import validate_report_full as validate_report_full_backend
from mcp_visuales_avanzado.core.report_backend import (
    page_add,
    page_delete,
    page_get,
    page_list,
    page_set_background,
    page_set_visibility,
    report_convert,
    report_create,
    report_info,
    report_validate,
    theme_apply_palette,
    theme_diff,
    theme_get,
    theme_set,
)
from mcp_visuales_avanzado.core.style_backend import (
    visual_get_container_style as visual_get_container_style_backend,
    visual_set_chart_style as visual_set_chart_style_backend,
    visual_set_container as visual_set_container_backend,
    visual_set_series_style as visual_set_series_style_backend,
)
from mcp_visuales_avanzado.core.visual_backend import (
    DEFAULT_SIZES,
    ROLE_ALIASES,
    VISUAL_DATA_ROLES,
    _load_template,
    _resolve_visual_type,
    visual_add,
    visual_bind,
    visual_calc_add,
    visual_calc_delete,
    visual_calc_list,
    visual_delete,
    visual_get,
    visual_list,
    visual_update,
)
from mcp_visuales_avanzado.preview.renderer import render_page, render_report
from mcp_visuales_avanzado.utils.desktop_sync import sync_desktop


@dataclass
class ProjectContextState:
    """Persisted report context for the current MCP server process."""

    raw_path: str | None = None
    definition_path: str | None = None


_CONTEXT = ProjectContextState()


def _report_folder_from_definition(definition_path: Path) -> Path:
    """Return the `.Report` folder for a resolved PBIR definition path."""
    return definition_path.parent


def _find_pbip_path(report_folder: Path) -> str | None:
    """Best-effort lookup for the sibling `.pbip` file."""
    project_root = report_folder.parent
    preferred = project_root / f"{report_folder.name.removesuffix('.Report')}.pbip"
    if preferred.exists():
        return str(preferred)

    for candidate in sorted(project_root.glob("*.pbip")):
        return str(candidate)
    return None


def _build_context_payload(
    definition_path: Path,
    raw_path: str | None,
    source: str,
) -> dict[str, Any]:
    """Return a normalized context payload."""
    report_folder = _report_folder_from_definition(definition_path)
    return {
        "configured": True,
        "source": source,
        "input_path": raw_path,
        "definition_path": str(definition_path),
        "report_folder": str(report_folder),
        "project_root": str(report_folder.parent),
        "pbip_path": _find_pbip_path(report_folder),
    }


def _resolve_definition_path(report_path: str | None = None) -> Path:
    """Resolve the active PBIR definition path from an explicit or stored path."""
    if report_path is not None:
        return resolve_report_path(report_path)

    if _CONTEXT.definition_path is not None:
        definition_path = Path(_CONTEXT.definition_path)
        if definition_path.is_dir():
            return definition_path

    return resolve_report_path(None)


def _resolve_report_folder(report_path: str | None = None) -> Path:
    """Resolve the active `.Report` folder."""
    return _report_folder_from_definition(_resolve_definition_path(report_path))


def _sync_hint_path(report_path: str | None = None) -> str | None:
    """Return the most useful path hint for Desktop sync."""
    if report_path is not None:
        return report_path
    if _CONTEXT.raw_path is not None:
        return _CONTEXT.raw_path
    return str(_resolve_report_folder(None))


def get_project_context() -> dict[str, Any]:
    """Get the current PBIR project context."""
    if _CONTEXT.definition_path is not None:
        return _build_context_payload(
            Path(_CONTEXT.definition_path),
            _CONTEXT.raw_path,
            source="stored",
        )

    try:
        definition_path = resolve_report_path(None)
    except ReportNotFoundError:
        return {
            "configured": False,
            "source": "none",
            "input_path": None,
            "definition_path": None,
            "report_folder": None,
            "project_root": None,
            "pbip_path": None,
        }

    return _build_context_payload(definition_path, None, source="auto-detected")


def set_project_context(path: str | None = None, reset: bool = False) -> dict[str, Any]:
    """Set or clear the active PBIR project context."""
    global _CONTEXT

    if reset:
        _CONTEXT = ProjectContextState()
        if path is None:
            return {
                "status": "cleared",
                "configured": False,
            }

    definition_path = resolve_report_path(path)
    _CONTEXT = ProjectContextState(raw_path=path, definition_path=str(definition_path))
    payload = _build_context_payload(definition_path, path, source="stored")
    payload["status"] = "set"
    return payload


def list_supported_visuals() -> dict[str, Any]:
    """List all supported visual types, aliases, roles, and default sizes."""
    aliases_by_type: dict[str, list[str]] = {name: [] for name in SUPPORTED_VISUAL_TYPES}
    for alias, canonical in VISUAL_TYPE_ALIASES.items():
        aliases_by_type.setdefault(canonical, []).append(alias)

    visuals: list[dict[str, Any]] = []
    for visual_type in sorted(SUPPORTED_VISUAL_TYPES):
        width, height = DEFAULT_SIZES.get(visual_type, (400, 300))
        visuals.append(
            {
                "visual_type": visual_type,
                "aliases": sorted(aliases_by_type.get(visual_type, [])),
                "default_size": {"width": width, "height": height},
                "data_roles": VISUAL_DATA_ROLES.get(visual_type, []),
                "role_aliases": ROLE_ALIASES.get(visual_type, {}),
            }
        )

    return {"total": len(visuals), "visuals": visuals}


def describe_visual_type(visual_type: str) -> dict[str, Any]:
    """Describe one visual type, including aliases, roles, size, and template."""
    canonical = _resolve_visual_type(visual_type)
    width, height = DEFAULT_SIZES.get(canonical, (400, 300))
    aliases = sorted([alias for alias, target in VISUAL_TYPE_ALIASES.items() if target == canonical])
    return {
        "visual_type": canonical,
        "aliases": aliases,
        "default_size": {"width": width, "height": height},
        "data_roles": VISUAL_DATA_ROLES.get(canonical, []),
        "role_aliases": ROLE_ALIASES.get(canonical, {}),
        "template": _load_template(canonical),
    }


def get_visual_template(visual_type: str) -> dict[str, Any]:
    """Return the raw JSON template for a visual type."""
    canonical = _resolve_visual_type(visual_type)
    return {"visual_type": canonical, "template": _load_template(canonical)}


def create_report_project(
    target_path: str,
    name: str,
    dataset_path: str | None = None,
) -> dict[str, Any]:
    """Create a PBIR report project and set it as the active context."""
    result = report_create(Path(target_path), name=name, dataset_path=dataset_path)
    definition_path = Path(str(result["definition_path"]))
    global _CONTEXT
    _CONTEXT = ProjectContextState(raw_path=str(definition_path.parent), definition_path=str(definition_path))
    result["context"] = _build_context_payload(definition_path, str(definition_path.parent), "stored")
    return result


def convert_report_project(
    source_path: str,
    output_path: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Convert a `.Report` folder into a `.pbip` project."""
    return report_convert(
        source_path=Path(source_path),
        output_path=Path(output_path) if output_path else None,
        force=force,
    )


def describe_report(report_path: str | None = None) -> dict[str, Any]:
    """Return report metadata and the resolved context."""
    definition_path = _resolve_definition_path(report_path)
    result = report_info(definition_path)
    result["context"] = _build_context_payload(definition_path, report_path, "explicit" if report_path else "active")
    return result


def validate_report_structure(report_path: str | None = None, full: bool = False) -> dict[str, Any]:
    """Validate the active PBIR report."""
    definition_path = _resolve_definition_path(report_path)
    if full:
        return validate_report_full_backend(definition_path)
    return report_validate(definition_path)


def render_report_preview_html(report_path: str | None = None) -> dict[str, Any]:
    """Render the active report preview as HTML."""
    definition_path = _resolve_definition_path(report_path)
    return {"definition_path": str(definition_path), "html": render_report(definition_path)}


def render_page_preview_html(page_name: str, report_path: str | None = None) -> dict[str, Any]:
    """Render one page preview as HTML."""
    definition_path = _resolve_definition_path(report_path)
    return {
        "definition_path": str(definition_path),
        "page_name": page_name,
        "html": render_page(definition_path, page_name),
    }


def sync_desktop_project(report_path: str | None = None) -> dict[str, Any]:
    """Close, save, restore PBIR edits, and reopen the `.pbip` in Desktop."""
    definition_path = _resolve_definition_path(report_path)
    return sync_desktop(
        pbip_hint=_sync_hint_path(report_path),
        definition_path=str(definition_path),
    )


def list_pages(report_path: str | None = None) -> list[dict[str, Any]]:
    """List pages in the active report."""
    return page_list(_resolve_definition_path(report_path))


def describe_page(page_name: str, report_path: str | None = None) -> dict[str, Any]:
    """Return page details together with its visuals."""
    definition_path = _resolve_definition_path(report_path)
    page = page_get(definition_path, page_name)
    page["visuals"] = visual_list(definition_path, page_name)
    return page


def create_page(
    display_name: str,
    name: str | None = None,
    width: int = 1280,
    height: int = 720,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Create a page in the active report."""
    return page_add(
        _resolve_definition_path(report_path),
        display_name=display_name,
        name=name,
        width=width,
        height=height,
    )


def delete_page(page_name: str, report_path: str | None = None) -> dict[str, Any]:
    """Delete a page from the active report."""
    return page_delete(_resolve_definition_path(report_path), page_name)


def set_page_background(
    page_name: str,
    color: str,
    transparency: int = 0,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Set the page background color."""
    return page_set_background(
        _resolve_definition_path(report_path),
        page_name=page_name,
        color=color,
        transparency=transparency,
    )


def set_page_visibility(
    page_name: str,
    hidden: bool,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Hide or show a page in navigation."""
    return page_set_visibility(_resolve_definition_path(report_path), page_name=page_name, hidden=hidden)


def set_report_theme(theme_path: str, report_path: str | None = None) -> dict[str, Any]:
    """Apply a report theme JSON."""
    return theme_set(_resolve_definition_path(report_path), Path(theme_path))


def apply_report_palette(
    name: str,
    data_colors: list[str],
    background: str = "#FFFFFF",
    foreground: str = "#252423",
    background_light: str | None = None,
    background_neutral: str | None = None,
    neutral_secondary: str | None = None,
    neutral_tertiary: str | None = None,
    table_accent: str | None = None,
    good: str | None = None,
    neutral: str | None = None,
    bad: str | None = None,
    minimum: str | None = None,
    center: str | None = None,
    maximum: str | None = None,
    visual_background: str | None = None,
    border_color: str | None = None,
    font_family: str = "Segoe UI",
    title_font_family: str | None = None,
    title_font_size: int = 14,
    label_font_size: int = 10,
    line_stroke_width: int = 3,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Generate and apply a report theme palette directly from MCP inputs."""
    return theme_apply_palette(
        _resolve_definition_path(report_path),
        name=name,
        data_colors=data_colors,
        background=background,
        foreground=foreground,
        background_light=background_light,
        background_neutral=background_neutral,
        neutral_secondary=neutral_secondary,
        neutral_tertiary=neutral_tertiary,
        table_accent=table_accent,
        good=good,
        neutral=neutral,
        bad=bad,
        minimum=minimum,
        center=center,
        maximum=maximum,
        visual_background=visual_background,
        border_color=border_color,
        font_family=font_family,
        title_font_family=title_font_family,
        title_font_size=title_font_size,
        label_font_size=label_font_size,
        line_stroke_width=line_stroke_width,
    )


def get_report_theme(report_path: str | None = None) -> dict[str, Any]:
    """Get the currently applied report theme."""
    return theme_get(_resolve_definition_path(report_path))


def diff_report_theme(theme_path: str, report_path: str | None = None) -> dict[str, Any]:
    """Diff a proposed theme JSON against the current theme."""
    return theme_diff(_resolve_definition_path(report_path), Path(theme_path))


def list_visuals(page_name: str, report_path: str | None = None) -> list[dict[str, Any]]:
    """List visuals on a page."""
    return visual_list(_resolve_definition_path(report_path), page_name)


def describe_visual(
    page_name: str,
    visual_name: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Get one visual's details, including bindings."""
    return visual_get(_resolve_definition_path(report_path), page_name, visual_name)


def get_visual_container_style(
    page_name: str,
    visual_name: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Get raw visual container styling for a visual."""
    return visual_get_container_style_backend(
        _resolve_definition_path(report_path),
        page_name,
        visual_name,
    )


def create_visual(
    page_name: str,
    visual_type: str,
    name: str | None = None,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Create a visual on a page from a PBIR template."""
    return visual_add(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_type=visual_type,
        name=name,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def update_visual_layout(
    page_name: str,
    visual_name: str,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    hidden: bool | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Update a visual's position, size, or visibility."""
    return visual_update(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        x=x,
        y=y,
        width=width,
        height=height,
        hidden=hidden,
    )


def delete_visual(
    page_name: str,
    visual_name: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Delete a visual from a page."""
    return visual_delete(_resolve_definition_path(report_path), page_name, visual_name)


def bind_visual(
    page_name: str,
    visual_name: str,
    bindings: list[dict[str, Any]],
    report_path: str | None = None,
) -> dict[str, Any]:
    """Bind fields to a visual, resolving Column/Measure from TMDL when present.

    Each binding supports role, field, and optional field_type/kind
    ("Column" or "Measure") for cases where the semantic model is not local.
    """
    return visual_bind(_resolve_definition_path(report_path), page_name, visual_name, bindings)


def query_visuals(
    page_name: str,
    visual_type: str | None = None,
    name_pattern: str | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
    report_path: str | None = None,
) -> list[dict[str, Any]]:
    """Filter visuals on a page by type, name pattern, or position."""
    return visual_where(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_type=visual_type,
        name_pattern=name_pattern,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
    )


def bulk_bind_visuals(
    page_name: str,
    visual_type: str,
    bindings: list[dict[str, str]],
    name_pattern: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Bind fields to all matching visuals on a page."""
    return visual_bulk_bind(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_type=visual_type,
        bindings=bindings,
        name_pattern=name_pattern,
    )


def bulk_update_visuals(
    page_name: str,
    where_type: str | None = None,
    where_name_pattern: str | None = None,
    set_hidden: bool | None = None,
    set_width: float | None = None,
    set_height: float | None = None,
    set_x: float | None = None,
    set_y: float | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Update all visuals matching the provided filters."""
    return visual_bulk_update(
        _resolve_definition_path(report_path),
        page_name=page_name,
        where_type=where_type,
        where_name_pattern=where_name_pattern,
        set_hidden=set_hidden,
        set_width=set_width,
        set_height=set_height,
        set_x=set_x,
        set_y=set_y,
    )


def bulk_delete_visuals(
    page_name: str,
    where_type: str | None = None,
    where_name_pattern: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Delete all visuals matching the provided filters."""
    return visual_bulk_delete(
        _resolve_definition_path(report_path),
        page_name=page_name,
        where_type=where_type,
        where_name_pattern=where_name_pattern,
    )


def set_visual_container(
    page_name: str,
    visual_name: str,
    border_show: bool | None = None,
    border_color: str | None = None,
    border_radius: int | None = None,
    background_show: bool | None = None,
    background_color: str | None = None,
    background_transparency: int | None = None,
    title: str | None = None,
    title_color: str | None = None,
    title_font_size: int | None = None,
    title_font_family: str | None = None,
    title_alignment: str | None = None,
    title_heading: str | None = None,
    title_wrap: bool | None = None,
    subtitle: str | None = None,
    subtitle_show: bool | None = None,
    subtitle_font_size: int | None = None,
    subtitle_alignment: str | None = None,
    subtitle_wrap: bool | None = None,
    subtitle_bold: bool | None = None,
    subtitle_italic: bool | None = None,
    divider_show: bool | None = None,
    divider_color: str | None = None,
    spacing_vertical: int | None = None,
    space_below_title: int | None = None,
    space_below_subtitle: int | None = None,
    space_below_title_area: int | None = None,
    padding_top: int | None = None,
    padding_right: int | None = None,
    padding_bottom: int | None = None,
    padding_left: int | None = None,
    drop_shadow: bool | None = None,
    visual_header_show: bool | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Update rich visual container styling like radius, padding, subtitle, and shadow."""
    return visual_set_container_backend(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        border_show=border_show,
        border_color=border_color,
        border_radius=border_radius,
        background_show=background_show,
        background_color=background_color,
        background_transparency=background_transparency,
        title=title,
        title_color=title_color,
        title_font_size=title_font_size,
        title_font_family=title_font_family,
        title_alignment=title_alignment,
        title_heading=title_heading,
        title_wrap=title_wrap,
        subtitle=subtitle,
        subtitle_show=subtitle_show,
        subtitle_font_size=subtitle_font_size,
        subtitle_alignment=subtitle_alignment,
        subtitle_wrap=subtitle_wrap,
        subtitle_bold=subtitle_bold,
        subtitle_italic=subtitle_italic,
        divider_show=divider_show,
        divider_color=divider_color,
        spacing_vertical=spacing_vertical,
        space_below_title=space_below_title,
        space_below_subtitle=space_below_subtitle,
        space_below_title_area=space_below_title_area,
        padding_top=padding_top,
        padding_right=padding_right,
        padding_bottom=padding_bottom,
        padding_left=padding_left,
        drop_shadow=drop_shadow,
        visual_header_show=visual_header_show,
    )


def set_visual_chart_style(
    page_name: str,
    visual_name: str,
    legend_show: bool | None = None,
    legend_position: str | None = None,
    category_axis_show: bool | None = None,
    category_axis_title_show: bool | None = None,
    category_axis_label_color: str | None = None,
    category_axis_font_size: int | None = None,
    category_axis_bold: bool | None = None,
    category_axis_preferred_width: int | None = None,
    value_axis_show: bool | None = None,
    value_axis_title_show: bool | None = None,
    value_axis_gridlines_show: bool | None = None,
    value_axis_label_color: str | None = None,
    value_axis_font_size: int | None = None,
    y2_axis_show: bool | None = None,
    labels_show: bool | None = None,
    labels_font_size: int | None = None,
    labels_bold: bool | None = None,
    labels_position: str | None = None,
    labels_color: str | None = None,
    line_chart_type: str | None = None,
    line_stroke_width: int | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Set common chart styling like legend, axes, labels, and line thickness."""
    return visual_set_chart_style_backend(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        legend_show=legend_show,
        legend_position=legend_position,
        category_axis_show=category_axis_show,
        category_axis_title_show=category_axis_title_show,
        category_axis_label_color=category_axis_label_color,
        category_axis_font_size=category_axis_font_size,
        category_axis_bold=category_axis_bold,
        category_axis_preferred_width=category_axis_preferred_width,
        value_axis_show=value_axis_show,
        value_axis_title_show=value_axis_title_show,
        value_axis_gridlines_show=value_axis_gridlines_show,
        value_axis_label_color=value_axis_label_color,
        value_axis_font_size=value_axis_font_size,
        y2_axis_show=y2_axis_show,
        labels_show=labels_show,
        labels_font_size=labels_font_size,
        labels_bold=labels_bold,
        labels_position=labels_position,
        labels_color=labels_color,
        line_chart_type=line_chart_type,
        line_stroke_width=line_stroke_width,
    )


def set_visual_series_style(
    page_name: str,
    visual_name: str,
    query_ref: str,
    color: str | None = None,
    line_stroke_width: int | None = None,
    line_chart_type: str | None = None,
    label_color: str | None = None,
    label_font_size: int | None = None,
    label_bold: bool | None = None,
    label_position: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Set per-series color, line thickness, and label styling by metadata query ref."""
    return visual_set_series_style_backend(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        query_ref=query_ref,
        color=color,
        line_stroke_width=line_stroke_width,
        line_chart_type=line_chart_type,
        label_color=label_color,
        label_font_size=label_font_size,
        label_bold=label_bold,
        label_position=label_position,
    )


def add_visual_calculation(
    page_name: str,
    visual_name: str,
    calc_name: str,
    expression: str,
    role: str = "Y",
    report_path: str | None = None,
) -> dict[str, Any]:
    """Add or replace a visual calculation in a visual role."""
    return visual_calc_add(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        calc_name=calc_name,
        expression=expression,
        role=role,
    )


def list_visual_calculations(
    page_name: str,
    visual_name: str,
    report_path: str | None = None,
) -> list[dict[str, Any]]:
    """List visual calculations on a visual."""
    return visual_calc_list(_resolve_definition_path(report_path), page_name, visual_name)


def delete_visual_calculation(
    page_name: str,
    visual_name: str,
    calc_name: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Delete a visual calculation by name."""
    return visual_calc_delete(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        calc_name=calc_name,
    )


def list_filters(
    page_name: str,
    visual_name: str | None = None,
    report_path: str | None = None,
) -> list[dict[str, Any]]:
    """List page-level or visual-level filters."""
    return filter_list(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
    )


def add_categorical_filter(
    page_name: str,
    table: str,
    column: str,
    values: list[str],
    visual_name: str | None = None,
    name: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Add a categorical filter to a page or visual."""
    return filter_add_categorical(
        _resolve_definition_path(report_path),
        page_name=page_name,
        table=table,
        column=column,
        values=values,
        visual_name=visual_name,
        name=name,
    )


def add_topn_filter(
    page_name: str,
    table: str,
    column: str,
    n: int,
    order_by_table: str,
    order_by_column: str,
    direction: str = "Top",
    visual_name: str | None = None,
    name: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Add a TopN filter to a page or visual."""
    return filter_add_topn(
        _resolve_definition_path(report_path),
        page_name=page_name,
        table=table,
        column=column,
        n=n,
        order_by_table=order_by_table,
        order_by_column=order_by_column,
        direction=direction,
        visual_name=visual_name,
        name=name,
    )


def add_relative_date_filter(
    page_name: str,
    table: str,
    column: str,
    amount: int,
    time_unit: str,
    visual_name: str | None = None,
    name: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Add a relative-date filter to a page or visual."""
    return filter_add_relative_date(
        _resolve_definition_path(report_path),
        page_name=page_name,
        table=table,
        column=column,
        amount=amount,
        time_unit=time_unit,
        visual_name=visual_name,
        name=name,
    )


def remove_filter(
    page_name: str,
    filter_name: str,
    visual_name: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Remove a filter from a page or visual."""
    return filter_remove(
        _resolve_definition_path(report_path),
        page_name=page_name,
        filter_name=filter_name,
        visual_name=visual_name,
    )


def clear_filters(
    page_name: str,
    visual_name: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Clear all filters from a page or visual."""
    return filter_clear(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
    )


def get_visual_formatting(
    page_name: str,
    visual_name: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Get current formatting objects for a visual."""
    return format_get(_resolve_definition_path(report_path), page_name, visual_name)


def clear_visual_formatting(
    page_name: str,
    visual_name: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Clear all formatting objects from a visual."""
    return format_clear(_resolve_definition_path(report_path), page_name, visual_name)


def apply_gradient_background(
    page_name: str,
    visual_name: str,
    input_table: str,
    input_column: str,
    field_query_ref: str,
    min_color: str = "#FFFFFF",
    max_color: str = "#118DFF",
    report_path: str | None = None,
) -> dict[str, Any]:
    """Apply gradient conditional formatting to a visual field background."""
    return format_background_gradient(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        input_table=input_table,
        input_column=input_column,
        field_query_ref=field_query_ref,
        min_color=min_color,
        max_color=max_color,
    )


def apply_conditional_background(
    page_name: str,
    visual_name: str,
    input_table: str,
    input_column: str,
    threshold: float,
    color_hex: str,
    comparison: str = "gt",
    field_query_ref: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Apply rule-based conditional formatting to a visual field background."""
    return format_background_conditional(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        input_table=input_table,
        input_column=input_column,
        threshold=threshold,
        color_hex=color_hex,
        comparison=comparison,
        field_query_ref=field_query_ref,
    )


def apply_measure_background(
    page_name: str,
    visual_name: str,
    measure_table: str,
    measure_property: str,
    field_query_ref: str,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Apply measure-driven conditional formatting to a visual field background."""
    return format_background_measure(
        _resolve_definition_path(report_path),
        page_name=page_name,
        visual_name=visual_name,
        measure_table=measure_table,
        measure_property=measure_property,
        field_query_ref=field_query_ref,
    )


def list_bookmarks(report_path: str | None = None) -> list[dict[str, Any]]:
    """List bookmarks in the active report."""
    return bookmark_list(_resolve_definition_path(report_path))


def get_bookmark(name: str, report_path: str | None = None) -> dict[str, Any]:
    """Get one bookmark by name."""
    return bookmark_get(_resolve_definition_path(report_path), name)


def create_bookmark(
    display_name: str,
    target_page: str,
    name: str | None = None,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Create a bookmark pointing to a page."""
    return bookmark_add(
        _resolve_definition_path(report_path),
        display_name=display_name,
        target_page=target_page,
        name=name,
    )


def delete_bookmark(name: str, report_path: str | None = None) -> dict[str, Any]:
    """Delete a bookmark from the active report."""
    return bookmark_delete(_resolve_definition_path(report_path), name)


def set_bookmark_visual_visibility(
    bookmark_name: str,
    page_name: str,
    visual_name: str,
    hidden: bool,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Set the visibility of a visual inside a bookmark."""
    return bookmark_set_visibility(
        _resolve_definition_path(report_path),
        name=bookmark_name,
        page_name=page_name,
        visual_name=visual_name,
        hidden=hidden,
    )


def import_custom_visual(
    pbiviz_path: str,
    replace: bool = False,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Import a local `.pbiviz` into the active report."""
    return custom_visual_import(
        _resolve_definition_path(report_path),
        pbiviz_path=Path(pbiviz_path),
        replace=replace,
    )


def list_custom_visuals(report_path: str | None = None) -> dict[str, Any]:
    """List embedded and public custom visuals."""
    return custom_visual_list(_resolve_definition_path(report_path))


def remove_custom_visual(identifier: str, report_path: str | None = None) -> dict[str, Any]:
    """Remove an embedded custom visual by GUID or name."""
    return custom_visual_remove(_resolve_definition_path(report_path), identifier)


def bump_custom_visual_patch_version(pbiviz_json_path: str) -> dict[str, Any]:
    """Increment the patch version in a `pbiviz.json` file."""
    return pbiviz_bump_patch(Path(pbiviz_json_path))
