"""PBIR JSON to HTML/SVG renderer.

Renders a simplified structural preview of PBIR report pages.
Not pixel-perfect Power BI rendering -- shows layout, visual types,
and field bindings for validation before opening in Desktop.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


def render_report(definition_path: Path) -> str:
    """Render a full PBIR report as an HTML page."""
    report_data = _read_json(definition_path / "report.json")
    theme = report_data.get("themeCollection", {}).get("baseTheme", {}).get("name", "Default")

    pages_html = []
    pages_dir = definition_path / "pages"
    if pages_dir.is_dir():
        page_order = _get_page_order(definition_path)
        page_dirs = sorted(
            [d for d in pages_dir.iterdir() if d.is_dir() and (d / "page.json").exists()],
            key=lambda d: page_order.index(d.name) if d.name in page_order else 9999,
        )
        for page_dir in page_dirs:
            pages_html.append(_render_page(page_dir))

    pages_content = (
        "\n".join(pages_html) if pages_html else "<p class='empty'>No pages in report</p>"
    )

    return _HTML_TEMPLATE.replace("{{THEME}}", escape(theme)).replace("{{PAGES}}", pages_content)


def render_page(definition_path: Path, page_name: str) -> str:
    """Render a single page as HTML."""
    page_dir = definition_path / "pages" / page_name
    if not page_dir.is_dir():
        return f"<p>Page '{escape(page_name)}' not found</p>"
    return _render_page(page_dir)


# ---------------------------------------------------------------------------
# Internal renderers
# ---------------------------------------------------------------------------

_VISUAL_COLORS: dict[str, str] = {
    # Original 9
    "barChart": "#4472C4",
    "lineChart": "#ED7D31",
    "card": "#A5A5A5",
    "tableEx": "#5B9BD5",
    "pivotTable": "#70AD47",
    "slicer": "#FFC000",
    "kpi": "#00B050",
    "gauge": "#7030A0",
    "donutChart": "#FF6B6B",
    # v3.1.0 additions
    "columnChart": "#4472C4",
    "areaChart": "#ED7D31",
    "ribbonChart": "#9DC3E6",
    "waterfallChart": "#548235",
    "scatterChart": "#FF0000",
    "funnelChart": "#0070C0",
    "multiRowCard": "#595959",
    "treemap": "#833C00",
    "cardNew": "#767171",
    "stackedBarChart": "#2E75B6",
    "lineStackedColumnComboChart": "#C55A11",
    # v3.4.0 additions
    "cardVisual": "#767171",
    "actionButton": "#E8832A",
    # v3.5.0 additions
    "clusteredColumnChart": "#4472C4",
    "clusteredBarChart": "#4472C4",
    "textSlicer": "#FFC000",
    "listSlicer": "#FFC000",
    # v3.6.0 additions
    "image": "#9E480E",
    "shape": "#7F7F7F",
    "textbox": "#404040",
    "pageNavigator": "#00B0F0",
    "advancedSlicerVisual": "#FFC000",
    # v3.8.0 additions
    "azureMap": "#0078D4",
}

_VISUAL_ICONS: dict[str, str] = {
    # Original 9
    "barChart": "&#9612;&#9612;&#9612;",
    "lineChart": "&#10138;",
    "card": "&#9632;",
    "tableEx": "&#9638;",
    "pivotTable": "&#9641;",
    "slicer": "&#9776;",
    "kpi": "&#9650;",
    "gauge": "&#9201;",
    "donutChart": "&#9673;",
    # v3.1.0 additions
    "columnChart": "&#9616;&#9616;&#9616;",
    "areaChart": "&#9650;",
    "ribbonChart": "&#9654;",
    "waterfallChart": "&#8597;",
    "scatterChart": "&#8901;&#8901;&#8901;",
    "funnelChart": "&#9660;",
    "multiRowCard": "&#9636;&#9636;",
    "treemap": "&#9635;",
    "cardNew": "&#9633;",
    "stackedBarChart": "&#9612;&#9612;",
    "lineStackedColumnComboChart": "&#9616;&#10138;",
    # v3.4.0 additions
    "cardVisual": "&#9632;",
    "actionButton": "&#9654;",
    # v3.5.0 additions
    "clusteredColumnChart": "&#9616;&#9616;&#9616;",
    "clusteredBarChart": "&#9612;&#9612;&#9612;",
    "textSlicer": "&#9776;",
    "listSlicer": "&#9776;",
    # v3.6.0 additions
    "image": "&#9679;",
    "shape": "&#9650;",
    "textbox": "&#9723;",
    "pageNavigator": "&#9658;",
    "advancedSlicerVisual": "&#9776;",
    # v3.8.0 additions
    "azureMap": "&#9670;",
}


def _render_page(page_dir: Path) -> str:
    """Render a single page directory as HTML."""
    page_data = _read_json(page_dir / "page.json")
    display_name = page_data.get("displayName", page_dir.name)
    width = page_data.get("width", 1280)
    height = page_data.get("height", 720)
    name = page_data.get("name", page_dir.name)

    visuals_html = []
    visuals_dir = page_dir / "visuals"
    if visuals_dir.is_dir():
        for vdir in sorted(visuals_dir.iterdir()):
            if not vdir.is_dir():
                continue
            vfile = vdir / "visual.json"
            if vfile.exists():
                visuals_html.append(_render_visual(vfile))

    visuals_content = "\n".join(visuals_html)
    if not visuals_content:
        visuals_content = "<div class='empty-page'>Empty page</div>"

    # Scale factor for the preview (fit to ~900px wide container)
    scale = min(900 / width, 1.0)

    return f"""
    <div class="page" data-page="{escape(name)}">
      <h2 class="page-title">{escape(display_name)}</h2>
      <div class="page-canvas" style="width:{width}px;height:{height}px;transform:scale({scale:.3f});transform-origin:top left;">
        {visuals_content}
      </div>
    </div>
    """


def _render_visual(vfile: Path) -> str:
    """Render a single visual.json as an HTML element."""
    data = _read_json(vfile)
    pos = data.get("position", {})
    x = pos.get("x", 0)
    y = pos.get("y", 0)
    w = pos.get("width", 200)
    h = pos.get("height", 150)
    z = pos.get("z", 0)

    visual_config = data.get("visual", {})
    vtype = visual_config.get("visualType", "unknown")
    name = data.get("name", "")
    hidden = data.get("isHidden", False)

    color = _VISUAL_COLORS.get(vtype, "#888")
    icon = _VISUAL_ICONS.get(vtype, "?")

    # Extract bound fields
    bindings = _extract_bindings(visual_config)
    bindings_html = ""
    if bindings:
        items = "".join(f"<li>{escape(b)}</li>" for b in bindings)
        bindings_html = f"<ul class='bindings'>{items}</ul>"

    opacity = "0.4" if hidden else "1"

    return f"""
    <div class="visual" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{z};border-color:{color};opacity:{opacity};" data-visual="{escape(name)}" data-type="{escape(vtype)}">
      <div class="visual-header" style="background:{color};">
        <span class="visual-icon">{icon}</span>
        <span class="visual-type">{escape(vtype)}</span>
      </div>
      <div class="visual-body">
        {_render_visual_content(vtype, w, h, bindings)}
        {bindings_html}
      </div>
    </div>
    """


def _render_visual_content(vtype: str, w: float, h: float, bindings: list[str]) -> str:
    """Render simplified chart preview content."""
    body_h = h - 30  # header height

    if vtype == "barChart":
        bars = ""
        num_bars = min(len(bindings), 5) if bindings else 4
        bar_w = max(w / (num_bars * 2), 15)
        for i in range(num_bars):
            bar_h = body_h * (0.3 + 0.5 * ((i * 37 + 13) % 7) / 7)
            bars += (
                f'<rect x="{i * bar_w * 2 + bar_w / 2}" y="{body_h - bar_h}" '
                f'width="{bar_w}" height="{bar_h}" fill="#4472C4" opacity="0.7"/>'
            )
        return f'<svg class="chart-svg" viewBox="0 0 {w} {body_h}">{bars}</svg>'

    if vtype == "lineChart":
        points = []
        num_points = 6
        for i in range(num_points):
            px = (w / (num_points - 1)) * i
            py = body_h * (0.2 + 0.6 * ((i * 47 + 23) % 11) / 11)
            points.append(f"{px},{py}")
        polyline = (
            f'<polyline points="{" ".join(points)}" fill="none" stroke="#ED7D31" stroke-width="3"/>'
        )
        return f'<svg class="chart-svg" viewBox="0 0 {w} {body_h}">{polyline}</svg>'

    if vtype == "card":
        label = bindings[0] if bindings else "Measure"
        return f'<div class="card-value">123.4K</div><div class="card-label">{escape(label)}</div>'

    if vtype in ("tableEx", "pivotTable"):
        cols = bindings[:5] if bindings else ["Col 1", "Col 2", "Col 3"]
        header = "".join(f"<th>{escape(c)}</th>" for c in cols)
        rows = ""
        for r in range(3):
            cells = "".join("<td>...</td>" for _ in cols)
            rows += f"<tr>{cells}</tr>"
        return f'<table class="data-table"><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>'

    return f'<div class="unknown-visual">{escape(vtype)}</div>'


def _extract_bindings(visual_config: dict[str, Any]) -> list[str]:
    """Extract field binding names from visual configuration."""
    bindings: list[str] = []
    query_state = visual_config.get("query", {}).get("queryState", {})

    for role, state in query_state.items():
        for proj in state.get("projections", []):
            ref = proj.get("queryRef", "")
            if ref:
                bindings.append(ref)

    # Also check Commands-based bindings
    for cmd in visual_config.get("query", {}).get("Commands", []):
        sq = cmd.get("SemanticQueryDataShapeCommand", {}).get("Query", {})
        sources = {s["Name"]: s["Entity"] for s in sq.get("From", [])}
        for sel in sq.get("Select", []):
            name = sel.get("Name", "")
            if name:
                # Try to make it readable
                for kind in ("Column", "Measure"):
                    if kind in sel:
                        src = sel[kind].get("Expression", {}).get("SourceRef", {}).get("Source", "")
                        prop = sel[kind].get("Property", "")
                        table = sources.get(src, src)
                        bindings.append(f"{table}[{prop}]")
                        break

    return bindings


def _get_page_order(definition_path: Path) -> list[str]:
    """Read page order from pages.json."""
    pages_json = definition_path / "pages" / "pages.json"
    if not pages_json.exists():
        return []
    try:
        data = json.loads(pages_json.read_text(encoding="utf-8"))
        order: list[str] = data.get("pageOrder", [])
        return order
    except (json.JSONDecodeError, KeyError):
        return []


def _read_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vicente Antonio Juan Magallanes Report Preview</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #1e1e1e;
      color: #e0e0e0;
      padding: 20px;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 24px;
      padding-bottom: 12px;
      border-bottom: 1px solid #333;
    }
    .header h1 {
      font-size: 18px;
      font-weight: 600;
      color: #f2c811;
    }
    .header .badge {
      background: #333;
      color: #aaa;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
    .header .theme {
      margin-left: auto;
      font-size: 13px;
      color: #888;
    }
    .page {
      margin-bottom: 40px;
    }
    .page-title {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #ccc;
      padding-left: 4px;
    }
    .page-canvas {
      position: relative;
      background: #2d2d2d;
      border: 1px solid #444;
      border-radius: 4px;
      overflow: hidden;
    }
    .visual {
      position: absolute;
      border: 2px solid;
      border-radius: 4px;
      background: #252525;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .visual-header {
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 600;
      color: white;
      display: flex;
      align-items: center;
      gap: 6px;
      min-height: 24px;
    }
    .visual-icon { font-size: 14px; }
    .visual-type { text-transform: capitalize; }
    .visual-body {
      flex: 1;
      padding: 6px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .chart-svg { width: 100%; height: 100%; }
    .card-value {
      font-size: 28px;
      font-weight: 700;
      text-align: center;
      color: #f2c811;
      padding: 10px 0 4px;
    }
    .card-label {
      font-size: 11px;
      text-align: center;
      color: #888;
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    .data-table th {
      background: #333;
      padding: 4px 6px;
      text-align: left;
      border-bottom: 1px solid #555;
      color: #ccc;
    }
    .data-table td {
      padding: 3px 6px;
      border-bottom: 1px solid #333;
      color: #999;
    }
    .bindings {
      list-style: none;
      margin-top: 4px;
      font-size: 10px;
      color: #777;
    }
    .bindings li::before {
      content: "\\2192 ";
      color: #555;
    }
    .empty { color: #666; text-align: center; padding: 40px; }
    .empty-page {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #555;
      font-size: 14px;
    }
    .unknown-visual {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #666;
      font-style: italic;
    }
    .ws-status {
      position: fixed;
      bottom: 12px;
      right: 12px;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      background: #333;
    }
    .ws-status.connected { color: #4caf50; }
    .ws-status.disconnected { color: #f44336; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Vicente Antonio Juan Magallanes Report Preview</h1>
    <span class="badge">STRUCTURAL</span>
    <span class="theme">Theme: {{THEME}}</span>
  </div>
  {{PAGES}}
  <div class="ws-status disconnected" id="ws-status">disconnected</div>
  <script>
    (function() {
      var wsUrl = 'ws://' + location.hostname + ':' + (parseInt(location.port) + 1);
      var status = document.getElementById('ws-status');
      function connect() {
        var ws = new WebSocket(wsUrl);
        ws.onopen = function() {
          status.textContent = 'live';
          status.className = 'ws-status connected';
        };
        ws.onmessage = function(e) {
          if (e.data === 'reload') location.reload();
        };
        ws.onclose = function() {
          status.textContent = 'disconnected';
          status.className = 'ws-status disconnected';
          setTimeout(connect, 2000);
        };
      }
      connect();
    })();
  </script>
</body>
</html>"""
