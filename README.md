# Power BI PBIR + MCP Visuals Playbook

Repositorio de trabajo para distribuir el MCP `mcp__powerbi_visuals` y documentar su uso con proyectos Power BI en formato PBIP/PBIR.

Este repo contiene:

- `Informe_Charlas_Microsoft.pbip`: proyecto Power BI.
- `Informe_Charlas_Microsoft.Report`: definicion PBIR del informe.
- `Informe_Charlas_Microsoft.SemanticModel`: modelo semantico TMDL.
- `mcp-server/`: codigo fuente instalable del servidor MCP `mcp_visuales_avanzado`.
- `docs/`: pasos de uso, decisiones y errores conocidos.
- `scripts/Validate-PBIRVisuals.ps1`: validacion local para evitar los bugs que aparecieron al generar visuales.
- `.github/workflows/validate-pbir.yml`: validacion automatica opcional al subir a GitHub.

## Requisitos

- Power BI Desktop con soporte PBIP/PBIR.
- Proyecto guardado como `.pbip`.
- Python 3.10 o superior.
- MCP instalado desde `mcp-server/` y disponible en Codex.
- `pbir` CLI opcional para validacion adicional.

Comprobar CLI:

```powershell
pbir --version
```

Instalar este MCP desde el repo:

```powershell
python -m pip install -e .\mcp-server
```

Configuracion MCP para Codex:

```toml
[mcp_servers.powerbi_visuals]
command = "python"
args = ["-m", "mcp_visuales_avanzado.server"]
cwd = 'C:\ruta\al\powerbi-mcp-visuals-playbook\mcp-server'
enabled = true
startup_timeout_sec = 20.0
tool_timeout_sec = 120.0
```

## Flujo recomendado

1. Guardar el informe en Power BI Desktop.
2. Cerrar Power BI Desktop antes de editar PBIR desde MCP.
3. Crear/modificar paginas y visuales con `mcp__powerbi_visuals`.
4. Validar con:

```powershell
.\scripts\Validate-PBIRVisuals.ps1
```

5. Opcionalmente validar tambien con:

```powershell
$env:PYTHONIOENCODING='utf-8'
pbir validate 'Informe_Charlas_Microsoft.Report'
```

6. Reabrir el `.pbip` en Power BI Desktop.

## Documentacion incluida

- [Instalar y reutilizar el MCP](docs/install-and-reuse-mcp.md)
- [Usar este repo con otro informe PBIP](docs/reuse-with-another-report.md)
- [Recetas de prompts para Codex + MCP](docs/prompt-recipes.md)
- [Guia de uso del MCP](docs/mcp-powerbi-visuals-usage.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Subir este proyecto a un repo](docs/repo-upload.md)

## Resubir cambios a GitHub

Este workspace ya tiene remoto. Para resubir cambios:

```powershell
git status
git add README.md docs scripts mcp-server .gitignore Informe_Charlas_Microsoft.pbip Informe_Charlas_Microsoft.Report Informe_Charlas_Microsoft.SemanticModel
git commit -m "Add Power BI visuals MCP server source"
git push origin main
```

Para cambiar el remoto en otro equipo:

```powershell
git remote set-url origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```

## Notas importantes

- No guardar desde Power BI Desktop una sesion abierta con errores despues de editar PBIR fuera de Desktop.
- En slicers, tablas y matrices, las dimensiones deben escribirse como `Column`, no como `Measure`.
- En cards, gauges y ejes numericos conviene usar medidas explicitas.
- Algunos tipos visuales que el MCP puede listar no estan disponibles en Desktop si no estan embebidos como custom visuals.
