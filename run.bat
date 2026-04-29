@echo off
if "%1"=="" (
    powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1" start
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1" %1
)
