"""Enhanced PBIR validation beyond basic structure checks.

Provides three tiers of validation:
  1. Structural: folder layout and file existence (in pbir_path.py)
  2. Schema: required fields, valid types, cross-file consistency
  3. Model-aware: field bindings against a connected semantic model (optional)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Immutable container for a single validation finding."""

    level: str  # "error", "warning", "info"
    file: str
    message: str


def validate_report_full(definition_path: Path) -> dict[str, Any]:
    """Run all validation tiers and return a structured report.

    Returns a dict with ``valid``, ``errors``, ``warnings``, and ``summary``.
    """
    findings: list[ValidationResult] = []

    # Tier 1: structural (reuse existing)
    from mcp_visuales_avanzado.core.pbir_path import validate_report_structure

    structural = validate_report_structure(definition_path)
    for msg in structural:
        findings.append(ValidationResult("error", "", msg))

    if not definition_path.is_dir():
        return _build_result(findings)

    # Tier 2: JSON syntax
    findings.extend(_validate_json_syntax(definition_path))

    # Tier 2: schema validation per file type
    findings.extend(_validate_report_json(definition_path))
    findings.extend(_validate_version_json(definition_path))
    findings.extend(_validate_pages_metadata(definition_path))
    findings.extend(_validate_all_pages(definition_path))
    findings.extend(_validate_all_visuals(definition_path))

    # Tier 2: cross-file consistency
    findings.extend(_validate_page_order_consistency(definition_path))
    findings.extend(_validate_visual_name_uniqueness(definition_path))

    return _build_result(findings)


def validate_bindings_against_model(
    definition_path: Path,
    model_tables: list[dict[str, Any]],
) -> list[ValidationResult]:
    """Tier 3: cross-reference visual field bindings against a model.

    ``model_tables`` should be a list of dicts with 'name' and 'columns' keys,
    where 'columns' is a list of dicts with 'name' keys. Measures are included
    as columns.
    """
    findings: list[ValidationResult] = []

    # Build lookup set
    valid_fields: set[str] = set()
    for table in model_tables:
        table_name = table.get("name", "")
        for col in table.get("columns", []):
            valid_fields.add(f"{table_name}[{col.get('name', '')}]")
        for mea in table.get("measures", []):
            valid_fields.add(f"{table_name}[{mea.get('name', '')}]")

    pages_dir = definition_path / "pages"
    if not pages_dir.is_dir():
        return findings

    for page_dir in sorted(pages_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        visuals_dir = page_dir / "visuals"
        if not visuals_dir.is_dir():
            continue
        for vdir in sorted(visuals_dir.iterdir()):
            if not vdir.is_dir():
                continue
            vfile = vdir / "visual.json"
            if not vfile.exists():
                continue
            try:
                data = json.loads(vfile.read_text(encoding="utf-8"))
                visual_config = data.get("visual", {})
                query = visual_config.get("query", {})

                # Check Commands-based bindings
                for cmd in query.get("Commands", []):
                    sq = cmd.get("SemanticQueryDataShapeCommand", {}).get("Query", {})
                    sources = {s["Name"]: s["Entity"] for s in sq.get("From", [])}
                    for sel in sq.get("Select", []):
                        ref = _extract_field_ref(sel, sources)
                        if ref and ref not in valid_fields:
                            rel = f"{page_dir.name}/visuals/{vdir.name}"
                            findings.append(
                                ValidationResult(
                                    "warning",
                                    rel,
                                    f"Field '{ref}' not found in semantic model",
                                )
                            )
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    return findings


# ---------------------------------------------------------------------------
# Tier 2 validators
# ---------------------------------------------------------------------------


def _validate_json_syntax(definition_path: Path) -> list[ValidationResult]:
    """Check all JSON files parse without errors."""
    findings: list[ValidationResult] = []
    for json_file in definition_path.rglob("*.json"):
        try:
            json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            rel = str(json_file.relative_to(definition_path))
            findings.append(ValidationResult("error", rel, f"Invalid JSON: {e}"))
    return findings


def _validate_report_json(definition_path: Path) -> list[ValidationResult]:
    """Validate report.json required fields and schema."""
    findings: list[ValidationResult] = []
    report_json = definition_path / "report.json"
    if not report_json.exists():
        return findings  # Structural check already caught this

    try:
        data = json.loads(report_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return findings

    if "$schema" not in data:
        findings.append(ValidationResult("warning", "report.json", "Missing $schema reference"))

    if "themeCollection" not in data:
        findings.append(
            ValidationResult("error", "report.json", "Missing required 'themeCollection'")
        )
    else:
        tc = data["themeCollection"]
        if "baseTheme" not in tc:
            findings.append(
                ValidationResult("warning", "report.json", "themeCollection missing 'baseTheme'")
            )

    return findings


def _validate_version_json(definition_path: Path) -> list[ValidationResult]:
    """Validate version.json content."""
    findings: list[ValidationResult] = []
    version_json = definition_path / "version.json"
    if not version_json.exists():
        return findings

    try:
        data = json.loads(version_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return findings

    if "version" not in data:
        findings.append(ValidationResult("error", "version.json", "Missing required 'version'"))

    return findings


def _validate_pages_metadata(definition_path: Path) -> list[ValidationResult]:
    """Validate pages.json if present."""
    findings: list[ValidationResult] = []
    pages_json = definition_path / "pages" / "pages.json"
    if not pages_json.exists():
        return findings

    try:
        data = json.loads(pages_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return findings

    page_order = data.get("pageOrder", [])
    if not isinstance(page_order, list):
        findings.append(
            ValidationResult("error", "pages/pages.json", "'pageOrder' must be an array")
        )

    return findings


def _validate_all_pages(definition_path: Path) -> list[ValidationResult]:
    """Validate individual page.json files."""
    findings: list[ValidationResult] = []
    pages_dir = definition_path / "pages"
    if not pages_dir.is_dir():
        return findings

    for page_dir in sorted(pages_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        page_json = page_dir / "page.json"
        if not page_json.exists():
            continue

        try:
            data = json.loads(page_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        rel = f"pages/{page_dir.name}/page.json"

        for req in ("name", "displayName", "displayOption"):
            if req not in data:
                findings.append(ValidationResult("error", rel, f"Missing required '{req}'"))

        valid_options = {
            "FitToPage",
            "FitToWidth",
            "ActualSize",
            "ActualSizeTopLeft",
            "DeprecatedDynamic",
        }
        opt = data.get("displayOption")
        if opt and opt not in valid_options:
            findings.append(ValidationResult("warning", rel, f"Unknown displayOption '{opt}'"))

        if opt != "DeprecatedDynamic":
            if "width" not in data:
                findings.append(ValidationResult("error", rel, "Missing required 'width'"))
            if "height" not in data:
                findings.append(ValidationResult("error", rel, "Missing required 'height'"))

        name = data.get("name", "")
        if name and len(name) > 50:
            findings.append(
                ValidationResult("warning", rel, f"Name exceeds 50 chars: '{name[:20]}...'")
            )

    return findings


def _validate_all_visuals(definition_path: Path) -> list[ValidationResult]:
    """Validate individual visual.json files."""
    findings: list[ValidationResult] = []
    pages_dir = definition_path / "pages"
    if not pages_dir.is_dir():
        return findings

    for page_dir in sorted(pages_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        visuals_dir = page_dir / "visuals"
        if not visuals_dir.is_dir():
            continue
        for vdir in sorted(visuals_dir.iterdir()):
            if not vdir.is_dir():
                continue
            vfile = vdir / "visual.json"
            if not vfile.exists():
                continue

            try:
                data = json.loads(vfile.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

            rel = f"pages/{page_dir.name}/visuals/{vdir.name}/visual.json"

            if "name" not in data:
                findings.append(ValidationResult("error", rel, "Missing required 'name'"))

            if "position" not in data:
                findings.append(ValidationResult("error", rel, "Missing required 'position'"))
            else:
                pos = data["position"]
                for req in ("x", "y", "width", "height"):
                    if req not in pos:
                        findings.append(
                            ValidationResult("error", rel, f"Position missing required '{req}'")
                        )

            visual_config = data.get("visual", {})
            vtype = visual_config.get("visualType", "")
            if not vtype:
                # Could be a visualGroup, which is also valid
                if "visualGroup" not in data:
                    findings.append(
                        ValidationResult(
                            "warning",
                            rel,
                            "Missing 'visual.visualType' (not a visual group either)",
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Cross-file consistency
# ---------------------------------------------------------------------------


def _validate_page_order_consistency(definition_path: Path) -> list[ValidationResult]:
    """Check that pages.json references match actual page folders."""
    findings: list[ValidationResult] = []
    pages_json = definition_path / "pages" / "pages.json"
    if not pages_json.exists():
        return findings

    try:
        data = json.loads(pages_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return findings

    page_order = data.get("pageOrder", [])
    pages_dir = definition_path / "pages"

    actual_pages = {
        d.name for d in pages_dir.iterdir() if d.is_dir() and (d / "page.json").exists()
    }

    for name in page_order:
        if name not in actual_pages:
            findings.append(
                ValidationResult(
                    "warning",
                    "pages/pages.json",
                    f"pageOrder references '{name}' but no such page folder exists",
                )
            )

    unlisted = actual_pages - set(page_order)
    for name in sorted(unlisted):
        findings.append(
            ValidationResult(
                "info",
                "pages/pages.json",
                f"Page '{name}' exists but is not listed in pageOrder",
            )
        )

    return findings


def _validate_visual_name_uniqueness(definition_path: Path) -> list[ValidationResult]:
    """Check that visual names are unique within each page."""
    findings: list[ValidationResult] = []
    pages_dir = definition_path / "pages"
    if not pages_dir.is_dir():
        return findings

    for page_dir in sorted(pages_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        visuals_dir = page_dir / "visuals"
        if not visuals_dir.is_dir():
            continue

        names_seen: dict[str, str] = {}
        for vdir in sorted(visuals_dir.iterdir()):
            if not vdir.is_dir():
                continue
            vfile = vdir / "visual.json"
            if not vfile.exists():
                continue
            try:
                data = json.loads(vfile.read_text(encoding="utf-8"))
                name = data.get("name", "")
                if name in names_seen:
                    rel = f"pages/{page_dir.name}/visuals/{vdir.name}/visual.json"
                    findings.append(
                        ValidationResult(
                            "error",
                            rel,
                            f"Duplicate visual name '{name}' (also in {names_seen[name]})",
                        )
                    )
                else:
                    names_seen[name] = vdir.name
            except (json.JSONDecodeError, KeyError):
                continue

    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_result(findings: list[ValidationResult]) -> dict[str, Any]:
    """Build the final validation report dict."""
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    infos = [f for f in findings if f.level == "info"]

    return {
        "valid": len(errors) == 0,
        "errors": [{"file": f.file, "message": f.message} for f in errors],
        "warnings": [{"file": f.file, "message": f.message} for f in warnings],
        "info": [{"file": f.file, "message": f.message} for f in infos],
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(infos),
        },
    }


def _extract_field_ref(select_item: dict[str, Any], sources: dict[str, str]) -> str | None:
    """Extract a Table[Column] reference from a semantic query select item."""
    for kind in ("Column", "Measure"):
        if kind in select_item:
            item = select_item[kind]
            source_name = item.get("Expression", {}).get("SourceRef", {}).get("Source", "")
            prop = item.get("Property", "")
            table = sources.get(source_name, source_name)
            if table and prop:
                return f"{table}[{prop}]"
    return None
