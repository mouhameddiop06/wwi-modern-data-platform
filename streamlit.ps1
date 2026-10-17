# Lance l'application Streamlit (http://localhost:8501)
#   .\streamlit.ps1
#   .\streamlit.ps1 --server.port 8502   (si le port 8501 est déjà pris)
$root = $PSScriptRoot
Push-Location (Join-Path $root "app")
try {
    & (Join-Path $root ".venv\Scripts\streamlit.exe") run streamlit_app.py --server.port 8501 --browser.gatherUsageStats false @args
}
finally {
    Pop-Location  # revient au dossier de départ, même après Ctrl+C
}
