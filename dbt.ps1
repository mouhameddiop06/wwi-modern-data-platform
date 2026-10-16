# Lance dbt avec les variables du fichier .env
#   .\dbt.ps1 build
#   .\dbt.ps1 docs generate
$root = $PSScriptRoot
Get-Content (Join-Path $root ".env") | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim('"'), 'Process')
    }
}
$project = Join-Path $root "transform\wwi_dbt"
& (Join-Path $root ".venv\Scripts\dbt.exe") @args --project-dir $project --profiles-dir $project
exit $LASTEXITCODE
