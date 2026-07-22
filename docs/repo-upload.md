# Subir este proyecto a un repo

## 1. Revisar estado local

```powershell
git status
git branch --show-current
git remote -v
```

## 2. Validar antes de subir

```powershell
.\scripts\Validate-PBIRVisuals.ps1
```

Opcional:

```powershell
$env:PYTHONIOENCODING='utf-8'
pbir validate 'Informe_Charlas_Microsoft.Report'
```

## 3. Preparar commit

```powershell
git add README.md docs scripts mcp-server .gitignore Informe_Charlas_Microsoft.pbip Informe_Charlas_Microsoft.Report Informe_Charlas_Microsoft.SemanticModel
git commit -m "Add Power BI MCP visuals playbook"
```

`mcp-server/` contiene el servidor MCP real. Sin esa carpeta el repo solo conserva la documentacion y el informe de ejemplo.

## 4. Crear repo remoto

Crear un repo vacio en GitHub, GitLab, Azure DevOps o similar.

No anadir README desde la web si ya existe localmente.

## 5. Conectar remoto

GitHub HTTPS:

```powershell
git remote add origin https://github.com/<usuario>/<repo>.git
```

GitHub SSH:

```powershell
git remote add origin git@github.com:<usuario>/<repo>.git
```

Si ya habia remoto:

```powershell
git remote set-url origin https://github.com/<usuario>/<repo>.git
```

## 6. Subir

```powershell
git push -u origin main
```

## 7. Confirmar

```powershell
git status
git remote -v
```
