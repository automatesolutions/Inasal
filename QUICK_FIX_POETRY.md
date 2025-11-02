# Quick Fix: Poetry Not Recognized

Poetry is installed but not on your PATH. Here are quick solutions:

## Option 1: Add to PATH for Current Session (Quickest)

Run this in PowerShell:
```powershell
$env:Path += ";$env:APPDATA\Roaming\Python\Python313\Scripts"
```

Then verify it works:
```powershell
poetry --version
```

## Option 2: Use Full Path (No PATH Changes Needed)

Instead of `poetry`, use the full path:
```powershell
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" install
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" --version
```

Or for npm scripts, update `backend/package.json` to use full path (but Option 1 is easier).

## Option 3: Add to PATH Permanently

1. Open PowerShell as Administrator
2. Run:
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:APPDATA\Roaming\Python\Python313\Scripts", [EnvironmentVariableTarget]::User)
```

3. Restart your terminal

## After Fixing PATH

Then run:
```powershell
cd backend
poetry install
```

## Recommended: Quick Fix for Now

Just run this once in your current PowerShell session:
```powershell
$env:Path += ";$env:APPDATA\Roaming\Python\Python313\Scripts"
poetry --version  # Verify it works
cd backend
poetry install
```

