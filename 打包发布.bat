@echo off
setlocal
REM Build a one-file exe from the project root.
REM Double-click keeps the window open after build.
REM Use this script with "/nopause" for automation.

set "SCRIPT_DIR=%~dp0"
set "ENTRY_FILE=自动筛选模组分类器.pyw"

set "NO_PAUSE="
if /I "%~1"=="/nopause" set "NO_PAUSE=1"

REM Check that Python 3 is available.
where python >nul 2>nul
if errorlevel 1 (
    echo Python 3 not found.
    if not defined NO_PAUSE pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%%ENTRY_FILE%" (
    echo Entry script not found.
    if not defined NO_PAUSE pause
    exit /b 1
)

REM Extract VERSION constant from .pyw via Python
for /f "delims=" %%V in ('python -c "import re,sys; f=open(sys.argv[1]); m=re.search(r'VERSION\s*=\s*[\"']([^\"']+)[\"']', f.read()); print(m.group(1) if m else 'unknown')" "%SCRIPT_DIR%%ENTRY_FILE%"') do set "VERSION=%%V"

if "%VERSION%"=="unknown" (
    echo Could not detect VERSION from %ENTRY_FILE%.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo Building version: %VERSION%

REM Find the first .ico file in the current directory.
set "ICON_FILE="
for %%I in ("%SCRIPT_DIR%*.ico") do if not defined ICON_FILE set "ICON_FILE=%%~nxI"

if not exist "%SCRIPT_DIR%%ICON_FILE%" (
    echo Icon file not found.
    if not defined NO_PAUSE pause
    exit /b 1
)

REM Run PyInstaller inside the project directory.
pushd "%SCRIPT_DIR%"
python -m PyInstaller --noconfirm --clean --noconsole --onefile --hidden-import=DrissionPage --exclude-module=cv2 --exclude-module=PIL --exclude-module=numpy --exclude-module=openpyxl --exclude-module=cloudscraper --exclude-module=curl_cffi --name "auto-mod-classifier-%VERSION%" --icon "%ICON_FILE%" "%ENTRY_FILE%"
set "BUILD_ERROR=%ERRORLEVEL%"
popd

if not "%BUILD_ERROR%"=="0" (
    echo Build failed.
    if not defined NO_PAUSE pause
    exit /b %BUILD_ERROR%
)

echo.
echo Build complete: dist\auto-mod-classifier-%VERSION%.exe
if not defined NO_PAUSE pause