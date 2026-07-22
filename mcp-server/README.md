# MCP Visuales Avanzado

Autor: Vicente Antonio Juan Magallanes.

Servidor MCP autónomo para crear y editar visualizaciones Power BI sobre
proyectos PBIR (`.pbip` / `.Report`) sin depender de la capa .NET del modelo
semántico.

Incluye:

- creación y validación de reportes PBIR
- páginas
- visuales y operaciones masivas
- bindings de campos
- estilizado de contenedores, ejes y series
- paletas y temas generados desde MCP
- filtros
- formato condicional
- bookmarks
- temas
- custom visuals `.pbiviz`
- preview HTML
- sync opcional con Power BI Desktop

## Instalación

```bash
cd C:\ruta\al\powerbi-mcp-visuals-playbook\mcp-server
pip install -e .
```

Con extras:

```bash
pip install -e ".[preview,reload]"
```

## Arranque

```bash
mcp-visuales-avanzado
```

Equivalente:

```bash
python -m mcp_visuales_avanzado.server
```

## Configuración MCP

```json
{
  "mcpServers": {
    "pbi-visuales": {
      "command": "python",
      "args": ["-m", "mcp_visuales_avanzado.server"],
      "cwd": "C:\\ruta\\al\\powerbi-mcp-visuals-playbook\\mcp-server"
    }
  }
}
```

## Flujo de uso

1. Conectar el servidor MCP en tu host.
2. Ejecutar `set_project_context(path="C:\\ruta\\a\\MiReporte.pbip")`.
3. Crear páginas y visuales.
4. Bindear campos, aplicar filtros y formato.
5. Validar con `validate_report_structure`.
6. Si quieres, sincronizar con Desktop con `sync_desktop_project`.

Cuando hagas `bind_visual`, el servidor intenta leer el modelo TMDL del proyecto
para distinguir columnas de medidas. Si el modelo no está junto al informe,
puedes forzar el tipo con `field_type="Column"` o `field_type="Measure"`.

## Diseño y estilo

El MCP ya puede aplicar estilo más rico sin tocar JSON a mano:

- `apply_report_palette(...)` para generar una paleta/tema desde el prompt
- `set_visual_container(...)` para radio, borde, fondo, subtítulo, padding y sombra
- `set_visual_chart_style(...)` para leyenda, ejes, labels y grosor de línea
- `set_visual_series_style(...)` para color y estilo por serie

Ejemplo rápido:

```text
apply_report_palette(
  name="Executive Sage",
  data_colors=["#1D9E75", "#BA7517", "#E24B4A"],
  background="#F5F4F0",
  foreground="#2C2C2A",
  visual_background="#FFFFFF",
  border_color="#D3D1C7"
)

set_visual_container(
  page_name="overview",
  visual_name="sales_trend",
  border_show=true,
  border_color="#D3D1C7",
  border_radius=18,
  background_show=true,
  background_color="#FFFFFF",
  title="Evolución del gasto",
  subtitle="Vista mensual",
  drop_shadow=true
)
```

La guía detallada está en [docs/visuals-mcp.md](docs/visuals-mcp.md).
