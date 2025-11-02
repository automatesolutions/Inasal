# PowerShell script to add Poetry to PATH and install dependencies

Write-Host "Adding Poetry to PATH..." -ForegroundColor Yellow
$poetryPath = "$env:APPDATA\Roaming\Python\Python313\Scripts"

# Check if Poetry exists
if (Test-Path "$poetryPath\poetry.exe") {
    Write-Host "Poetry found at: $poetryPath" -ForegroundColor Green
    $env:Path += ";$poetryPath"
    
    Write-Host "`nVerifying Poetry installation..." -ForegroundColor Yellow
    & "$poetryPath\poetry.exe" --version
    
    Write-Host "`nInstalling backend dependencies..." -ForegroundColor Yellow
    & "$poetryPath\poetry.exe" install
    
    Write-Host "`n✅ Done! Poetry is now available in this session." -ForegroundColor Green
    Write-Host "Note: You'll need to run this script each time you open a new terminal," -ForegroundColor Yellow
    Write-Host "or add Poetry to your PATH permanently (see INSTALL_POETRY.md)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Poetry not found at: $poetryPath" -ForegroundColor Red
    Write-Host "Please install Poetry first:" -ForegroundColor Yellow
    Write-Host "  pip install poetry" -ForegroundColor Cyan
    exit 1
}

