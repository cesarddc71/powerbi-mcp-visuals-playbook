# AGENTS.md

## Alcance del repositorio

Este repositorio combina un proyecto Power BI en formato PBIP/PBIR con un servidor MCP Python para crear y modificar visuales. Mantén separadas estas superficies:

- `Informe_Charlas_Microsoft.Report/`: definicion PBIR del informe, principalmente JSON bajo `definition/`.
- `Informe_Charlas_Microsoft.SemanticModel/`: modelo semantico TMDL; las tablas y medidas estan bajo `definition/tables/`.
- `mcp-server/src/mcp_visuales_avanzado/`: paquete Python del servidor MCP.
- `scripts/Validate-PBIRVisuals.ps1`: validacion local del informe de ejemplo.
- `docs/`: procedimientos y casos conocidos; enlaza esta documentacion en vez de duplicarla.

Consulta primero [README.md](README.md), [mcp-server/README.md](mcp-server/README.md) y [docs/visuals-mcp.md](mcp-server/docs/visuals-mcp.md) para el flujo completo.

## Reglas de trabajo

- Antes de editar PBIR, cierra Power BI Desktop. Despues de validar, reabre el `.pbip` y comprueba el resultado en Desktop.
- Inspecciona el TMDL antes de crear bindings. Usa `Column` para dimensiones y `Measure` para medidas DAX; no adivines nombres ni tipos.
- Usa bindings con formato `Tabla[Campo]` en las llamadas MCP. Si el modelo no esta disponible junto al reporte, especifica `field_type` de forma explicita.
- Conserva los roles PBIR que espera cada visual: `Values` para `donutChart`, `Value` para `gauge` y `Location` para `azureMap`.
- No dejes `active` como propiedad hermana de `projections` dentro de `queryState.<Role>`; Power BI Desktop rechaza esa forma.
- Prefiere visuales estandar (`card`, `slicer`) sobre `cardNew`, `listSlicer`, `advancedSlicerVisual` o `textSlicer` salvo que el custom visual este embebido en el informe.
- Para cambios masivos, valida despues de cada lote pequeno y conserva el estilo de los JSON/TMDL existentes. Evita reformatear archivos no relacionados.
- No incluyas credenciales, tokens, rutas privadas de configuracion MCP ni artefactos generados en commits.

## Desarrollo del servidor MCP

Desde `mcp-server/`:

```powershell
python -m pip install -e .
python -m mcp_visuales_avanzado.server
```

Extras opcionales:

```powershell
python -m pip install -e ".[preview,reload]"
```

El servidor usa `stdio` y la capa de servicio coordina los backends en `src/mcp_visuales_avanzado/core/`. Los backends PBIR son la frontera para cambios de reportes, paginas, visuales, filtros y estilos; `service.py` expone la API estructurada y `server.py` la registra en MCP. Mantén esa separacion al agregar operaciones.

## Validacion requerida

Desde la raiz del repositorio, ejecuta despues de cambios en PBIR, TMDL o bindings:

```powershell
.\scripts\Validate-PBIRVisuals.ps1
```

Para cambios Python, al menos comprueba que el paquete compila:

```powershell
python -m compileall mcp-server\src
```

Si esta instalado, la validacion adicional es:

```powershell
$env:PYTHONIOENCODING='utf-8'
pbir validate 'Informe_Charlas_Microsoft.Report'
```

No hay una suite de tests automatizados en el repositorio; no inventes un comando de tests. El workflow de GitHub ejecuta el validador PowerShell en `windows-latest`.

Ante errores de apertura o schemas, revisa [docs/troubleshooting.md](docs/troubleshooting.md) antes de cambiar el formato generado. Para reutilizar el flujo con otro informe, consulta [docs/reuse-with-another-report.md](docs/reuse-with-another-report.md).
