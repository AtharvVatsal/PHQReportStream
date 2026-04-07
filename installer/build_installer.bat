@echo off
REM Build Script for HP Police ReportStream
REM Requires: Python, PyInstaller, Inno Setup

echo ============================================
echo HP Police ReportStream - Build Script
echo ============================================
echo.

REM Check if Inno Setup is installed
set "ISCC="
for /f "tokens=*" %%i in ('where iscc 2^>nul') do set "ISCC=%%i"

if not defined ISCC (
    echo ERROR: Inno Setup not found in PATH
    echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
    echo After installation, run this script again.
    pause
    exit /b 1
)

echo Found Inno Setup: %ISCC%
echo.

REM Build the installer
echo Building installer...
cd /d "%~dp0"

"%ISCC%" HPReportStream.iss

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo Build Complete!
echo ============================================
echo.
echo Output: installer\HPReportStream_Setup_v4.0.0.exe
echo.

pause