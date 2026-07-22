"""Pure-function backend for PBIR conditional formatting operations.

Mirrors ``report_backend.py`` but focuses on visual conditional formatting.
Every function takes a ``Path`` to the definition folder and returns a plain
Python dict suitable for ``format_result()``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp_visuales_avanzado.core.errors import PbiCliError
from mcp_visuales_avanzado.core.pbir_path import get_visual_dir

# ---------------------------------------------------------------------------
# JSON helpers (same as report_backend / visual_backend)
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file."""
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with consistent formatting."""
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_visual(definition_path: Path, page_name: str, visual_name: str) -> dict[str, Any]:
    """Load and return visual JSON data, raising PbiCliError if missing."""
    visual_path = get_visual_dir(definition_path, page_name, visual_name) / "visual.json"
    if not visual_path.exists():
        raise PbiCliError(
            f"Visual '{visual_name}' not found on page '{page_name}'. Expected: {visual_path}"
        )
    return _read_json(visual_path)


def _save_visual(
    definition_path: Path,
    page_name: str,
    visual_name: str,
    data: dict[str, Any],
) -> None:
    """Write visual JSON data back to disk.

    A ``.json.bak`` copy of the previous file is created before writing so
    that a corrupted write can be recovered manually.
    """
    visual_path = get_visual_dir(definition_path, page_name, visual_name) / "visual.json"
    if visual_path.exists():
        backup_path = visual_path.with_suffix(".json.bak")
        backup_path.write_bytes(visual_path.read_bytes())
    _write_json(visual_path, data)


def _get_values_list(objects: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the objects.values list, defaulting to empty."""
    return list(objects.get("values", []))


def _replace_or_append(
    values: list[dict[str, Any]],
    new_entry: dict[str, Any],
    field_query_ref: str,
) -> list[dict[str, Any]]:
    """Return a new list with *new_entry* replacing any existing entry
    whose ``selector.metadata`` matches *field_query_ref*, or appended
    if no match exists. Immutable -- does not modify the input list.
    """
    replaced = False
    result: list[dict[str, Any]] = []
    for entry in values:
        meta = entry.get("selector", {}).get("metadata", "")
        if meta == field_query_ref:
            result.append(new_entry)
            replaced = True
        else:
            result.append(entry)
    if not replaced:
        result.append(new_entry)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_get(
    definition_path: Path,
    page_name: str,
    visual_name: str,
) -> dict[str, Any]:
    """Return current formatting objects for a visual.

    Returns ``{"visual": visual_name, "objects": {...}}`` where *objects*
    is the content of ``visual.objects`` (empty dict if absent).
    """
    data = _load_visual(definition_path, page_name, visual_name)
    objects = data.get("visual", {}).get("objects", {})
    return {"visual": visual_name, "objects": objects}


def format_clear(
    definition_path: Path,
    page_name: str,
    visual_name: str,
) -> dict[str, Any]:
    """Clear all formatting objects from a visual.

    Sets ``visual.objects`` to ``{}`` and persists the change.
    Returns ``{"status": "cleared", "visual": visual_name}``.
    """
    data = _load_visual(definition_path, page_name, visual_name)
    visual_section = dict(data.get("visual", {}))
    visual_section["objects"] = {}
    new_data = {**data, "visual": visual_section}
    _save_visual(definition_path, page_name, visual_name, new_data)
    return {"status": "cleared", "visual": visual_name}


def format_background_gradient(
    definition_path: Path,
    page_name: str,
    visual_name: str,
    input_table: str,
    input_column: str,
    field_query_ref: str,
    min_color: str = "#FFFFFF",
    max_color: str = "#118DFF",
) -> dict[str, Any]:
    """Add a linear gradient background color rule to a visual column.

    *input_table* / *input_column*: the measure/column driving the gradient
    (used for the FillRule.Input Aggregation).

    *field_query_ref*: the queryRef of the target field (e.g.
    ``"Sum(financials.Profit)"``). Used as ``selector.metadata``.

    Adds/replaces the entry in ``visual.objects.values[]`` whose
    ``selector.metadata`` matches *field_query_ref*.

    Returns ``{"status": "applied", "visual": visual_name,
    "rule": "gradient", "field": field_query_ref}``.
    """
    data = _load_visual(definition_path, page_name, visual_name)
    visual_section = dict(data.get("visual", {}))
    objects = dict(visual_section.get("objects", {}))
    values = _get_values_list(objects)

    new_entry: dict[str, Any] = {
        "properties": {
            "backColor": {
                "solid": {
                    "color": {
                        "expr": {
                            "FillRule": {
                                "Input": {
                                    "Aggregation": {
                                        "Expression": {
                                            "Column": {
                                                "Expression": {
                                                    "SourceRef": {"Entity": input_table}
                                                },
                                                "Property": input_column,
                                            }
                                        },
                                        "Function": 0,
                                    }
                                },
                                "FillRule": {
                                    "linearGradient2": {
                                        "min": {
                                            "color": {"Literal": {"Value": f"'{min_color}'"}},
                                            "nullColoringStrategy": {
                                                "strategy": {"Literal": {"Value": "'asZero'"}}
                                            },
                                        },
                                        "max": {"color": {"Literal": {"Value": f"'{max_color}'"}}},
                                    }
                                },
                            }
                        }
                    }
                }
            }
        },
        "selector": {
            "data": [{"dataViewWildcard": {"matchingOption": 1}}],
            "metadata": field_query_ref,
        },
    }

    new_values = _replace_or_append(values, new_entry, field_query_ref)
    new_objects = {**objects, "values": new_values}
    new_visual = {**visual_section, "objects": new_objects}
    new_data = {**data, "visual": new_visual}
    _save_visual(definition_path, page_name, visual_name, new_data)

    return {
        "status": "applied",
        "visual": visual_name,
        "rule": "gradient",
        "field": field_query_ref,
    }


# ComparisonKind integer codes (Power BI query expression).
_COMPARISON_KINDS: dict[str, int] = {
    "eq": 0,
    "neq": 1,
    "gt": 2,
    "gte": 3,
    "lt": 4,
    "lte": 5,
}


def format_background_conditional(
    definition_path: Path,
    page_name: str,
    visual_name: str,
    input_table: str,
    input_column: str,
    threshold: float | int,
    color_hex: str,
    comparison: str = "gt",
    field_query_ref: str | None = None,
) -> dict[str, Any]:
    """Add a rule-based conditional background color to a visual column.

    When the aggregated value of *input_column* satisfies the comparison
    against *threshold*, the cell background is set to *color_hex*.

    *comparison* is one of ``"eq"``, ``"neq"``, ``"gt"``, ``"gte"``,
    ``"lt"``, ``"lte"`` (default ``"gt"``).

    *field_query_ref* is the ``selector.metadata`` queryRef of the target
    field (e.g. ``"Sum(financials.Units Sold)"``).  Defaults to
    ``"Sum({table}.{column})"`` if omitted.

    Returns ``{"status": "applied", "visual": visual_name,
    "rule": "conditional", "field": field_query_ref}``.
    """
    comparison_lower = comparison.strip().lower()
    if comparison_lower not in _COMPARISON_KINDS:
        valid = ", ".join(_COMPARISON_KINDS)
        raise PbiCliError(f"comparison must be one of {valid}, got '{comparison}'.")
    comparison_kind = _COMPARISON_KINDS[comparison_lower]

    if field_query_ref is None:
        field_query_ref = f"Sum({input_table}.{input_column})"

    # Format threshold as a Power BI decimal literal (D suffix).
    threshold_literal = f"{threshold}D"

    data = _load_visual(definition_path, page_name, visual_name)
    visual_section = dict(data.get("visual", {}))
    objects = dict(visual_section.get("objects", {}))
    values = _get_values_list(objects)

    new_entry: dict[str, Any] = {
        "properties": {
            "backColor": {
                "solid": {
                    "color": {
                        "expr": {
                            "Conditional": {
                                "Cases": [
                                    {
                                        "Condition": {
                                            "Comparison": {
                                                "ComparisonKind": comparison_kind,
                                                "Left": {
                                                    "Aggregation": {
                                                        "Expression": {
                                                            "Column": {
                                                                "Expression": {
                                                                    "SourceRef": {
                                                                        "Entity": input_table
                                                                    }
                                                                },
                                                                "Property": input_column,
                                                            }
                                                        },
                                                        "Function": 0,
                                                    }
                                                },
                                                "Right": {"Literal": {"Value": threshold_literal}},
                                            }
                                        },
                                        "Value": {"Literal": {"Value": f"'{color_hex}'"}},
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        "selector": {
            "data": [{"dataViewWildcard": {"matchingOption": 1}}],
            "metadata": field_query_ref,
        },
    }

    new_values = _replace_or_append(values, new_entry, field_query_ref)
    new_objects = {**objects, "values": new_values}
    new_visual = {**visual_section, "objects": new_objects}
    new_data = {**data, "visual": new_visual}
    _save_visual(definition_path, page_name, visual_name, new_data)

    return {
        "status": "applied",
        "visual": visual_name,
        "rule": "conditional",
        "field": field_query_ref,
    }


def format_background_measure(
    definition_path: Path,
    page_name: str,
    visual_name: str,
    measure_table: str,
    measure_property: str,
    field_query_ref: str,
) -> dict[str, Any]:
    """Add a measure-driven background color rule to a visual column.

    *measure_table* / *measure_property*: the DAX measure that returns a
    hex color string.

    *field_query_ref*: the queryRef of the target field.

    Adds/replaces the entry in ``visual.objects.values[]`` whose
    ``selector.metadata`` matches *field_query_ref*.

    Returns ``{"status": "applied", "visual": visual_name,
    "rule": "measure", "field": field_query_ref}``.
    """
    data = _load_visual(definition_path, page_name, visual_name)
    visual_section = dict(data.get("visual", {}))
    objects = dict(visual_section.get("objects", {}))
    values = _get_values_list(objects)

    new_entry: dict[str, Any] = {
        "properties": {
            "backColor": {
                "solid": {
                    "color": {
                        "expr": {
                            "Measure": {
                                "Expression": {"SourceRef": {"Entity": measure_table}},
                                "Property": measure_property,
                            }
                        }
                    }
                }
            }
        },
        "selector": {
            "data": [{"dataViewWildcard": {"matchingOption": 1}}],
            "metadata": field_query_ref,
        },
    }

    new_values = _replace_or_append(values, new_entry, field_query_ref)
    new_objects = {**objects, "values": new_values}
    new_visual = {**visual_section, "objects": new_objects}
    new_data = {**data, "visual": new_visual}
    _save_visual(definition_path, page_name, visual_name, new_data)

    return {
        "status": "applied",
        "visual": visual_name,
        "rule": "measure",
        "field": field_query_ref,
    }
