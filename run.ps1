param([string]$Action = "start")

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$PidFile   = Join-Path $ScriptDir ".app.pid"
$LogFile   = Join-Path $ScriptDir "app.log"

function Check-Venv {
    if (-not (Test-Path $PythonExe)) {
        Write-Host "Error: .venv not found. Run:"
        Write-Host "  python -m venv .venv"
        Write-Host "  .venv\Scripts\pip install -r requirements.txt"
        exit 1
    }
}

function Start-App {
    if (Test-Path $PidFile) {
        $existingPid = [int](Get-Content $PidFile -Raw).Trim()
        if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
            Write-Host "Already running (PID: $existingPid)"
            exit 1
        }
        Remove-Item $PidFile
    }
    Check-Venv
    $proc = Start-Process -FilePath $PythonExe `
        -ArgumentList "-m", "my_writing" `
        -WorkingDirectory $ScriptDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$LogFile.stdout" `
        -RedirectStandardError $LogFile `
        -PassThru
    $proc.Id | Out-File -FilePath $PidFile -Encoding ascii -NoNewline
    Write-Host "Started (PID: $($proc.Id), log: app.log)"
}

function Stop-App {
    if (-not (Test-Path $PidFile)) {
        Write-Host "Not running (no PID file)"
        exit 1
    }
    $savedPid = [int](Get-Content $PidFile -Raw).Trim()
    Stop-Process -Id $savedPid -Force -ErrorAction SilentlyContinue
    Remove-Item $PidFile
    Write-Host "Stopped (PID: $savedPid)"
}

function Restart-App {
    if (Test-Path $PidFile) {
        $savedPid = [int](Get-Content $PidFile -Raw).Trim()
        Stop-Process -Id $savedPid -Force -ErrorAction SilentlyContinue
        Remove-Item $PidFile
        Start-Sleep -Seconds 1
    }
    Start-App
}

function Get-AppStatus {
    if (Test-Path $PidFile) {
        $savedPid = [int](Get-Content $PidFile -Raw).Trim()
        if (Get-Process -Id $savedPid -ErrorAction SilentlyContinue) {
            Write-Host "Running (PID: $savedPid)"
        } else {
            Remove-Item $PidFile
            Write-Host "Not running (removed stale PID file)"
        }
    } else {
        Write-Host "Not running"
    }
}

switch ($Action.ToLower()) {
    "start"   { Start-App }
    "stop"    { Stop-App }
    "restart" { Restart-App }
    "status"  { Get-AppStatus }
    default   { Write-Host "Usage: .\run.ps1 {start|stop|restart|status}"; exit 1 }
}
