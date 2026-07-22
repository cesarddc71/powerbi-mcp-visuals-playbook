# Reutilizar este repo con otro informe PBIP

Este playbook se puede adaptar a otro informe Power BI guardado como PBIP/PBIR.

## 1. Preparar el nuevo informe

En Power BI Desktop:

1. Abre tu `.pbix`.
2. Guarda como proyecto Power BI `.pbip`.
3. Cierra Power BI Desktop.

Estructura esperada:

```text
MiInforme.pbip
MiInforme.Report/
MiInforme.SemanticModel/
```

## 2. Copiar scripts y docs

Desde este repo, puedes reutilizar:

```text
docs/
scripts/Validate-PBIRVisuals.ps1
.github/workflows/validate-pbir.yml
```

## 3. Ejecutar validacion con rutas nuevas

Si tu informe se llama distinto:

```powershell
.\scripts\Validate-PBIRVisuals.ps1 `
  -ReportPath "MiInforme.Report" `
  -SemanticModelPath "MiInforme.SemanticModel"
```

## 4. Inspeccionar modelo antes de crear visuales

```powershell
rg "^\s*(table|column|measure)\s+" "MiInforme.SemanticModel\definition\tables"
```

Identifica:

- Medidas disponibles.
- Columnas de fecha.
- Dimensiones de categoria.
- Campos geograficos.

## 5. Prompt base para Codex

```text
Usa mcp__powerbi_visuals sobre el reporte "MiInforme.Report".
Primero inspecciona paginas y modelo.
No adivines campos.
Usa columnas Dim como categorias/slicers y medidas explicitas en valores.
Crea una pagina nueva con graficos y valida despues.
```

## 6. Reglas de mapping

| Uso | Campo recomendado | Tipo PBIR |
| --- | --- | --- |
| Eje X / Categoria | Dimension o fecha | `Column` |
| Leyenda | Dimension | `Column` |
| Slicer | Dimension | `Column` |
| Tabla / matriz detalle | Dimension + medida | `Column` + `Measure` |
| Card / KPI / Gauge | Medida explicita | `Measure` |
| Eje Y / Values | Medida explicita | `Measure` |

## 7. Roles con cuidado

Algunos visuales tienen roles mas estrictos que los alias del MCP:

| Visual | Roles seguros |
| --- | --- |
| `lineChart` | `Category`, `Y` |
| `barChart` | `Category`, `Y` |
| `clusteredColumnChart` | `Category`, `Y`, `Legend` |
| `donutChart` | `Category`, `Values` |
| `gauge` | `Value`, `MaxValue` |
| `azureMap` | `Location`, `Size` |
| `slicer` | `Values` |
| `tableEx` | `Values` |
| `pivotTable` | `Rows`, `Columns`, `Values` |

## 8. Validar antes de abrir

```powershell
.\scripts\Validate-PBIRVisuals.ps1 `
  -ReportPath "MiInforme.Report" `
  -SemanticModelPath "MiInforme.SemanticModel"
```

Si pasa, abre:

```powershell
Invoke-Item ".\MiInforme.pbip"
```

