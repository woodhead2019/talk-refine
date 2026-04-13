<# TalkRefine - One-click installer for Windows #>
param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "  TalkRefine Installer" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

if ($Uninstall) {
    Write-Host "Uninstalling TalkRefine..." -ForegroundColor Yellow

    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    Remove-ItemProperty -Path $regPath -Name "TalkRefine" -ErrorAction SilentlyContinue
    Write-Host "  [OK] Autostart removed" -ForegroundColor Green

    $shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\TalkRefine.lnk"
    if (Test-Path $shortcut) { Remove-Item $shortcut }
    Write-Host "  [OK] Start Menu shortcut removed" -ForegroundColor Green

    $startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\TalkRefine.lnk"
    if (Test-Path $startup) { Remove-Item $startup }
    Write-Host "  [OK] Startup shortcut removed" -ForegroundColor Green

    Write-Host ""
    Write-Host "To fully remove, also run:" -ForegroundColor Yellow
    Write-Host "  pip uninstall funasr modelscope torch torchaudio pyaudio -y"
    Write-Host "  Remove-Item -Recurse ~\.cache\modelscope"
    Write-Host "  winget uninstall Ollama.Ollama  # if no longer needed"
    Write-Host "  winget uninstall Gyan.FFmpeg    # if no longer needed"
    exit 0
}

# ── Check what to install ──

Write-Host "Select components to install:" -ForegroundColor Cyan
Write-Host ""

function Ask-YesNo($prompt, $default = "Y") {
    $answer = Read-Host "$prompt [Y/n]"
    if ([string]::IsNullOrWhiteSpace($answer)) { $answer = $default }
    return $answer.ToUpper() -eq "Y"
}

$installPythonRT  = Ask-YesNo "  [1] Python runtime (if not installed)"
$installFFmpeg    = Ask-YesNo "  [2] ffmpeg (audio processing)"
$installOllama    = Ask-YesNo "  [3] Ollama (local LLM runtime)"
$installLLMModel  = Ask-YesNo "  [4] Qwen3.5:2b model (~2GB, for text refinement)"
$installPython    = Ask-YesNo "  [5] Python packages (torch, funasr, etc.)"
$installASRModel  = Ask-YesNo "  [6] SenseVoice ASR model (~944MB, for speech recognition)"
$setupAutostart   = Ask-YesNo "  [7] Autostart + Start Menu shortcut"

Write-Host ""

$step = 0
$total = @($installPythonRT, $installFFmpeg, $installOllama, $installLLMModel, $installPython, $installASRModel, $setupAutostart) | Where-Object { $_ } | Measure-Object | Select-Object -ExpandProperty Count
if ($total -eq 0) {
    Write-Host "Nothing selected. Exiting." -ForegroundColor Yellow
    exit 0
}

# ── Python runtime ──
if ($installPythonRT) {
    $step++
    Write-Host "[$step/$total] Checking Python..." -ForegroundColor Cyan
    $pyFound = Get-Command python -ErrorAction SilentlyContinue
    $needInstall = $false
    if ($pyFound) {
        $pyVer = python --version 2>&1
        # Check version - need 3.10-3.12 (3.13+ has compatibility issues with many packages)
        $verMatch = [regex]::Match($pyVer, '(\d+)\.(\d+)')
        $major = [int]$verMatch.Groups[1].Value
        $minor = [int]$verMatch.Groups[2].Value
        if ($minor -ge 13) {
            Write-Host "  [WARN] $pyVer detected - Python 3.13+ has compatibility issues" -ForegroundColor Yellow
            Write-Host "         Many packages (torch, funasr, pystray) don't support 3.13 yet" -ForegroundColor Yellow
            Write-Host "  Installing Python 3.12 alongside..." -ForegroundColor Yellow
            $needInstall = $true
        } elseif ($minor -lt 10) {
            Write-Host "  [WARN] $pyVer is too old (need 3.10+)" -ForegroundColor Yellow
            $needInstall = $true
        } else {
            Write-Host "  [OK] $pyVer" -ForegroundColor Green
        }
    } else {
        $needInstall = $true
    }
    if ($needInstall) {
        Write-Host "  Installing Python 3.12 via winget..." -ForegroundColor Yellow
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        # After installing 3.12, try to use it specifically
        $py312 = Get-Command py -ErrorAction SilentlyContinue
        if ($py312) {
            Write-Host "  [OK] Python 3.12 installed. Use 'py -3.12' to run." -ForegroundColor Green
            Write-Host "  [INFO] Creating venv with Python 3.12..." -ForegroundColor Cyan
            $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
            $projectDir = Split-Path -Parent $scriptDir
            Push-Location $projectDir
            py -3.12 -m venv venv
            .\venv\Scripts\Activate.ps1
            Pop-Location
            Write-Host "  [OK] Virtual environment created and activated" -ForegroundColor Green
        } else {
            Write-Host "  [OK] Python 3.12 installed" -ForegroundColor Green
        }
    }
} else {
    # Still need to verify Python exists and version is compatible
    $pyFound = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyFound) {
        Write-Host "[!] Python not found. Please install Python 3.12:" -ForegroundColor Red
        Write-Host "    winget install Python.Python.3.12" -ForegroundColor Yellow
        exit 1
    }
    $pyVer = python --version 2>&1
    $verMatch = [regex]::Match($pyVer, '(\d+)\.(\d+)')
    $minor = [int]$verMatch.Groups[2].Value
    if ($minor -ge 13) {
        Write-Host "[!] $pyVer detected - Python 3.13+ is not supported yet." -ForegroundColor Red
        Write-Host "    Please install Python 3.12: winget install Python.Python.3.12" -ForegroundColor Yellow
        Write-Host "    Then create a venv: py -3.12 -m venv venv && .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
        exit 1
    }
}

# ── ffmpeg ──
if ($installFFmpeg) {
    $step++
    Write-Host "[$step/$total] Checking ffmpeg..." -ForegroundColor Cyan
    $ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpegPath) {
        Write-Host "  [OK] Already installed" -ForegroundColor Green
    } else {
        Write-Host "  Installing ffmpeg..." -ForegroundColor Yellow
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  [OK] ffmpeg installed" -ForegroundColor Green
    }
}

# ── Ollama ──
if ($installOllama) {
    $step++
    Write-Host "[$step/$total] Checking Ollama..." -ForegroundColor Cyan
    $ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaPath) {
        Write-Host "  [OK] Already installed" -ForegroundColor Green
    } else {
        Write-Host "  Installing Ollama (~1.8GB)..." -ForegroundColor Yellow
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  [OK] Ollama installed" -ForegroundColor Green
    }
}

# ── LLM Model ──
if ($installLLMModel) {
    $step++
    Write-Host "[$step/$total] Pulling LLM model (qwen3.5:2b)..." -ForegroundColor Cyan
    $ErrorActionPreference = "Continue"
    $models = ollama list 2>&1
    $ErrorActionPreference = "Stop"
    if ($models -match "qwen3.5:2b") {
        Write-Host "  [OK] Already downloaded" -ForegroundColor Green
    } else {
        Write-Host "  Downloading (~2GB, may take a few minutes)..." -ForegroundColor Yellow
        $ErrorActionPreference = "Continue"
        ollama pull qwen3.5:2b
        $ErrorActionPreference = "Stop"
        Write-Host "  [OK] Model ready" -ForegroundColor Green
    }
}

# ── Python packages ──
if ($installPython) {
    $step++
    Write-Host "[$step/$total] Installing Python packages..." -ForegroundColor Cyan
    $ErrorActionPreference = "Continue"

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectDir = Split-Path -Parent $scriptDir
    Push-Location $projectDir

    # Always use a virtual environment for isolation
    $venvPython = Join-Path $projectDir "venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
    }
    .\venv\Scripts\Activate.ps1
    Write-Host "  (virtual environment activated)" -ForegroundColor Gray

    # PyTorch CPU must be installed first (needs special index URL)
    Write-Host "  Installing PyTorch (CPU)..." -ForegroundColor Yellow
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet 2>&1 | Out-Null

    # Install talkrefine + all dependencies from pyproject.toml
    Write-Host "  Installing talkrefine and dependencies..." -ForegroundColor Yellow
    pip install -e ".[win32]" --quiet 2>&1 | Out-Null

    # Verify critical packages
    $missing = @()
    foreach ($pkg in @("pyaudio", "funasr", "torch", "yaml", "keyboard", "pystray", "PIL")) {
        python -c "import $pkg" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $missing += $pkg }
    }
    if ($missing.Count -gt 0) {
        Write-Host "  [FAIL] Missing packages: $($missing -join ', ')" -ForegroundColor Red
        Write-Host "         Try deleting the venv folder and re-running this installer" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  ========================================" -ForegroundColor Red
        Write-Host "  Installation FAILED - missing packages" -ForegroundColor Red
        Write-Host "  ========================================" -ForegroundColor Red
        Pop-Location
        exit 1
    } else {
        Write-Host "  [OK] All dependencies installed and verified" -ForegroundColor Green
    }

    Pop-Location
    $ErrorActionPreference = "Stop"
}

# ── ASR Model (SenseVoice) ──
if ($installASRModel) {
    $step++
    Write-Host "[$step/$total] Downloading ASR model (SenseVoice ~944MB)..." -ForegroundColor Cyan
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectDir = Split-Path -Parent $scriptDir
    Push-Location $projectDir
    $venvActivate = Join-Path $projectDir "venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) { & $venvActivate }
    $ErrorActionPreference = "Continue"
    python -c "
from funasr import AutoModel
model = AutoModel(model='FunAudioLLM/SenseVoiceSmall', trust_remote_code=True, device='cpu', disable_update=True, hub='hf')
print('Model downloaded successfully')
" 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"
    Pop-Location
    Write-Host "  [OK] ASR model ready" -ForegroundColor Green
}

# ── Autostart & shortcuts ──
if ($setupAutostart) {
    $step++
    Write-Host "[$step/$total] Setting up shortcuts..." -ForegroundColor Cyan
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectDir = Split-Path -Parent $scriptDir
    Push-Location $projectDir
    $venvActivate = Join-Path $projectDir "venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) { & $venvActivate }
    $ErrorActionPreference = "Continue"
    python -m talkrefine --install 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [WARN] Shortcut setup had errors. You can set up later via:" -ForegroundColor Yellow
        Write-Host "         python -m talkrefine --install" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] Setup complete" -ForegroundColor Green
    }
    $ErrorActionPreference = "Stop"
    Pop-Location
}

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Start: Search 'TalkRefine' in Start Menu"
Write-Host "  Or run: .\venv\Scripts\Activate.ps1; python -m talkrefine"
Write-Host "  Hotkey: Press F6 to record (configurable in settings)"
Write-Host ""
