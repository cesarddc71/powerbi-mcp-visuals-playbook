param(
    [string]$ReportPath = "Informe_Charlas_Microsoft.Report",
    [string]$SemanticModelPath = "Informe_Charlas_Microsoft.SemanticModel"
)

$ErrorActionPreference = "Stop"

function Add-Issue {
    param(
        [string]$Severity,
        [string]$File,
        [string]$Message
    )

    [pscustomobject]@{
        Severity = $Severity
        File     = $File
        Message  = $Message
    }
}

function Visit-JsonNode {
    param(
        [object]$Node,
        [scriptblock]$Visitor
    )

    if ($null -eq $Node) {
        return
    }

    & $Visitor $Node

    if ($Node -is [System.Array]) {
        foreach ($item in $Node) {
            Visit-JsonNode -Node $item -Visitor $Visitor
        }
        return
    }

    if ($Node -is [pscustomobject]) {
        foreach ($prop in $Node.PSObject.Properties) {
            Visit-JsonNode -Node $prop.Value -Visitor $Visitor
        }
    }
}

$repoRoot = (Get-Location).Path
$reportFullPath = Join-Path $repoRoot $ReportPath
$semanticFullPath = Join-Path $repoRoot $SemanticModelPath

if (-not (Test-Path -LiteralPath $reportFullPath)) {
    throw "Report path not found: $reportFullPath"
}

if (-not (Test-Path -LiteralPath $semanticFullPath)) {
    throw "Semantic model path not found: $semanticFullPath"
}

$columns = @{}
$measures = @{}

$tableFiles = Get-ChildItem -LiteralPath (Join-Path $semanticFullPath "definition\tables") -Filter "*.tmdl"
foreach ($file in $tableFiles) {
    $tableName = $null
    foreach ($line in Get-Content -LiteralPath $file.FullName) {
        if ($line -match "^table\s+(.+)$") {
            $tableName = $Matches[1].Trim()
            continue
        }

        if ($null -eq $tableName) {
            continue
        }

        if ($line -match "^\s+column\s+(.+)$") {
            $columns["$tableName.$($Matches[1].Trim())"] = $true
            continue
        }

        if ($line -match "^\s+measure\s+(.+?)\s*=") {
            $measures["$tableName.$($Matches[1].Trim())"] = $true
        }
    }
}

$extensionPath = Join-Path $reportFullPath "definition\reportExtensions.json"
if (Test-Path -LiteralPath $extensionPath) {
    $extensionJson = Get-Content -LiteralPath $extensionPath -Raw | ConvertFrom-Json
    foreach ($entity in @($extensionJson.entities)) {
        foreach ($measure in @($entity.measures)) {
            $measures["$($entity.name).$($measure.name)"] = $true
        }
    }
}

$issues = @()
$visualFiles = Get-ChildItem -LiteralPath (Join-Path $reportFullPath "definition\pages") -Recurse -Filter "visual.json"

$customLikeVisualTypes = @(
    "cardNew",
    "listSlicer",
    "advancedSlicerVisual",
    "textSlicer"
)

foreach ($file in $visualFiles) {
    $relative = Resolve-Path -LiteralPath $file.FullName -Relative
    try {
        $json = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    }
    catch {
        $issues += Add-Issue -Severity "Error" -File $relative -Message "Invalid JSON: $($_.Exception.Message)"
        continue
    }

    $visualType = $json.visual.visualType
    if ($customLikeVisualTypes -contains $visualType) {
        $issues += Add-Issue -Severity "Warning" -File $relative -Message "Visual type '$visualType' may require an embedded custom visual. Prefer standard 'card' or 'slicer'."
    }

    $queryState = $json.visual.query.queryState
    if ($null -ne $queryState) {
        foreach ($role in $queryState.PSObject.Properties) {
            if ($role.Value.PSObject.Properties.Name -contains "active") {
                $issues += Add-Issue -Severity "Error" -File $relative -Message "Bucket-level 'active' found in queryState.$($role.Name). Move/remove it; Power BI Desktop rejects it."
            }
        }
    }

    if ($visualType -eq "donutChart" -and $null -ne $queryState -and -not ($queryState.PSObject.Properties.Name -contains "Values")) {
        $issues += Add-Issue -Severity "Warning" -File $relative -Message "donutChart should use role 'Values' for the measure."
    }

    if ($visualType -eq "gauge" -and $null -ne $queryState -and -not ($queryState.PSObject.Properties.Name -contains "Value")) {
        $issues += Add-Issue -Severity "Warning" -File $relative -Message "gauge should use role 'Value' for the measure."
    }

    if ($visualType -eq "azureMap" -and $null -ne $queryState -and -not ($queryState.PSObject.Properties.Name -contains "Location")) {
        $issues += Add-Issue -Severity "Warning" -File $relative -Message "azureMap should use role 'Location' for geography fields."
    }

    Visit-JsonNode -Node $json -Visitor {
        param($node)

        if ($node -isnot [pscustomobject]) {
            return
        }

        if ($node.PSObject.Properties.Name -contains "Column") {
            $column = $node.Column
            $entity = $column.Expression.SourceRef.Entity
            $property = $column.Property
            if ($entity -and $property) {
                $key = "$entity.$property"
                if (-not $columns.ContainsKey($key)) {
                    $issues += Add-Issue -Severity "Error" -File $relative -Message "Field '$key' is referenced as Column but was not found as a model column."
                }
            }
        }

        if ($node.PSObject.Properties.Name -contains "Measure") {
            $measure = $node.Measure
            $sourceRef = $measure.Expression.SourceRef
            $entity = $sourceRef.Entity
            $property = $measure.Property
            if ($entity -and $property) {
                $key = "$entity.$property"
                if (-not $measures.ContainsKey($key)) {
                    $issues += Add-Issue -Severity "Error" -File $relative -Message "Field '$key' is referenced as Measure but was not found as a model or extension measure."
                }
            }
        }
    }
}

if ($issues.Count -eq 0) {
    Write-Host "PBIR visual validation passed." -ForegroundColor Green
    exit 0
}

$issues | Sort-Object Severity, File, Message | Format-Table -AutoSize

if ($issues.Severity -contains "Error") {
    exit 1
}

exit 0
