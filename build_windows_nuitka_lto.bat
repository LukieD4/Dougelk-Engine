@echo off
setlocal enabledelayedexpansion

REM ==================================================
REM PROJECT CONFIG
REM ==================================================
set PROJECT_NAME=Game
set ENTRY_POINT=py_client.py
set ICON_PATH=assets\sprites\program.ico
set SRCDIR=%~dp0
set DISTDIR=builds
set TARGET_EXE=%DISTDIR%\%PROJECT_NAME%.exe

@REM Warning: Changing this could cause the compiler to break.
@REM          make sure it matches your PROJECT_NAME.
set VERSION_FILE=%PROJECT_NAME%Build.version



REM --- METADATA (USER EDITABLE)
set COMPANY_NAME=NAME
set PRODUCT_NAME=%PROJECT_NAME%
set FILE_DESCRIPTION=Made with the Dougelk Game Engine (c) %YEAR% %COMPANY_NAME%

REM --- DYNAMIC COPYRIGHT YEAR
for /f %%i in ('powershell -command "Get-Date -Format yyyy"') do set YEAR=%%i
set COPYRIGHT=Copyright (c) %YEAR% %COMPANY_NAME%


























cd /d "%SRCDIR%"

if not exist "%DISTDIR%" mkdir "%DISTDIR%"

REM ==================================================
REM START TIMER
REM ==================================================
echo [%TIME%] Starting build...
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
set /a START_SEC=%%a*3600 + %%b*60 + %%c
)

REM ==================================================
REM LOCATE VSDEVCMD
REM ==================================================
set "VSDEVCMD="

if defined VSDEVCMD (
echo [INFO] Using VSDEVCMD from environment: %VSDEVCMD%
) else (
if exist "C:\PROGRA~2\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\vsdevcmd.bat" (
set "VSDEVCMD=C:\PROGRA~2\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\vsdevcmd.bat"
) else if exist "C:\PROGRA~2\Microsoft Visual Studio\2019\BuildTools\Common7\Tools\vsdevcmd.bat" (
set "VSDEVCMD=C:\PROGRA~2\Microsoft Visual Studio\2019\BuildTools\Common7\Tools\vsdevcmd.bat"
) else if exist "C:\PROGRA~2\Microsoft Visual Studio\18\BuildTools\Common7\Tools\vsdevcmd.bat" (
set "VSDEVCMD=C:\PROGRA~2\Microsoft Visual Studio\18\BuildTools\Common7\Tools\vsdevcmd.bat"
)

```
if not defined VSDEVCMD (
    if exist "C:\PROGRA~2\Microsoft Visual Studio\Installer\vswhere.exe" (
        for /f "usebackq tokens=*" %%I in (`
            "C:\PROGRA~2\Microsoft Visual Studio\Installer\vswhere.exe" ^
            -latest -products * ^
            -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
            -property installationPath
        `) do (
            if exist "%%I\Common7\Tools\vsdevcmd.bat" (
                set "VSDEVCMD=%%I\Common7\Tools\vsdevcmd.bat"
            )
        )
    )
)
```

)

REM ==================================================
REM INITIALISE VS ENVIRONMENT
REM ==================================================
if defined VSDEVCMD (
echo [INFO] Found vsdevcmd: %VSDEVCMD%
echo [INFO] Initializing Visual Studio build environment...

```
call "%VSDEVCMD%" -arch=x86 -host_arch=x86

if errorlevel 1 (
    echo [WARNING] vsdevcmd returned non-zero exit code
) else (
    echo [INFO] Visual Studio environment initialized.
)
```

) else (
echo [WARNING] Could not locate vsdevcmd.bat automatically.
)

REM ==================================================
REM PYTHON SELECTION
REM ==================================================
set VENV_PY=%SRCDIR%.venv\Scripts\python.exe
if not exist "%VENV_PY%" (
echo [WARNING] .venv not found — using system Python
set VENV_PY=python
) else (
echo [INFO] Using venv: %VENV_PY%
)

REM ==================================================
REM DEPENDENCY CHECK
REM ==================================================
echo [INFO] Checking dependencies...
"%VENV_PY%" -c "import nuitka, pygame, imageio" 2>nul
if errorlevel 1 (
echo [INFO] Installing missing dependencies...
"%VENV_PY%" -m pip install --quiet --upgrade pip
"%VENV_PY%" -m pip install --quiet nuitka pygame imageio
) else (
echo [INFO] All dependencies present
)

REM ==================================================
REM READ BUILD NUMBER
REM ==================================================
set BUILDVER=0
set VERSION_FILE=%PROJECT_NAME%Build.version

if exist "%VERSION_FILE%" (
set /p BUILDVER=<"%VERSION_FILE%"
) else (
echo [WARNING] %VERSION_FILE% not found — defaulting to 0
)

echo [INFO] Build version: %BUILDVER%

REM ==================================================
REM CLEAN OUTPUT
REM ==================================================
echo [INFO] Cleaning previous build...
if exist "%TARGET_EXE%" del /q "%TARGET_EXE%" 2>nul

REM ==================================================
REM BUILD WITH NUITKA
REM ==================================================
echo [INFO] Building %PROJECT_NAME%...

"%VENV_PY%" -m nuitka ^
--onefile ^
--onefile-tempdir-spec="{TEMP}/%PROJECT_NAME%" ^
--output-dir="%DISTDIR%" ^
--output-filename="%PROJECT_NAME%.exe" ^
--windows-icon-from-ico="%ICON_PATH%" ^
--windows-file-version=1.0.0.%BUILDVER% ^
--windows-product-version=1.0.0.%BUILDVER% ^
--windows-company-name="%COMPANY_NAME%" ^
--windows-product-name="%PRODUCT_NAME%" ^
--windows-file-description="%FILE_DESCRIPTION%" ^
--windows-console-mode=attach ^
--include-data-dir=assets=assets ^
--include-data-file="%VERSION_FILE%=%VERSION_FILE%" ^
--nofollow-import-to=tkinter,unittest,pytest,setuptools,IPython,dask,numpy,matplotlib,pandas,scipy,PIL.ImageQt ^
--lto=yes ^
--jobs=%NUMBER_OF_PROCESSORS% ^
--assume-yes-for-downloads ^
--remove-output ^
"%ENTRY_POINT%"

REM ==================================================
REM VERIFY BUILD
REM ==================================================
if not exist "%TARGET_EXE%" (
echo.
echo [ERROR] Build failed — executable not found at:
echo %TARGET_EXE%
pause
exit /b 1
)

REM ==================================================
REM TIMER END
REM ==================================================
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
set /a END_SEC=%%a*3600 + %%b*60 + %%c
)
set /a ELAPSED=%END_SEC%-%START_SEC%
if %ELAPSED% lss 0 set /a ELAPSED+=86400

REM ==================================================
REM SUMMARY
REM ==================================================
echo.
echo ==================================================
echo   BUILD SUCCESSFUL
echo ==================================================
echo   Output: %TARGET_EXE%
for %%F in ("%TARGET_EXE%") do echo   Size: %%~zF bytes
echo   Time: %ELAPSED% seconds
echo ==================================================
echo.
pause
