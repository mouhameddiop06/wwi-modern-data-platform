# Lance l'interface Dagster (http://localhost:3000) avec le planificateur
#   .\dagster.ps1
$root = $PSScriptRoot
$env:DAGSTER_HOME = Join-Path $root ".dagster_home"
New-Item -ItemType Directory -Force $env:DAGSTER_HOME | Out-Null
if (-not (Test-Path (Join-Path $env:DAGSTER_HOME "dagster.yaml"))) {
    New-Item -ItemType File (Join-Path $env:DAGSTER_HOME "dagster.yaml") | Out-Null
}
Set-Location $root
& (Join-Path $root ".venv\Scripts\dagster.exe") dev -m orchestration.definitions -d $root @args
