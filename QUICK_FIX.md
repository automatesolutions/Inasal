# Quick Fix: Install Backend Dependencies

## Poetry is installed - use this command:

**Important:** You need the `&` operator before the path!

```powershell
cd backend
& "$env:APPDATA\Python\Python313\Scripts\poetry.exe" install
```

**OR use the direct full path:**

```powershell
& "C:\Users\jonel\AppData\Roaming\Python\Python313\Scripts\poetry.exe" install
```

**Or use the helper script:**

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File install-poetry.ps1
```

## Or find Poetry automatically:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File find-poetry.ps1
```

This will show you the exact path to Poetry and the command to use.

## After installing dependencies:

```powershell
# Test that it works
& "C:\Users\jonel\AppData\Roaming\Python\Python313\Scripts\poetry.exe" run pytest --version

# Run tests
pnpm --filter backend test
```

