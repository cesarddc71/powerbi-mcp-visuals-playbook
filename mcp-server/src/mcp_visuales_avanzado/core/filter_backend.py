"""Pure-function backend for PBIR filter operations.

Every function takes a ``Path`` to the definition folder and returns a plain
Python dict suitable for ``format_result()``.

Filters are stored in ``filterConfig.filters[]`` inside either:
- ``pages/<page_name>/page.json`` for page-level filters
- ``pages/<page_name>/visuals/<visual_name>/visual.json`` for visual-level filters
"""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Any

from mcp_visuales_avanzado.core.errors import PbiCliError
from mcp_visuales_avanzado.core.pbir_path import get_page_dir, get_visual_dir

# ---------------------------------------------------------------------------
# JSON helpers
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


def _generate_name() -> str:
    """Generate a 20-character hex identifier matching PBIR convention."""
    return secrets.token_hex(10)


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------


def _resolve_target_path(
    definition_path: Path,
    page_name: str,
    visual_name: str | None,
) -> Path:
    """Return the JSON file path for the target (page or visual)."""
    if visual_name is None:
        return get_page_dir(definition_path, page_name) / "page.json"
    return get_visual_dir(definition_path, page_name, visual_name) / "visual.json"


def _get_filters(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the filters list from a page or visual JSON dict."""
    filter_config = data.get("filterConfig")
    if not isinstance(filter_config, dict):
        return []
    filters = filter_config.get("filters")
    if not isinstance(filters, list):
        return []
    return filters


def _set_filters(data: dict[str, Any], filters: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a new dict with filterConfig.filters replaced (immutable update)."""
    filter_config = dict(data.get("filterConfig") or {})
    filter_config["filters"] = filters
    return {**data, "filterConfig": filter_config}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def filter_list(
    definition_path: Path,
    page_name: str,
    visual_name: str | None = None,
) -> list[dict[str, Any]]:
    """List filters on a page or specific visual.

    If visual_name is None, returns page-level filters from page.json.
    If visual_name is given, returns visual-level filters from visual.json.
    Returns the raw filter dicts from filterConfig.filters[].
    """
    target = _resolve_target_path(definition_path, page_name, visual_name)
    if not target.exists():
        raise PbiCliError(f"File not found: {target}")
    data = _read_json(target)
    return _get_filters(data)


def _to_pbi_literal(value: str) -> str:
    """Convert a CLI string value to a Power BI literal.

    Power BI uses typed literals: strings are single-quoted (``'text'``),
    integers use an ``L`` suffix (``123L``), and doubles use ``D`` (``1.5D``).
    """
    # Try integer first (e.g. "2014" -> "2014L")
    try:
        int(value)
        return f"{value}L"
    except ValueError:
        pass
    # Try float (e.g. "3.14" -> "3.14D")
    try:
        float(value)
        return f"{value}D"
    except ValueError:
        pass
    # Fall back to string literal
    return f"'{value}'"


def _find_semantic_model_dir(definition_path: Path) -> Path | None:
    """Best-effort lookup of the sibling `.SemanticModel` folder."""
    report_folder = definition_path.parent
    project_root = report_folder.parent
    preferred = project_root / f"{report_folder.name.removesuffix('.Report')}.SemanticModel"
    if preferred.is_dir():
        return preferred

    for candidate in sorted(project_root.glob("*.SemanticModel")):
        if candidate.is_dir():
            return candidate
    return None


def _read_table_tmdl(definition_path: Path, table: str) -> str | None:
    """Read one table TMDL file from the sibling semantic model if present."""
    semantic_model_dir = _find_semantic_model_dir(definition_path)
    if semantic_model_dir is None:
        return None

    table_file = semantic_model_dir / "definition" / "tables" / f"{table}.tmdl"
    if not table_file.is_file():
        return None

    try:
        return table_file.read_text(encoding="utf-8")
    except OSError:
        return None


def _is_measure_in_semantic_model(definition_path: Path, table: str, name: str) -> bool:
    """Return whether `table[name]` is declared as a measure in local TMDL."""
    text = _read_table_tmdl(definition_path, table)
    if text is None:
        return False

    escaped = re.escape(name)
    patterns = (
        rf"(?m)^\s*measure\s+'{escaped}'\s*=",
        rf'(?m)^\s*measure\s+"{escaped}"\s*=',
        rf"(?m)^\s*measure\s+{escaped}\s*=",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def filter_add_categorical(
    definition_path: Path,
    page_name: str,
    table: str,
    column: str,
    values: list[str],
    visual_name: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Add a categorical filter to a page or visual.

    Builds the full filterConfig entry from table/column/values.
    The source alias is always the first letter of the table name (lowercase).
    Returns a status dict with name, type, and scope.
    """
    target = _resolve_target_path(definition_path, page_name, visual_name)
    if not target.exists():
        raise PbiCliError(f"File not found: {target}")

    filter_name = name if name is not None else _generate_name()
    alias = table[0].lower()
    scope = "visual" if visual_name is not None else "page"

    where_values: list[list[dict[str, Any]]] = [
        [{"Literal": {"Value": _to_pbi_literal(v)}}] for v in values
    ]

    entry: dict[str, Any] = {
        "name": filter_name,
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": column,
            }
        },
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": alias, "Entity": table, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": alias}},
                                        "Property": column,
                                    }
                                }
                            ],
                            "Values": where_values,
                        }
                    }
                }
            ],
        },
    }

    if scope == "page":
        entry["howCreated"] = "User"

    data = _read_json(target)
    filters = list(_get_filters(data))
    filters.append(entry)
    updated = _set_filters(data, filters)
    _write_json(target, updated)

    return {"status": "added", "name": filter_name, "type": "Categorical", "scope": scope}


def filter_remove(
    definition_path: Path,
    page_name: str,
    filter_name: str,
    visual_name: str | None = None,
) -> dict[str, Any]:
    """Remove a filter by name from a page or visual.

    Raises PbiCliError if filter_name is not found.
    Returns a status dict with the removed filter name.
    """
    target = _resolve_target_path(definition_path, page_name, visual_name)
    if not target.exists():
        raise PbiCliError(f"File not found: {target}")

    data = _read_json(target)
    filters = _get_filters(data)
    remaining = [f for f in filters if f.get("name") != filter_name]

    if len(remaining) == len(filters):
        raise PbiCliError(
            f"Filter '{filter_name}' not found on "
            f"{'visual ' + visual_name if visual_name else 'page'} '{page_name}'."
        )

    updated = _set_filters(data, remaining)
    _write_json(target, updated)
    return {"status": "removed", "name": filter_name}


def filter_add_topn(
    definition_path: Path,
    page_name: str,
    table: str,
    column: str,
    n: int,
    order_by_table: str,
    order_by_column: str,
    direction: str = "Top",
    visual_name: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Add a TopN filter to a page or visual.

    *direction* is ``"Top"`` (highest N by *order_by_column*) or
    ``"Bottom"`` (lowest N).  Direction maps to Power BI query Direction
    values: Top = 2 (Descending), Bottom = 1 (Ascending).

    Returns a status dict with name, type, scope, n, and direction.
    """
    direction_upper = direction.strip().capitalize()
    if direction_upper not in ("Top", "Bottom"):
        raise PbiCliError(f"direction must be 'Top' or 'Bottom', got '{direction}'.")

    pbi_direction = 2 if direction_upper == "Top" else 1

    target = _resolve_target_path(definition_path, page_name, visual_name)
    if not target.exists():
        raise PbiCliError(f"File not found: {target}")

    filter_name = name if name is not None else _generate_name()
    cat_alias = table[0].lower()
    ord_alias = order_by_table[0].lower()
    # Avoid alias collision when both tables start with the same letter
    if ord_alias == cat_alias and order_by_table != table:
        ord_alias = ord_alias + "2"
    scope = "visual" if visual_name is not None else "page"

    # Inner subquery From: include both tables when they differ
    inner_from: list[dict[str, Any]] = [
        {"Name": cat_alias, "Entity": table, "Type": 0},
    ]
    if order_by_table != table:
        inner_from.append({"Name": ord_alias, "Entity": order_by_table, "Type": 0})

    order_source_alias = ord_alias if order_by_table != table else cat_alias
    order_is_measure = _is_measure_in_semantic_model(definition_path, order_by_table, order_by_column)

    if order_is_measure:
        order_expression: dict[str, Any] = {
            "Measure": {
                "Expression": {"SourceRef": {"Source": order_source_alias}},
                "Property": order_by_column,
            }
        }
    else:
        order_expression = {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": order_source_alias}},
                        "Property": order_by_column,
                    }
                },
                "Function": 0,
            }
        }

    entry: dict[str, Any] = {
        "name": filter_name,
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": column,
            }
        },
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {
                    "Name": "subquery",
                    "Expression": {
                        "Subquery": {
                            "Query": {
                                "Version": 2,
                                "From": inner_from,
                                "Select": [
                                    {
                                        "Column": {
                                            "Expression": {"SourceRef": {"Source": cat_alias}},
                                            "Property": column,
                                        },
                                        "Name": "field",
                                    }
                                ],
                                "OrderBy": [
                                    {
                                        "Direction": pbi_direction,
                                        "Expression": order_expression,
                                    }
                                ],
                                "Top": n,
                            }
                        }
                    },
                    "Type": 2,
                },
                {"Name": cat_alias, "Entity": table, "Type": 0},
            ],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": cat_alias}},
                                        "Property": column,
                                    }
                                }
                            ],
                            "Table": {"SourceRef": {"Source": "subquery"}},
                        }
                    }
                }
            ],
        },
    }

    if scope == "page":
        entry["howCreated"] = "User"

    data = _read_json(target)
    filters = list(_get_filters(data))
    filters.append(entry)
    updated = _set_filters(data, filters)
    _write_json(target, updated)

    return {
        "status": "added",
        "name": filter_name,
        "type": "TopN",
        "scope": scope,
        "n": n,
        "direction": direction_upper,
    }


# TimeUnit integer codes used by Power BI for RelativeDate filters.
_RELATIVE_DATE_TIME_UNITS: dict[str, int] = {
    "days": 0,
    "weeks": 1,
    "months": 2,
    "years": 3,
}


def filter_add_relative_date(
    definition_path: Path,
    page_name: str,
    table: str,
    column: str,
    amount: int,
    time_unit: str,
    visual_name: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Add a RelativeDate filter (e.g. "last 3 months") to a page or visual.

    *amount* is a positive integer representing the period count.
    *time_unit* is one of ``"days"``, ``"weeks"``, ``"months"``, ``"years"``.

    The filter matches rows where *column* falls in the last *amount* *time_unit*
    relative to today (inclusive of the current period boundary).

    Returns a status dict with name, type, scope, amount, and time_unit.
    """
    time_unit_lower = time_unit.strip().lower()
    if time_unit_lower not in _RELATIVE_DATE_TIME_UNITS:
        valid = ", ".join(_RELATIVE_DATE_TIME_UNITS)
        raise PbiCliError(f"time_unit must be one of {valid}, got '{time_unit}'.")
    time_unit_code = _RELATIVE_DATE_TIME_UNITS[time_unit_lower]
    days_code = _RELATIVE_DATE_TIME_UNITS["days"]

    target = _resolve_target_path(definition_path, page_name, visual_name)
    if not target.exists():
        raise PbiCliError(f"File not found: {target}")

    filter_name = name if name is not None else _generate_name()
    alias = table[0].lower()
    scope = "visual" if visual_name is not None else "page"

    # LowerBound: DateSpan(DateAdd(DateAdd(Now(), +1, days), -amount, time_unit), days)
    lower_bound: dict[str, Any] = {
        "DateSpan": {
            "Expression": {
                "DateAdd": {
                    "Expression": {
                        "DateAdd": {
                            "Expression": {"Now": {}},
                            "Amount": 1,
                            "TimeUnit": days_code,
                        }
                    },
                    "Amount": -amount,
                    "TimeUnit": time_unit_code,
                }
            },
            "TimeUnit": days_code,
        }
    }

    # UpperBound: DateSpan(Now(), days)
    upper_bound: dict[str, Any] = {
        "DateSpan": {
            "Expression": {"Now": {}},
            "TimeUnit": days_code,
        }
    }

    entry: dict[str, Any] = {
        "name": filter_name,
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": column,
            }
        },
        "type": "RelativeDate",
        "filter": {
            "Version": 2,
            "From": [{"Name": alias, "Entity": table, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "Between": {
                            "Expression": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Source": alias}},
                                    "Property": column,
                                }
                            },
                            "LowerBound": lower_bound,
                            "UpperBound": upper_bound,
                        }
                    }
                }
            ],
        },
    }

    if scope == "page":
        entry["howCreated"] = "User"

    data = _read_json(target)
    filters = list(_get_filters(data))
    filters.append(entry)
    updated = _set_filters(data, filters)
    _write_json(target, updated)

    return {
        "status": "added",
        "name": filter_name,
        "type": "RelativeDate",
        "scope": scope,
        "amount": amount,
        "time_unit": time_unit_lower,
    }


def filter_clear(
    definition_path: Path,
    page_name: str,
    visual_name: str | None = None,
) -> dict[str, Any]:
    """Remove all filters from a page or visual.

    Returns a status dict with the count of removed filters and scope.
    """
    target = _resolve_target_path(definition_path, page_name, visual_name)
    if not target.exists():
        raise PbiCliError(f"File not found: {target}")

    scope = "visual" if visual_name is not None else "page"
    data = _read_json(target)
    filters = _get_filters(data)
    removed = len(filters)

    updated = _set_filters(data, [])
    _write_json(target, updated)
    return {"status": "cleared", "removed": removed, "scope": scope}
