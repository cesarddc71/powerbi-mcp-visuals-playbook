"""Pure-function backend for PBIR visual styling operations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mcp_visuales_avanzado.core.errors import PbiCliError
from mcp_visuales_avanzado.core.pbir_path import get_visual_dir

_HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def _read_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_visual_json(
    definition_path: Path,
    page_name: str,
    visual_name: str,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    visual_json_path = get_visual_dir(definition_path, page_name, visual_name) / "visual.json"
    if not visual_json_path.exists():
        raise PbiCliError(f"Visual '{visual_name}' not found on page '{page_name}'.")

    data = _read_json(visual_json_path)
    visual = data.get("visual")
    if visual is None:
        raise PbiCliError(f"Visual '{visual_name}' has invalid JSON -- missing 'visual' key.")

    return visual_json_path, data, visual


def _validate_color(color: str) -> None:
    if not _HEX_COLOR_PATTERN.fullmatch(color):
        raise PbiCliError(
            f"Invalid color '{color}' -- expected hex format like '#118DFF' or '#DEEFFF'."
        )


def _validate_percent(value: int, label: str) -> None:
    if not 0 <= value <= 100:
        raise PbiCliError(f"Invalid {label} '{value}' -- must be between 0 and 100.")


def _validate_non_negative(value: int | float, label: str) -> None:
    if value < 0:
        raise PbiCliError(f"Invalid {label} '{value}' -- must be >= 0.")


def _escape_text(value: str) -> str:
    return value.replace("'", "''")


def _literal_expr(value: str) -> dict[str, Any]:
    return {"expr": {"Literal": {"Value": value}}}


def _bool_expr(value: bool) -> dict[str, Any]:
    return _literal_expr("true" if value else "false")


def _number_expr(value: int | float, suffix: str = "D") -> dict[str, Any]:
    normalized = int(value) if float(value).is_integer() else value
    return _literal_expr(f"{normalized}{suffix}")


def _text_expr(value: str) -> dict[str, Any]:
    return _literal_expr(f"'{_escape_text(value)}'")


def _normalize_container_alignment(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"left", "center", "right"}:
        raise PbiCliError(
            f"Invalid alignment '{value}' -- expected one of: left, center, right."
        )
    return normalized


def _solid_color_expr(color: str) -> dict[str, Any]:
    _validate_color(color)
    return {
        "solid": {
            "color": {
                "expr": {
                    "Literal": {
                        "Value": f"'{color}'",
                    }
                }
            }
        }
    }


def _selector_matches(entry: dict[str, Any], selector: dict[str, Any] | None) -> bool:
    if selector is None:
        return "selector" not in entry
    return entry.get("selector") == selector


def _upsert_properties_entry(
    section_map: dict[str, Any],
    section_name: str,
    prop_updates: dict[str, Any],
    selector: dict[str, Any] | None = None,
) -> None:
    if not prop_updates:
        return

    entries = list(section_map.get(section_name, []))
    match_index = next(
        (i for i, entry in enumerate(entries) if _selector_matches(entry, selector)),
        None,
    )

    if match_index is None:
        entry: dict[str, Any] = {"properties": {}}
        if selector is not None:
            entry["selector"] = selector
        entries.append(entry)
        match_index = len(entries) - 1

    updated_entry = dict(entries[match_index])
    properties = dict(updated_entry.get("properties", {}))
    properties.update(prop_updates)
    updated_entry["properties"] = properties
    entries[match_index] = updated_entry
    section_map[section_name] = entries


def _metadata_selector(query_ref: str) -> dict[str, Any]:
    return {"metadata": query_ref}


def _metadata_label_selector(query_ref: str) -> dict[str, Any]:
    return {
        "data": [{"dataViewWildcard": {"matchingOption": 1}}],
        "metadata": query_ref,
    }


def visual_get_container_style(
    definition_path: Path,
    page_name: str,
    visual_name: str,
) -> dict[str, Any]:
    """Return raw visual container objects for a visual."""
    _, _, visual = _load_visual_json(definition_path, page_name, visual_name)
    return {
        "visual": visual_name,
        "page": page_name,
        "visual_container_objects": visual.get("visualContainerObjects", {}),
    }


def visual_set_container(
    definition_path: Path,
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
) -> dict[str, Any]:
    """Set rich visual container properties on a visual."""
    visual_json_path, data, visual = _load_visual_json(definition_path, page_name, visual_name)

    for color in (border_color, background_color, title_color, divider_color):
        if color is not None:
            _validate_color(color)

    if background_transparency is not None:
        _validate_percent(background_transparency, "background_transparency")

    for label, number in (
        ("border_radius", border_radius),
        ("title_font_size", title_font_size),
        ("subtitle_font_size", subtitle_font_size),
        ("spacing_vertical", spacing_vertical),
        ("space_below_title", space_below_title),
        ("space_below_subtitle", space_below_subtitle),
        ("space_below_title_area", space_below_title_area),
        ("padding_top", padding_top),
        ("padding_right", padding_right),
        ("padding_bottom", padding_bottom),
        ("padding_left", padding_left),
    ):
        if number is not None:
            _validate_non_negative(number, label)

    if all(
        value is None
        for value in (
            border_show,
            border_color,
            border_radius,
            background_show,
            background_color,
            background_transparency,
            title,
            title_color,
            title_font_size,
            title_font_family,
            title_alignment,
            title_heading,
            title_wrap,
            subtitle,
            subtitle_show,
            subtitle_font_size,
            subtitle_alignment,
            subtitle_wrap,
            subtitle_bold,
            subtitle_italic,
            divider_show,
            divider_color,
            spacing_vertical,
            space_below_title,
            space_below_subtitle,
            space_below_title_area,
            padding_top,
            padding_right,
            padding_bottom,
            padding_left,
            drop_shadow,
            visual_header_show,
        )
    ):
        return {
            "status": "no-op",
            "visual": visual_name,
            "page": page_name,
            "updated_sections": [],
        }

    vco: dict[str, Any] = dict(visual.get("visualContainerObjects", {}))
    updated_sections: list[str] = []

    border_props: dict[str, Any] = {}
    if border_show is not None:
        border_props["show"] = _bool_expr(border_show)
    if border_color is not None:
        border_props["color"] = _solid_color_expr(border_color)
    if border_radius is not None:
        border_props["radius"] = _number_expr(border_radius, "D")
    if border_props:
        _upsert_properties_entry(vco, "border", border_props)
        updated_sections.append("border")

    background_props: dict[str, Any] = {}
    if background_show is not None:
        background_props["show"] = _bool_expr(background_show)
    if background_color is not None:
        background_props["color"] = _solid_color_expr(background_color)
    if background_transparency is not None:
        background_props["transparency"] = _number_expr(background_transparency, "D")
    if background_props:
        _upsert_properties_entry(vco, "background", background_props)
        updated_sections.append("background")

    title_props: dict[str, Any] = {}
    if title is not None:
        title_props["text"] = _text_expr(title)
    if title_color is not None:
        title_props["fontColor"] = _solid_color_expr(title_color)
    if title_font_size is not None:
        title_props["fontSize"] = _number_expr(title_font_size, "D")
    if title_font_family is not None:
        title_props["fontFamily"] = _text_expr(title_font_family)
    if title_alignment is not None:
        title_props["alignment"] = _text_expr(_normalize_container_alignment(title_alignment))
    if title_heading is not None:
        title_props["heading"] = _text_expr(title_heading)
    if title_wrap is not None:
        title_props["titleWrap"] = _bool_expr(title_wrap)
    if title_props:
        _upsert_properties_entry(vco, "title", title_props)
        updated_sections.append("title")

    subtitle_props: dict[str, Any] = {}
    if subtitle_show is not None:
        subtitle_props["show"] = _bool_expr(subtitle_show)
    if subtitle is not None:
        subtitle_props["text"] = _text_expr(subtitle)
        subtitle_props.setdefault("show", _bool_expr(True))
    if subtitle_font_size is not None:
        subtitle_props["fontSize"] = _number_expr(subtitle_font_size, "D")
    if subtitle_alignment is not None:
        subtitle_props["alignment"] = _text_expr(_normalize_container_alignment(subtitle_alignment))
    if subtitle_wrap is not None:
        subtitle_props["titleWrap"] = _bool_expr(subtitle_wrap)
    if subtitle_bold is not None:
        subtitle_props["bold"] = _bool_expr(subtitle_bold)
    if subtitle_italic is not None:
        subtitle_props["italic"] = _bool_expr(subtitle_italic)
    if subtitle_props:
        _upsert_properties_entry(vco, "subTitle", subtitle_props)
        updated_sections.append("subTitle")

    divider_props: dict[str, Any] = {}
    if divider_show is not None:
        divider_props["show"] = _bool_expr(divider_show)
    if divider_color is not None:
        divider_props["color"] = _solid_color_expr(divider_color)
    if divider_props:
        _upsert_properties_entry(vco, "divider", divider_props)
        updated_sections.append("divider")

    spacing_props: dict[str, Any] = {}
    if any(
        value is not None
        for value in (
            spacing_vertical,
            space_below_title,
            space_below_subtitle,
            space_below_title_area,
        )
    ):
        spacing_props["customizeSpacing"] = _bool_expr(True)
        if spacing_vertical is not None:
            spacing_props["verticalSpacing"] = _number_expr(spacing_vertical, "D")
        if space_below_title is not None:
            spacing_props["spaceBelowTitle"] = _number_expr(space_below_title, "D")
        if space_below_subtitle is not None:
            spacing_props["spaceBelowSubTitle"] = _number_expr(space_below_subtitle, "D")
        if space_below_title_area is not None:
            spacing_props["spaceBelowTitleArea"] = _number_expr(space_below_title_area, "D")
        _upsert_properties_entry(vco, "spacing", spacing_props)
        updated_sections.append("spacing")

    padding_props: dict[str, Any] = {}
    if padding_top is not None:
        padding_props["top"] = _number_expr(padding_top, "D")
    if padding_right is not None:
        padding_props["right"] = _number_expr(padding_right, "D")
    if padding_bottom is not None:
        padding_props["bottom"] = _number_expr(padding_bottom, "D")
    if padding_left is not None:
        padding_props["left"] = _number_expr(padding_left, "D")
    if padding_props:
        _upsert_properties_entry(vco, "padding", padding_props)
        updated_sections.append("padding")

    shadow_props: dict[str, Any] = {}
    if drop_shadow is not None:
        shadow_props["show"] = _bool_expr(drop_shadow)
    if shadow_props:
        _upsert_properties_entry(vco, "dropShadow", shadow_props)
        updated_sections.append("dropShadow")

    header_props: dict[str, Any] = {}
    if visual_header_show is not None:
        header_props["show"] = _bool_expr(visual_header_show)
    if header_props:
        _upsert_properties_entry(vco, "visualHeader", header_props)
        updated_sections.append("visualHeader")

    updated_visual = {**visual, "visualContainerObjects": vco}
    _write_json(visual_json_path, {**data, "visual": updated_visual})

    return {
        "status": "updated",
        "visual": visual_name,
        "page": page_name,
        "updated_sections": updated_sections,
    }


def visual_set_chart_style(
    definition_path: Path,
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
) -> dict[str, Any]:
    """Set common chart-formatting properties in ``visual.objects``."""
    visual_json_path, data, visual = _load_visual_json(definition_path, page_name, visual_name)

    for color in (category_axis_label_color, value_axis_label_color, labels_color):
        if color is not None:
            _validate_color(color)

    for label, number in (
        ("category_axis_font_size", category_axis_font_size),
        ("category_axis_preferred_width", category_axis_preferred_width),
        ("value_axis_font_size", value_axis_font_size),
        ("labels_font_size", labels_font_size),
        ("line_stroke_width", line_stroke_width),
    ):
        if number is not None:
            _validate_non_negative(number, label)

    if all(
        value is None
        for value in (
            legend_show,
            legend_position,
            category_axis_show,
            category_axis_title_show,
            category_axis_label_color,
            category_axis_font_size,
            category_axis_bold,
            category_axis_preferred_width,
            value_axis_show,
            value_axis_title_show,
            value_axis_gridlines_show,
            value_axis_label_color,
            value_axis_font_size,
            y2_axis_show,
            labels_show,
            labels_font_size,
            labels_bold,
            labels_position,
            labels_color,
            line_chart_type,
            line_stroke_width,
        )
    ):
        return {
            "status": "no-op",
            "visual": visual_name,
            "page": page_name,
            "updated_sections": [],
        }

    objects: dict[str, Any] = dict(visual.get("objects", {}))
    updated_sections: list[str] = []

    legend_props: dict[str, Any] = {}
    if legend_show is not None:
        legend_props["show"] = _bool_expr(legend_show)
    if legend_position is not None:
        legend_props["position"] = _text_expr(legend_position)
    if legend_props:
        _upsert_properties_entry(objects, "legend", legend_props)
        updated_sections.append("legend")

    category_axis_props: dict[str, Any] = {}
    if category_axis_show is not None:
        category_axis_props["show"] = _bool_expr(category_axis_show)
    if category_axis_title_show is not None:
        category_axis_props["showAxisTitle"] = _bool_expr(category_axis_title_show)
    if category_axis_label_color is not None:
        category_axis_props["labelColor"] = _solid_color_expr(category_axis_label_color)
    if category_axis_font_size is not None:
        category_axis_props["fontSize"] = _number_expr(category_axis_font_size, "D")
    if category_axis_bold is not None:
        category_axis_props["bold"] = _bool_expr(category_axis_bold)
    if category_axis_preferred_width is not None:
        category_axis_props["preferredCategoryWidth"] = _number_expr(
            category_axis_preferred_width,
            "D",
        )
    if category_axis_props:
        _upsert_properties_entry(objects, "categoryAxis", category_axis_props)
        updated_sections.append("categoryAxis")

    value_axis_props: dict[str, Any] = {}
    if value_axis_show is not None:
        value_axis_props["show"] = _bool_expr(value_axis_show)
    if value_axis_title_show is not None:
        value_axis_props["showAxisTitle"] = _bool_expr(value_axis_title_show)
    if value_axis_gridlines_show is not None:
        value_axis_props["gridlineShow"] = _bool_expr(value_axis_gridlines_show)
    if value_axis_label_color is not None:
        value_axis_props["labelColor"] = _solid_color_expr(value_axis_label_color)
    if value_axis_font_size is not None:
        value_axis_props["fontSize"] = _number_expr(value_axis_font_size, "D")
    if value_axis_props:
        _upsert_properties_entry(objects, "valueAxis", value_axis_props)
        updated_sections.append("valueAxis")

    y2_axis_props: dict[str, Any] = {}
    if y2_axis_show is not None:
        y2_axis_props["show"] = _bool_expr(y2_axis_show)
    if y2_axis_props:
        _upsert_properties_entry(objects, "y2Axis", y2_axis_props)
        updated_sections.append("y2Axis")

    labels_props: dict[str, Any] = {}
    if labels_show is not None:
        labels_props["show"] = _bool_expr(labels_show)
    if labels_font_size is not None:
        labels_props["fontSize"] = _number_expr(labels_font_size, "D")
    if labels_bold is not None:
        labels_props["bold"] = _bool_expr(labels_bold)
    if labels_position is not None:
        labels_props["labelPosition"] = _text_expr(labels_position)
    if labels_color is not None:
        labels_props["color"] = _solid_color_expr(labels_color)
    if labels_props:
        _upsert_properties_entry(objects, "labels", labels_props)
        updated_sections.append("labels")

    line_styles_props: dict[str, Any] = {}
    if line_chart_type is not None:
        line_styles_props["lineChartType"] = _text_expr(line_chart_type)
    if line_stroke_width is not None:
        line_styles_props["strokeWidth"] = _number_expr(line_stroke_width, "L")
    if line_styles_props:
        _upsert_properties_entry(objects, "lineStyles", line_styles_props)
        updated_sections.append("lineStyles")

    updated_visual = {**visual, "objects": objects}
    _write_json(visual_json_path, {**data, "visual": updated_visual})

    return {
        "status": "updated",
        "visual": visual_name,
        "page": page_name,
        "updated_sections": updated_sections,
    }


def visual_set_series_style(
    definition_path: Path,
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
) -> dict[str, Any]:
    """Set per-series style using metadata selectors in ``visual.objects``."""
    visual_json_path, data, visual = _load_visual_json(definition_path, page_name, visual_name)

    for color_value in (color, label_color):
        if color_value is not None:
            _validate_color(color_value)

    for label, number in (
        ("line_stroke_width", line_stroke_width),
        ("label_font_size", label_font_size),
    ):
        if number is not None:
            _validate_non_negative(number, label)

    if all(
        value is None
        for value in (
            color,
            line_stroke_width,
            line_chart_type,
            label_color,
            label_font_size,
            label_bold,
            label_position,
        )
    ):
        return {
            "status": "no-op",
            "visual": visual_name,
            "page": page_name,
            "query_ref": query_ref,
            "updated_sections": [],
        }

    objects: dict[str, Any] = dict(visual.get("objects", {}))
    updated_sections: list[str] = []

    if color is not None:
        _upsert_properties_entry(
            objects,
            "dataPoint",
            {"fill": _solid_color_expr(color)},
            selector=_metadata_selector(query_ref),
        )
        updated_sections.append("dataPoint")

    line_style_props: dict[str, Any] = {}
    if line_stroke_width is not None:
        line_style_props["strokeWidth"] = _number_expr(line_stroke_width, "L")
    if line_chart_type is not None:
        line_style_props["lineChartType"] = _text_expr(line_chart_type)
    if line_style_props:
        _upsert_properties_entry(
            objects,
            "lineStyles",
            line_style_props,
            selector=_metadata_selector(query_ref),
        )
        updated_sections.append("lineStyles")

    label_props: dict[str, Any] = {}
    if label_font_size is not None:
        label_props["fontSize"] = _number_expr(label_font_size, "D")
    if label_bold is not None:
        label_props["bold"] = _bool_expr(label_bold)
    if label_position is not None:
        label_props["labelPosition"] = _text_expr(label_position)
    if label_props:
        _upsert_properties_entry(
            objects,
            "labels",
            label_props,
            selector=_metadata_selector(query_ref),
        )
        updated_sections.append("labels")

    if label_color is not None:
        _upsert_properties_entry(
            objects,
            "labels",
            {"color": _solid_color_expr(label_color)},
            selector=_metadata_label_selector(query_ref),
        )
        updated_sections.append("labels")

    updated_visual = {**visual, "objects": objects}
    _write_json(visual_json_path, {**data, "visual": updated_visual})

    return {
        "status": "updated",
        "visual": visual_name,
        "page": page_name,
        "query_ref": query_ref,
        "updated_sections": updated_sections,
    }
