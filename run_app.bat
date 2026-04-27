@echo off
setlocal

cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    set "PYTHONW_EXE=%~dp0.venv\Scripts\pythonw.exe"

    "%PYTHON_EXE%" -c "import PySide6" >nul 2>nul
    if errorlevel 1 goto missing_pyside

    if exist "%PYTHONW_EXE%" (
        start "" "%PYTHONW_EXE%" -m app.bootstrap.entrypoint
    ) else (
        start "" "%PYTHON_EXE%" -m app.bootstrap.entrypoint
    )
    exit /b 0
)

where python >nul 2>nul
if errorlevel 1 goto missing_python

python -c "import PySide6" >nul 2>nul
if errorlevel 1 goto missing_pyside

where pythonw >nul 2>nul
if errorlevel 1 (
    start "" python -m app.bootstrap.entrypoint
) else (
    start "" pythonw -m app.bootstrap.entrypoint
)
exit /b 0

:missing_python
echo Python was not found. Install Python 3.13+ or create a .venv in this project.
pause
exit /b 1

:missing_pyside
echo PySide6 is not installed.
echo.
echo Install it with one of these commands:
echo   python -m pip install PySide6
echo or, if you use a virtual environment:
echo   .venv\Scripts\python -m pip install PySide6
echo.
pause
exit /b 1
