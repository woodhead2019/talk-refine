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

    # Remove autostart
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    Remove-ItemProperty -Path $regPath -Name "TalkRefine" -ErrorAction SilentlyContinue
    Write-Host "  [OK] Autostart removed" -ForegroundColor Green

    # Remove start menu shortcut
    $shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\TalkRefine.lnk"
    if (Test-Path $shortcut) { Remove-Item $shortcut }
    Write-Host "  [OK] Start Menu shortcut removed" -ForegroundColor Green

    Write-Host ""
    Write-Host "To fully remove, also run:" -ForegroundColor Yellow
    Write-Host "  pip uninstall talkrefine funasr modelscope torch torchaudio -y"
    Write-Host "  Remove-Item -Recurse ~\.cache\modelscope"
    Write-Host "  winget uninstall Ollama.Ollama  # if no longer needed"
    Write-Host "  winget uninstall Gyan.FFmpeg    # if no longer needed"
    exit 0
}

# Step 1: Check Python
Write-Host "[1/6] Checking Python..." -ForegroundColor Cyan
try {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# Step 2: Check/install ffmpeg
Write-Host "[2/6] Checking ffmpeg..." -ForegroundColor Cyan
$ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegPath) {
    Write-Host "  [OK] ffmpeg found" -ForegroundColor Green
} else {
    Write-Host "  Installing ffmpeg..." -ForegroundColor Yellow
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "  [OK] ffmpeg installed" -ForegroundColor Green
}

# Step 3: Check/install Ollama
Write-Host "[3/6] Checking Ollama..." -ForegroundColor Cyan
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Host "  [OK] Ollama found" -ForegroundColor Green
} else {
    Write-Host "  Installing Ollama..." -ForegroundColor Yellow
    winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "  [OK] Ollama installed" -ForegroundColor Green
}

# Step 4: Pull LLM model
Write-Host "[4/6] Pulling LLM model (qwen3.5:2b)..." -ForegroundColor Cyan
$models = ollama list 2>&1
if ($models -match "qwen3.5:2b") {
    Write-Host "  [OK] Model already downloaded" -ForegroundColor Green
} else {
    Write-Host "  Downloading (~2GB)..." -ForegroundColor Yellow
    ollama pull qwen3.5:2b
    Write-Host "  [OK] Model ready" -ForegroundColor Green
}

# Step 5: Install Python dependencies
Write-Host "[5/6] Installing Python packages..." -ForegroundColor Cyan
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet 2>&1 | Out-Null
pip install funasr modelscope pyaudio pyperclip pyautogui keyboard requests pystray Pillow pyyaml pywin32 --quiet 2>&1 | Out-Null
Write-Host "  [OK] Dependencies installed" -ForegroundColor Green

# Step 6: Setup autostart & shortcut
Write-Host "[6/6] Setting up shortcuts..." -ForegroundColor Cyan
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Push-Location $projectDir
python -m talkrefine --install 2>&1
Pop-Location
Write-Host "  [OK] Setup complete" -ForegroundColor Green

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Start: Search 'TalkRefine' in Start Menu"
Write-Host "  Or run: python -m talkrefine"
Write-Host "  Hotkey: Press F7 to record (configurable in config.yaml)"
Write-Host ""
