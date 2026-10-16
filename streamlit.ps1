# Lance l'application Streamlit (http://localhost:8501)
#   .\streamlit.ps1
$root = $PSScriptRoot
Set-Location (Join-Path $root "app")
& (Join-Path $root ".venv\Scripts\streamlit.exe") run streamlit_app.py --server.port 8501 --browser.gatherUsageStats false @args
