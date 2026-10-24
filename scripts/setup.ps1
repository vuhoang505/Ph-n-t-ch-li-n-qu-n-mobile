$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\pip.exe")) {
    py -m venv --clear .venv
    if ($LASTEXITCODE -ne 0) { throw "Không thể tạo môi trường ảo Python." }
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Không thể nâng cấp pip trong .venv." }
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "Không thể cài dependency backend." }
Push-Location ".\frontend"
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Không thể cài dependency frontend." }
Pop-Location
Write-Host "Cài đặt hoàn tất. Chạy scripts/run-backend.ps1 và scripts/run-frontend.ps1 trong hai terminal."

