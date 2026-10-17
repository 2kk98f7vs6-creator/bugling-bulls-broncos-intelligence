$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Run START_BRONCOS.ps1 at least once first to install the app.'
}
Write-Host 'Refreshing the publicly shareable Broncos snapshot (not private notes)...'
& $python .\data_pipeline.py --seasons 2024 2025 2026
if ($LASTEXITCODE -ne 0) { throw 'Refresh failed; previous published data should still be available.' }
Write-Host 'Done. Refresh the website or Streamlit browser tab.'
