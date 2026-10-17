# Compile le rapport en PDF (trois passes pour la table des matières et les références)
#   .\rapport\build.ps1
$bin = Join-Path $env:LOCALAPPDATA "Programs\MiKTeX\miktex\bin\x64"
$pdflatex = if (Test-Path "$bin\pdflatex.exe") { "$bin\pdflatex.exe" } else { "pdflatex" }
Push-Location $PSScriptRoot
try {
    1..3 | ForEach-Object { & $pdflatex -interaction=nonstopmode -halt-on-error rapport.tex | Out-Null }
    if ($LASTEXITCODE -ne 0) { Write-Error "Échec de compilation : voir rapport.log"; exit 1 }
    Select-String -Path rapport.log -Pattern "Output written" | ForEach-Object { $_.Line }
}
finally {
    Pop-Location
}
