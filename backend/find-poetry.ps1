# Script to find where Poetry is installed

Write-Host "Searching for Poetry installation..." -ForegroundColor Yellow

# Common locations
$possiblePaths = @(
    "$env:APPDATA\Python\Python313\Scripts\poetry.exe",
    "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\Scripts\poetry.exe",
    "$env:USERPROFILE\.local\bin\poetry.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        Write-Host "✅ Found Poetry at: $path" -ForegroundColor Green
        Write-Host "`nTo use it, run:" -ForegroundColor Yellow
        Write-Host "  & `"$path`" --version" -ForegroundColor Cyan
        Write-Host "`nTo install dependencies:" -ForegroundColor Yellow
        Write-Host "  & `"$path`" install" -ForegroundColor Cyan
        exit 0
    }
}

# Try searching in user directories
Write-Host "Searching in user directories..." -ForegroundColor Yellow
$searchPaths = @(
    "$env:APPDATA",
    "$env:LOCALAPPDATA",
    "$env:USERPROFILE"
)

foreach ($basePath in $searchPaths) {
    if (Test-Path $basePath) {
        $found = Get-ChildItem -Path $basePath -Filter "poetry.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            Write-Host "✅ Found Poetry at: $($found.FullName)" -ForegroundColor Green
            Write-Host "`nTo use it, run:" -ForegroundColor Yellow
            Write-Host "  & `"$($found.FullName)`" --version" -ForegroundColor Cyan
            Write-Host "`nTo install dependencies:" -ForegroundColor Yellow
            Write-Host "  & `"$($found.FullName)`" install" -ForegroundColor Cyan
            exit 0
        }
    }
}

Write-Host "❌ Poetry not found in common locations." -ForegroundColor Red
Write-Host "Please install Poetry first:" -ForegroundColor Yellow
Write-Host "  pip install poetry" -ForegroundColor Cyan
exit 1

