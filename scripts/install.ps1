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
$installASRModel  = Ask-YesNo "  [6] SenseVoice ASR model (~200MB, for speech recognition)"
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
    if ($pyFound) {
        $pyVer = python --version 2>&1
        Write-Host "  [OK] Already installed: $pyVer" -ForegroundColor Green
    } else {
        Write-Host "  Installing Python via winget..." -ForegroundColor Yellow
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  [OK] Python installed" -ForegroundColor Green
    }
} else {
    # Still need to verify Python exists
    $pyFound = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyFound) {
        Write-Host "[!] Python not found. Please install Python 3.10+ first." -ForegroundColor Red
        Write-Host "    Download: https://python.org  or run: winget install Python.Python.3.12" -ForegroundColor Yellow
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
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet --user 2>&1 | Out-Null
    pip install funasr modelscope pyperclip pyautogui keyboard requests pystray Pillow pyyaml --quiet --user 2>&1 | Out-Null
    
    # pyaudio needs special handling (may need prebuilt wheel on some Python versions)
    pip install pyaudio --quiet --user 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [WARN] pyaudio failed to install via pip. Trying pipwin..." -ForegroundColor Yellow
        pip install pipwin --quiet --user 2>&1 | Out-Null
        pipwin install pyaudio 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [FAIL] pyaudio installation failed. Please install manually:" -ForegroundColor Red
            Write-Host "         pip install pyaudio" -ForegroundColor Red
        }
    }

    # pywin32 optional
    pip install pywin32 --quiet --user 2>&1 | Out-Null

    # Verify critical packages
    $missing = @()
    foreach ($pkg in @("pyaudio", "funasr", "torch", "yaml", "keyboard", "pystray", "PIL")) {
        python -c "import $pkg" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $missing += $pkg }
    }
    if ($missing.Count -gt 0) {
        Write-Host "  [WARN] Missing packages: $($missing -join ', ')" -ForegroundColor Yellow
        Write-Host "         Retrying install..." -ForegroundColor Yellow
        pip install pyaudio funasr torch torchaudio pystray Pillow pyyaml keyboard pyperclip pyautogui requests modelscope --quiet --user 2>&1 | Out-Null
        # Re-check
        $still_missing = @()
        foreach ($pkg in $missing) {
            python -c "import $pkg" 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { $still_missing += $pkg }
        }
        if ($still_missing.Count -gt 0) {
            Write-Host "  [FAIL] Still missing: $($still_missing -join ', ')" -ForegroundColor Red
            Write-Host "         Please install manually before running TalkRefine" -ForegroundColor Red
        } else {
            Write-Host "  [OK] Dependencies installed and verified (after retry)" -ForegroundColor Green
        }
    } else {
        Write-Host "  [OK] Dependencies installed and verified" -ForegroundColor Green
    }
    $ErrorActionPreference = "Stop"
}

# ── ASR Model (SenseVoice) ──
if ($installASRModel) {
    $step++
    Write-Host "[$step/$total] Downloading ASR model (SenseVoice ~200MB)..." -ForegroundColor Cyan
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectDir = Split-Path -Parent $scriptDir
    Push-Location $projectDir
    $ErrorActionPreference = "Continue"
    python -c "
from funasr import AutoModel
model = AutoModel(model='iic/SenseVoiceSmall', trust_remote_code=True, device='cpu', disable_update=True)
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
Write-Host "  Or run: python -m talkrefine"
Write-Host "  Hotkey: Press F6 to record (configurable in settings)"
Write-Host ""
