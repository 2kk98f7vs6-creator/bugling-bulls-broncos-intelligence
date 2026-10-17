$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    Write-Host 'Creating a separate Python environment for the Broncos fan beta...'
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python is not available. Install Python 3.12 and retry.' }
}
$python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path '.\.venv\broncos_requirements_ready.txt')) {
    Write-Host 'Installing Python dependencies...'
    & $python -m pip install -r .\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Set-Content -Path '.\.venv\broncos_requirements_ready.txt' -Value 'v0.2' -Encoding UTF8
}
if (-not (Test-Path '.\data\broncos_plays.csv')) {
    Write-Host 'First run: downloading REAL Broncos play-by-play and available charting...'
    & $python .\data_pipeline.py --seasons 2024 2025 2026
    if ($LASTEXITCODE -ne 0) { throw 'Data import failed. Nothing was fabricated. Check internet connection and retry.' }
}
Write-Host 'Opening http://localhost:8504 (leave this terminal open).'
& $python -m streamlit run .\app.py --server.port 8504 --server.address localhost
