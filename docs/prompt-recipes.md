# Recetas de prompts para Codex + `mcp__powerbi_visuals`

Prompts listos para reutilizar con este repo u otro informe PBIP/PBIR.

## Comprobar conexion

```text
Usa mcp__powerbi_visuals para conectarte al reporte:
C:\ruta\MiInforme.Report
Lista las paginas y describe la pagina activa.
No modifiques nada.
```

## Inspeccionar modelo

```text
Antes de crear visuales, inspecciona el modelo semantico TMDL.
Lista tablas, columnas y medidas relevantes.
Identifica que campos son Column y cuales Measure.
```

## Crear pagina de dashboard

```text
Usa mcp__powerbi_visuals para crear una pagina nueva de 1280x720.
Usa una medida explicita para valores.
Usa columnas de dimensiones para categorias y slicers.
Crea 2 cards, 1 linea temporal, 1 barra por categoria, 1 matriz y 1 slicer.
Valida despues de cada lote de cambios.
```

## Crear muchos visuales sin romper Desktop

```text
Crea varias paginas nuevas con visuales estandar solamente.
Evita cardNew, listSlicer, advancedSlicerVisual y textSlicer si no estan embebidos.
Para donut usa Values, para gauge usa Value y para azureMap usa Location.
Al final ejecuta una revision para detectar:
- active a nivel de bucket
- columnas Dim como Measure
- visuales personalizados no embebidos
```

## Corregir columnas como medidas

```text
Revisa todos los visual.json del reporte PBIR.
Si una columna de DimProducto, DimPais, DimFecha, DimComprador o DimTipoDescuento aparece como Measure, cambiala a Column.
No cambies medidas reales de Fact_Ventas.
Valida el informe al final.
```

## Corregir `active` mal colocado

```text
Busca propiedades "active" directamente dentro de queryState.<Role>.
Si existen como hermanas de projections, eliminalas.
No elimines active dentro de una proyeccion individual.
Valida el informe al final.
```

## Validacion final

```text
Ejecuta .\scripts\Validate-PBIRVisuals.ps1.
Luego ejecuta validate_report_structure del MCP.
Dime si queda algun error y en que archivo.
```

## Subir repo

```text
Revisa git status.
Si el arbol esta limpio, dime los comandos exactos para crear remoto y subir a GitHub.
No subas credenciales ni configuracion local.
```

