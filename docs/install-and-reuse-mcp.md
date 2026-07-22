# Instalar y reutilizar el MCP de Power BI Visuals

Este documento explica que necesitas para usar el flujo de trabajo con `mcp__powerbi_visuals` en otro equipo o repo.

## Que contiene este repo

Este repo contiene un proyecto PBIP/PBIR, documentacion, ejemplos de uso y scripts de validacion.

No contiene el servidor MCP en si. El MCP `mcp__powerbi_visuals` es una herramienta externa que debe estar disponible en tu entorno de Codex o en el entorno donde ejecutes el agente.

## Requisitos locales

Instala o verifica:

- Power BI Desktop.
- Git.
- Python 3.10 o superior.
- `pbir` CLI opcional, recomendado.
- Acceso a Codex con el MCP `mcp__powerbi_visuals` habilitado.

Comprobar Git:

```powershell
git --version
```

Comprobar Python:

```powershell
python --version
```

Instalar `pbir`:

```powershell
python -m pip install pbir-cli
pbir --version
```

## Verificar si el MCP esta disponible

En una sesion de Codex, pide:

```text
Tienes disponible el MCP mcp__powerbi_visuals? Lista sus herramientas.
```

O pide una accion segura:

```text
Usa mcp__powerbi_visuals para listar las paginas del reporte PBIR local.
```

Si esta disponible, deberias ver herramientas como:

- `list_pages`
- `describe_page`
- `create_page`
- `create_visual`
- `bind_visual`
- `set_visual_container`
- `validate_report_structure`

## Si el MCP no aparece

El repo no puede instalar automaticamente un MCP que pertenece al entorno del agente. Necesitas habilitarlo en Codex o en tu host MCP.

Checklist:

1. Confirma que el entorno soporta MCP.
2. Instala o registra el servidor MCP de Power BI Visuals segun las instrucciones de tu organizacion.
3. Reinicia Codex o la sesion del agente.
4. Verifica que aparezca el namespace:

```text
mcp__powerbi_visuals
```

Ejemplo generico de configuracion MCP, solo como referencia:

```toml
[mcp_servers.powerbi_visuals]
command = "<ruta-o-comando-del-servidor-mcp>"
args = ["--transport", "stdio"]
```

No subas archivos de configuracion personal con tokens, rutas privadas o credenciales.

## Instalar este playbook en otro equipo

Clonar repo:

```powershell
git clone https://github.com/<usuario>/<repo>.git
cd <repo>
```

Validar los visuales:

```powershell
.\scripts\Validate-PBIRVisuals.ps1
```

Abrir el informe:

```powershell
Invoke-Item ".\Informe_Charlas_Microsoft.pbip"
```

## Flujo de reutilizacion

1. Clona el repo.
2. Abre el `.pbip` en Power BI Desktop.
3. Guarda una copia si vas a experimentar.
4. Cierra Power BI Desktop antes de modificar PBIR con MCP.
5. Usa Codex con `mcp__powerbi_visuals`.
6. Valida con `.\scripts\Validate-PBIRVisuals.ps1`.
7. Reabre el `.pbip`.

## Buenas practicas

- Usa medidas explicitas para valores numericos.
- Usa columnas de dimensiones solo como categorias, filas, columnas o segmentadores.
- Evita visuales no estandar si no estan embebidos en el informe.
- Valida despues de cada lote de cambios.
- No guardes desde Desktop una sesion abierta con errores generados por PBIR externo.

