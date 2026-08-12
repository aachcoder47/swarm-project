# =============================================================
# FrontierX Scout — Windows PowerShell Environment Helper
# =============================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   FrontierX Labs — Windows Environment     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check Docker status
Write-Host "[1/3] Checking Docker Desktop status..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker daemon is running." -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Docker Desktop is not running or not accessible." -ForegroundColor Red
        Write-Host "     Please launch 'Docker Desktop' application on Windows first." -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ Docker executable not found in PATH." -ForegroundColor Red
}

# Check WSL status
Write-Host "[2/3] Checking WSL (Windows Subsystem for Linux)..." -ForegroundColor Yellow
try {
    $wslList = wsl -l -v 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ WSL is installed:" -ForegroundColor Green
        Write-Host $wslList
    } else {
        Write-Host "  ℹ️  WSL is not enabled. Run 'wsl --install' in Admin PowerShell to enable Ubuntu." -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ℹ️  WSL command not available." -ForegroundColor Yellow
}

# Check Dashboard
Write-Host "[3/3] Web Dashboard..." -ForegroundColor Yellow
$dashboardPath = Join-Path $PSScriptRoot "..\dashboard\index.html"
if (Test-Path $dashboardPath) {
    Write-Host "  ✅ Interactive Dashboard available at:" -ForegroundColor Green
    Write-Host "     file:///$($dashboardPath.Replace('\', '/'))" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Header
Write-Host "• To view the project dashboard now: Open 'dashboard/index.html' in your browser."
Write-Host "• To run the ROS 2 / Isaac Sim container stack on Windows:"
Write-Host "  1. Start Docker Desktop application."
Write-Host "  2. Run: docker compose -f docker/docker-compose.yml up"
Write-Host ""
