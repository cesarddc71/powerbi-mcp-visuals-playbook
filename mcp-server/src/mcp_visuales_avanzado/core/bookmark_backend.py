"""Pure-function backend for PBIR bookmark operations.

Mirrors ``report_backend.py`` but operates on the bookmarks subfolder.
Every function takes a ``Path`` to the definition folder and returns a plain
Python dict suitable for ``format_result()``.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from mcp_visuales_avanzado.core.errors import PbiCliError

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

SCHEMA_BOOKMARKS_METADATA = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json"
)
SCHEMA_BOOKMARK = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/bookmark/2.1.0/schema.json"
)

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
# Path helpers
# ---------------------------------------------------------------------------


def _bookmarks_dir(definition_path: Path) -> Path:
    return definition_path / "bookmarks"


def _index_path(definition_path: Path) -> Path:
    return _bookmarks_dir(definition_path) / "bookmarks.json"


def _bookmark_path(definition_path: Path, name: str) -> Path:
    return _bookmarks_dir(definition_path) / f"{name}.bookmark.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bookmark_list(definition_path: Path) -> list[dict[str, Any]]:
    """List all bookmarks.

    Returns a list of ``{name, display_name, active_section}`` dicts.
    Returns ``[]`` if the bookmarks folder or index does not exist.
    """
    index_file = _index_path(definition_path)
    if not index_file.exists():
        return []

    index = _read_json(index_file)
    items: list[dict[str, Any]] = index.get("items", [])

    results: list[dict[str, Any]] = []
    for item in items:
        name = item.get("name", "")
        bm_file = _bookmark_path(definition_path, name)
        if not bm_file.exists():
            continue
        bm = _read_json(bm_file)
        exploration = bm.get("explorationState", {})
        results.append(
            {
                "name": name,
                "display_name": bm.get("displayName", ""),
                "active_section": exploration.get("activeSection"),
            }
        )

    return results


def bookmark_get(definition_path: Path, name: str) -> dict[str, Any]:
    """Get the full data for a single bookmark by name.

    Raises ``PbiCliError`` if the bookmark does not exist.
    """
    bm_file = _bookmark_path(definition_path, name)
    if not bm_file.exists():
        raise PbiCliError(f"Bookmark '{name}' not found.")
    return _read_json(bm_file)


def bookmark_add(
    definition_path: Path,
    display_name: str,
    target_page: str,
    name: str | None = None,
) -> dict[str, Any]:
    """Create a new bookmark pointing to *target_page*.

    Creates the ``bookmarks/`` directory and ``bookmarks.json`` index if they
    do not already exist. Returns a status dict with the created bookmark info.
    """
    bm_name = name if name is not None else _generate_name()

    bm_dir = _bookmarks_dir(definition_path)
    bm_dir.mkdir(parents=True, exist_ok=True)

    index_file = _index_path(definition_path)
    if index_file.exists():
        index = _read_json(index_file)
    else:
        index = {"$schema": SCHEMA_BOOKMARKS_METADATA, "items": []}

    index["items"] = list(index.get("items", []))
    index["items"].append({"name": bm_name})
    _write_json(index_file, index)

    bookmark_data: dict[str, Any] = {
        "$schema": SCHEMA_BOOKMARK,
        "displayName": display_name,
        "name": bm_name,
        "options": {"targetVisualNames": []},
        "explorationState": {
            "version": "1.3",
            "activeSection": target_page,
        },
    }
    _write_json(_bookmark_path(definition_path, bm_name), bookmark_data)

    return {
        "status": "created",
        "name": bm_name,
        "display_name": display_name,
        "target_page": target_page,
    }


def bookmark_delete(
    definition_path: Path,
    name: str,
) -> dict[str, Any]:
    """Delete a bookmark by name.

    Removes the ``.bookmark.json`` file and its entry in ``bookmarks.json``.
    Raises ``PbiCliError`` if the bookmark is not found.
    """
    index_file = _index_path(definition_path)
    if not index_file.exists():
        raise PbiCliError(f"Bookmark '{name}' not found.")

    index = _read_json(index_file)
    items: list[dict[str, Any]] = index.get("items", [])
    existing_names = [i.get("name") for i in items]

    if name not in existing_names:
        raise PbiCliError(f"Bookmark '{name}' not found.")

    bm_file = _bookmark_path(definition_path, name)
    if bm_file.exists():
        bm_file.unlink()

    updated_items = [i for i in items if i.get("name") != name]
    updated_index = {**index, "items": updated_items}
    _write_json(index_file, updated_index)

    return {"status": "deleted", "name": name}


def bookmark_set_visibility(
    definition_path: Path,
    name: str,
    page_name: str,
    visual_name: str,
    hidden: bool,
) -> dict[str, Any]:
    """Set a visual's hidden/visible state inside a bookmark's explorationState.

    When *hidden* is ``True``, sets ``singleVisual.display.mode = "hidden"``.
    When *hidden* is ``False``, removes the ``display`` key from ``singleVisual``
    (presence of ``display`` is what hides the visual in Power BI Desktop).

    Creates the ``explorationState.sections.{page_name}.visualContainers.{visual_name}``
    path if it does not already exist in the bookmark.

    Raises ``PbiCliError`` if the bookmark does not exist.
    Returns a status dict with name, page, visual, and the new visibility state.
    """
    bm_file = _bookmark_path(definition_path, name)
    if not bm_file.exists():
        raise PbiCliError(f"Bookmark '{name}' not found.")

    bm = _read_json(bm_file)

    # Navigate / build the explorationState path immutably.
    exploration = dict(bm.get("explorationState") or {})
    sections = dict(exploration.get("sections") or {})
    page_section = dict(sections.get(page_name) or {})
    visual_containers = dict(page_section.get("visualContainers") or {})
    container = dict(visual_containers.get(visual_name) or {})
    single_visual = dict(container.get("singleVisual") or {})

    if hidden:
        single_visual = {**single_visual, "display": {"mode": "hidden"}}
    else:
        single_visual = {k: v for k, v in single_visual.items() if k != "display"}

    new_container = {**container, "singleVisual": single_visual}
    new_visual_containers = {**visual_containers, visual_name: new_container}
    new_page_section = {**page_section, "visualContainers": new_visual_containers}
    new_sections = {**sections, page_name: new_page_section}
    new_exploration = {**exploration, "sections": new_sections}
    new_bm = {**bm, "explorationState": new_exploration}

    _write_json(bm_file, new_bm)

    return {
        "status": "updated",
        "bookmark": name,
        "page": page_name,
        "visual": visual_name,
        "hidden": hidden,
    }
