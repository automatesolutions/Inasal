# Installing Poetry on Windows

Poetry is required for managing Python dependencies in the backend.

## Quick Install (Recommended)

### Option 1: Using pip (Easiest)
```powershell
pip install poetry
```

### Option 2: Official Installer (More Reliable)
```powershell
# Run in PowerShell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

After installation, you may need to add Poetry to your PATH:

**Quick fix (for current session):**
```powershell
# Add to PATH for this session
$env:Path += ";$env:APPDATA\Roaming\Python\Python313\Scripts"
```

**Or use full path:**
```powershell
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" install
```

**Permanent fix (add to PATH permanently):**
1. Open System Properties → Environment Variables
2. Under "User variables", find "Path" and click Edit
3. Click "New" and add: `C:\Users\jonel\AppData\Roaming\Python\Python313\Scripts`
4. Click OK and restart your terminal

### Option 3: Using pipx (If you have pipx)
```powershell
pipx install poetry
```

## Verify Installation

```powershell
poetry --version
```

Should output something like: `Poetry (version 1.x.x)`

## After Installation

1. **Navigate to backend directory:**
   ```powershell
   cd backend
   ```

2. **Install dependencies:**
   ```powershell
   poetry install
   ```

3. **Verify it works:**
   ```powershell
   poetry run pytest --version
   ```

## Troubleshooting

### "poetry is not recognized"
- Make sure Poetry is in your PATH
- Restart your terminal/PowerShell
- Try using full path: `$env:APPDATA\Python\Scripts\poetry.exe`

### "python is not recognized"
- Make sure Python 3.11+ is installed
- Add Python to PATH during installation
- Verify: `python --version`

## Alternative: Using Python venv (Without Poetry)

If you prefer not to use Poetry, you can use a standard virtual environment:

```powershell
# Create virtual environment
cd backend
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install dependencies manually (you'll need to install from pyproject.toml)
pip install fastapi uvicorn motor redis langchain langchain-openai faiss-cpu pydantic python-jose passlib
# ... etc (all dependencies from pyproject.toml)
```

However, Poetry is recommended as it manages dependencies more reliably.

