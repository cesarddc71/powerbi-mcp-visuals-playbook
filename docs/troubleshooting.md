# Troubleshooting PBIR + MCP Visuals

Errores reales encontrados durante la generacion de visuales y como evitarlos.

## Error: "Este campo se elimino del modelo"

Causa:

- Un visual apunta a un campo como `Measure`, pero el modelo lo define como `column`.
- Ejemplo incorrecto:

```json
"Measure": {
  "Expression": {
    "SourceRef": { "Entity": "DimProducto" }
  },
  "Property": "Producto"
}
```

Solucion:

```json
"Column": {
  "Expression": {
    "SourceRef": { "Entity": "DimProducto" }
  },
  "Property": "Producto"
}
```

Regla:

- Dimensiones (`DimProducto`, `DimPais`, `DimFecha`, etc.) suelen ir como `Column`.
- Medidas DAX van como `Measure`.

## Error: propiedad `active` adicional en `queryState.Values`

Causa:

Power BI Desktop no permite:

```json
"Values": {
  "projections": [],
  "active": true
}
```

Solucion:

Quitar `active` del bucket. Si existe, debe estar dentro de una proyeccion concreta, no como hermano de `projections`.

## Error: visual personalizado no agregado al informe

Mensaje tipico:

```text
Para ver este objeto visual personalizado, primero debe agregarlo a este informe: cardNew
```

Causa:

El tipo visual no esta embebido en el informe como custom visual.

Solucion:

Usar tipos estandar:

- `card` en lugar de `cardNew`
- `slicer` en lugar de `listSlicer`, `advancedSlicerVisual` o `textSlicer`

## Warnings de roles que no renderizan

Algunos visuales usan nombres de bucket distintos de los alias del MCP.

Correcciones usadas:

| Visual | Bucket incorrecto | Bucket correcto |
| --- | --- | --- |
| `donutChart` | `Y` | `Values` |
| `gauge` | `Y` | `Value` |
| `azureMap` | `Category` | `Location` |

## Errores de `$schema` con `pbir validate`

`pbir 0.9.6` puede esperar schemas distintos a los que genera Power BI Desktop actual.

Si Power BI Desktop abre el informe y el script local pasa, esos errores pueden ser de version del CLI, no del visual.

Validaciones recomendadas:

```powershell
.\scripts\Validate-PBIRVisuals.ps1
```

```powershell
$env:PYTHONIOENCODING='utf-8'
pbir validate 'Informe_Charlas_Microsoft.Report'
```

## Reglas preventivas

- Inspeccionar el modelo antes de enlazar campos.
- Usar `Tabla[Campo]` en bindings MCP.
- Validar despues de cada lote de cambios.
- Cerrar Power BI Desktop antes de editar PBIR.
- Reabrir el `.pbip` despues de editar; no guardar una sesion abierta con errores.

