# Power BI Visuals MCP

Autor: Vicente Antonio Juan Magallanes.

This project includes a local MCP server that exposes advanced PBIR report and
visualization features over MCP.

The server is focused on the report/visual layer:

- report creation and validation
- pages
- visuals and bulk visual operations
- visual calculations
- container, chart, and series styling
- filters
- conditional formatting
- themes
- bookmarks
- embedded custom visuals (`.pbiviz`)
- HTML preview rendering
- optional Desktop sync

It does **not** use the .NET semantic-model connection layer.

## Install

For local development from this folder:

```bash
pip install -e .
```

If you also want preview HTML rendering dependencies and Desktop sync helpers:

```bash
pip install -e ".[preview,reload]"
```

## Run Directly

The server runs over `stdio` by default:

```bash
mcp-visuales-avanzado
```

Equivalent:

```bash
python -m mcp_visuales_avanzado.server
```

## Test with MCP Inspector

Using the official MCP dev tool:

```bash
mcp dev src/mcp_visuales_avanzado/server.py --with-editable .
```

This opens the MCP Inspector against the server using the editable local repo.

## Install into an MCP Host

### Option 1: generic `command` config

Use this when your MCP host accepts stdio command configs:

```json
{
  "mcpServers": {
    "pbi-visuals": {
      "command": "python",
      "args": ["-m", "mcp_visuales_avanzado.server"],
      "cwd": "C:\\ruta\\al\\powerbi-mcp-visuals-playbook\\mcp-server"
    }
  }
}
```

If the package is already installed in the active environment, you can simplify
it to:

```json
{
  "mcpServers": {
    "pbi-visuals": {
      "command": "mcp-visuales-avanzado"
    }
  }
}
```

### Option 2: install with the official MCP CLI

The official Python MCP SDK documents both `mcp dev` and `mcp install` for
local server workflows:

```bash
mcp install src/mcp_visuales_avanzado/server.py --name "Power BI Visuals MCP"
```

## First-use Workflow

After connecting the server in your MCP host, the practical first steps are:

1. Set the active report context.
2. Inspect supported visuals and the current report.
3. Create pages and visuals.
4. Bind fields, add filters, and format visuals.
5. Optionally sync the report back into Power BI Desktop.

Typical flow:

```text
set_project_context(path="C:\\Work\\Sales.pbip")
describe_report()
create_page(display_name="Overview", name="overview")
create_visual(page_name="overview", visual_type="bar", name="sales_by_region")
bind_visual(
  page_name="overview",
  visual_name="sales_by_region",
  bindings=[
    {"role": "category", "field": "Geo[Region]", "field_type": "Column"},
    {"role": "value", "field": "Sales[Amount]", "field_type": "Measure"}
  ]
)
apply_report_palette(
  name="Executive Warm",
  data_colors=["#1D9E75", "#BA7517", "#E24B4A"],
  background="#F5F4F0",
  foreground="#2C2C2A",
  visual_background="#FFFFFF",
  border_color="#D3D1C7"
)
set_visual_container(
  page_name="overview",
  visual_name="sales_by_region",
  border_show=true,
  border_color="#D3D1C7",
  border_radius=18,
  background_show=true,
  background_color="#FFFFFF",
  title="Sales by region",
  subtitle="Top contributors",
  drop_shadow=true
)
set_report_theme(theme_path="C:\\Work\\brand-theme.json")
validate_report_structure(full=True)
sync_desktop_project()
```

## Main Tools

### Context and report

- `get_project_context`
- `set_project_context`
- `create_report_project`
- `convert_report_project`
- `describe_report`
- `validate_report_structure`
- `render_report_preview_html`
- `render_page_preview_html`
- `sync_desktop_project`

### Visual catalog

- `list_supported_visuals`
- `describe_visual_type`
- `get_visual_template`

### Pages

- `list_pages`
- `describe_page`
- `create_page`
- `delete_page`
- `set_page_background`
- `set_page_visibility`

### Visuals

- `list_visuals`
- `describe_visual`
- `get_visual_container_style`
- `create_visual`
- `update_visual_layout`
- `delete_visual`
- `bind_visual`
- `query_visuals`
- `bulk_bind_visuals`
- `bulk_update_visuals`
- `bulk_delete_visuals`
- `set_visual_container`
- `set_visual_chart_style`
- `set_visual_series_style`
- `add_visual_calculation`
- `list_visual_calculations`
- `delete_visual_calculation`

### Filters

- `list_filters`
- `add_categorical_filter`
- `add_topn_filter`
- `add_relative_date_filter`
- `remove_filter`
- `clear_filters`

### Formatting

- `get_visual_formatting`
- `clear_visual_formatting`
- `apply_gradient_background`
- `apply_conditional_background`
- `apply_measure_background`

### Themes

- `set_report_theme`
- `apply_report_palette`
- `get_report_theme`
- `diff_report_theme`

### Bookmarks

- `list_bookmarks`
- `get_bookmark`
- `create_bookmark`
- `delete_bookmark`
- `set_bookmark_visual_visibility`

### Custom visuals

- `import_custom_visual`
- `list_custom_visuals`
- `remove_custom_visual`
- `bump_custom_visual_patch_version`

## Read-only Resources

The server also exposes MCP resources for quick inspection:

- `pbivis://context`
- `pbivis://supported-visuals`
- `pbivis://templates/{visual_type}.json`
- `pbivis://report/summary`
- `pbivis://pages/{page_name}`
- `pbivis://pages/{page_name}/visuals`
- `pbivis://visuals/{page_name}/{visual_name}`
- `pbivis://preview/report.html`
- `pbivis://preview/pages/{page_name}.html`

## Notes

- In MCP usage, `set_project_context(...)` is the recommended first step.
- The server stores the active report context in-process, so later tool calls
  can omit `report_path`.
- `bind_visual` reads sibling TMDL metadata to resolve `Column` vs `Measure`.
  If the model is not available locally, pass `field_type` or `kind` in each
  binding.
- Rounded borders, padding, subtitle, and drop shadow are handled through
  `set_visual_container(...)`.
- `render_report_preview_html` and the preview resources adapt the repo's
  preview feature to MCP in a non-blocking way.
- `sync_desktop_project` requires the optional `reload` extra because it uses
  `pywin32`.
- Embedded custom visual management is included. Full TypeScript authoring of
  `.pbiviz` projects still lives above this layer as a workflow.
