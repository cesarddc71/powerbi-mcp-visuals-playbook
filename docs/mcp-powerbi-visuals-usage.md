# Guia de uso del MCP `mcp__powerbi_visuals`

Esta guia resume el flujo usado para crear paginas y visuales en el informe local.

## 1. Conectar al informe

Ruta del reporte:

```text
.\Informe_Charlas_Microsoft.Report
```

Primero se inspecciona la pagina activa:

```json
{
  "report_path": ".\\Informe_Charlas_Microsoft.Report",
  "page_name": "ff007454f20d7d987e88"
}
```

Herramientas utiles:

- `list_pages`
- `describe_page`
- `list_visuals`
- `describe_visual`
- `list_supported_visuals`

## 2. Inspeccionar el modelo

Antes de hacer bindings, revisar las tablas TMDL:

```powershell
rg "^\s*(table|column|measure)\s+" "Informe_Charlas_Microsoft.SemanticModel\definition\tables"
```

En este informe, la medida fiable usada para los graficos es:

```DAX
Medida = SUM(Fact_Ventas[Precio_por_Unidad])
```

Campo como referencia MCP:

```text
Fact_Ventas[Medida]
```

Dimensiones usadas:

```text
DimProducto[Producto]
DimPais[Pais]
DimComprador[Comprador]
DimTipoDescuento[Tipo_de_Descuento]
DimFecha[Mes]
DimFecha[Trimestre]
```

## 3. Crear pagina

Ejemplo:

```json
{
  "report_path": ".\\Informe_Charlas_Microsoft.Report",
  "name": "graficos_medida_1",
  "display_name": "Graficos Medida 1",
  "width": 1280,
  "height": 720
}
```

Herramienta:

```text
mcp__powerbi_visuals.create_page
```

## 4. Crear visual

Ejemplo de grafico de linea:

```json
{
  "report_path": ".\\Informe_Charlas_Microsoft.Report",
  "page_name": "graficos_medida_1",
  "visual_type": "lineChart",
  "name": "gm1_linea_mes",
  "x": 30,
  "y": 30,
  "width": 393,
  "height": 310
}
```

Herramienta:

```text
mcp__powerbi_visuals.create_visual
```

## 5. Enlazar campos

Ejemplo correcto:

```json
{
  "report_path": ".\\Informe_Charlas_Microsoft.Report",
  "page_name": "graficos_medida_1",
  "visual_name": "gm1_linea_mes",
  "bindings": [
    { "role": "Category", "field": "DimFecha[Mes]", "field_type": "Column" },
    { "role": "Y", "field": "Fact_Ventas[Medida]", "field_type": "Measure" }
  ]
}
```

Herramienta:

```text
mcp__powerbi_visuals.bind_visual
```

Regla clave:

- Campos `Dim...` normalmente son columnas.
- `Fact_Ventas[Medida]` es medida.
- No usar columnas de texto como si fueran medidas.

## 6. Estilizar visual

Ejemplo:

```json
{
  "report_path": ".\\Informe_Charlas_Microsoft.Report",
  "page_name": "graficos_medida_1",
  "visual_name": "gm1_linea_mes",
  "title": "Medida por mes",
  "title_font_size": 12,
  "title_alignment": "left",
  "subtitle_show": false,
  "background_show": true,
  "background_color": "#FFFFFF",
  "background_transparency": 0,
  "border_show": true,
  "border_color": "#E5E7EB",
  "border_radius": 4
}
```

Herramienta:

```text
mcp__powerbi_visuals.set_visual_container
```

## 7. Validar

Validacion del MCP:

```text
mcp__powerbi_visuals.validate_report_structure
```

Validacion local recomendada:

```powershell
.\scripts\Validate-PBIRVisuals.ps1
```

Validacion adicional con CLI:

```powershell
$env:PYTHONIOENCODING='utf-8'
pbir validate 'Informe_Charlas_Microsoft.Report'
```

## 8. Abrir en Desktop

Cerrar Power BI Desktop antes de editar PBIR. Despues de validar, abrir:

```text
Informe_Charlas_Microsoft.pbip
```
