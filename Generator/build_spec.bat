@echo off
cd /d "%~dp0"

pyinstaller PoseScaleTomlGenerator.spec --clean

echo.

