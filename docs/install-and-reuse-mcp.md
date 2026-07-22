# Instalar y reutilizar el MCP de Power BI Visuals

Este repo ahora incluye el servidor MCP real en `mcp-server/`. Eso permite que otra persona clone el repo, instale el paquete Python local y registre el MCP en su host de Codex.

## Que contiene este repo

- `mcp-server/`: codigo fuente del servidor MCP `mcp_visuales_avanzado`.
- `Informe_Charlas_Microsoft.Report`: ejemplo PBIR con visuales creados/ajustados.
- `Informe_Charlas_Microsoft.SemanticModel`: modelo TMDL usado por el ejemplo.
- `docs/`: guias de uso, troubleshooting y prompts.
- `scripts/Validate-PBIRVisuals.ps1`: validacion local de PBIR.

## Requisitos locales

Instala o verifica:

- Power BI Desktop.
- Git.
- Python 3.10 o superior.
- Acceso a Codex o a otro host que soporte MCP por `stdio`.
- `pbir` CLI opcional, recomendado para validar.

Comprobar Git y Python:

```powershell
git --version
python --version
```

Instalar `pbir` si quieres validacion adicional:

```powershell
python -m pip install pbir-cli
pbir --version
```

## Clonar e instalar el MCP

```powershell
git clone https://github.com/vicente2121/powerbi-mcp-visuals-playbook.git
cd powerbi-mcp-visuals-playbook
python -m pip install -e .\mcp-server
```

Con extras para preview HTML y sincronizacion opcional con Desktop:

```powershell
python -m pip install -e ".\mcp-server[preview,reload]"
```

## Registrar el MCP en Codex

En la configuracion local de Codex, anade un servidor MCP como este. Cambia `cwd` por la ruta real donde clonaste el repo:

```toml
[mcp_servers.powerbi_visuals]
command = "python"
args = ["-m", "mcp_visuales_avanzado.server"]
cwd = 'C:\ruta\al\powerbi-mcp-visuals-playbook\mcp-server'
enabled = true
startup_timeout_sec = 20.0
tool_timeout_sec = 120.0
```

Despues reinicia Codex. El namespace esperado es:

```text
mcp__powerbi_visuals
```

No subas archivos de configuracion personal con tokens, rutas privadas o credenciales.

## Verificar que funciona

En una sesion de Codex, pide:

```text
Tienes disponible el MCP mcp__powerbi_visuals? Lista sus herramientas.
```

O prueba una accion segura:

```text
Usa mcp__powerbi_visuals para listar las paginas del reporte PBIR local.
```

Herramientas esperadas:

- `set_project_context`
- `list_pages`
- `describe_page`
- `create_page`
- `create_visual`
- `bind_visual`
- `set_visual_container`
- `validate_report_structure`

## Usarlo con cualquier informe PBIP/PBIR

1. Clona este repo e instala `mcp-server/`.
2. Abre tu informe `.pbip` en Power BI Desktop y guardalo.
3. Cierra Power BI Desktop antes de editar PBIR desde el MCP.
4. En Codex, establece contexto:

```text
set_project_context(path="C:\ruta\a\MiInforme.pbip")
```

5. Crea paginas, visuales, filtros y estilos con `mcp__powerbi_visuals`.
6. Valida:

```text
validate_report_structure(full=true)
```

7. Reabre el `.pbip` en Power BI Desktop.

## Bindings seguros

El MCP incluido intenta detectar si un campo es `Column` o `Measure` leyendo el modelo TMDL local. Si el modelo no esta junto al informe, fuerza el tipo en el binding:

```text
bind_visual(
  page_name="overview",
  visual_name="ventas_por_pais",
  bindings=[
    {"role": "category", "field": "DimPais[Pais]", "field_type": "Column"},
    {"role": "value", "field": "Fact_Ventas[Medida]", "field_type": "Measure"}
  ]
)
```

Buenas practicas:

- Usa columnas de dimensiones solo como categorias, filas, columnas o segmentadores.
- Usa medidas explicitas para valores numericos.
- Evita visuales no estandar si no estan embebidos en el informe.
- Valida despues de cada lote de cambios.
- No guardes desde Desktop una sesion abierta con errores generados por PBIR externo.
