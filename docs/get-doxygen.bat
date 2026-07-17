@ECHO OFF

setlocal

pushd "%~dp0"
if errorlevel 1 exit /b 1

set "DOXYGEN_VERSION=1.17.0"
set "DOXYGEN_SHA256=94594407c4cbca3049d76aacbb05d4a6f7d0f4e93c0de410b825d25ca5621c83"
set "DOXYGEN_URL=https://www.doxygen.nl/files/doxygen-%DOXYGEN_VERSION%.windows.x64.bin.zip"
set "DOXYGEN_DIR=%CD%\_tools\doxygen-%DOXYGEN_VERSION%"
set "DOXYGEN_ARCHIVE=%CD%\_tools\doxygen-%DOXYGEN_VERSION%.zip"
set "DOXYGEN_EXE=%DOXYGEN_DIR%\doxygen.exe"

if not exist "%DOXYGEN_EXE%" goto download
"%DOXYGEN_EXE%" --version >NUL 2>NUL
if not errorlevel 1 (
	echo Doxygen %DOXYGEN_VERSION% is already available at:
	echo   %DOXYGEN_EXE%
	goto success
)

:download
if not exist "_tools" mkdir "_tools"
if errorlevel 1 goto error

echo Downloading Doxygen %DOXYGEN_VERSION% from the official Doxygen site...
powershell.exe -NoLogo -NoProfile -NonInteractive -Command ^
    "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:DOXYGEN_URL -OutFile $env:DOXYGEN_ARCHIVE"
if errorlevel 1 goto error

echo Verifying SHA-256 checksum...
powershell.exe -NoLogo -NoProfile -NonInteractive -Command ^
    "if ((Get-FileHash -Algorithm SHA256 -LiteralPath $env:DOXYGEN_ARCHIVE).Hash -ne $env:DOXYGEN_SHA256) { Write-Error 'Doxygen archive checksum mismatch.'; exit 1 }"
if errorlevel 1 goto error

echo Extracting Doxygen to docs\_tools...
if exist "%DOXYGEN_DIR%" rmdir /S /Q "%DOXYGEN_DIR%"
if errorlevel 1 goto error
powershell.exe -NoLogo -NoProfile -NonInteractive -Command ^
    "Expand-Archive -LiteralPath $env:DOXYGEN_ARCHIVE -DestinationPath $env:DOXYGEN_DIR -Force"
if errorlevel 1 goto error

del /Q "%DOXYGEN_ARCHIVE%"
if not exist "%DOXYGEN_EXE%" (
	echo Expected executable was not found after extraction:
	echo   %DOXYGEN_EXE%
	goto error
)
"%DOXYGEN_EXE%" --version >NUL 2>NUL
if errorlevel 1 goto error

echo Doxygen %DOXYGEN_VERSION% is ready. Run:
echo   make.bat html

:success
popd
exit /b 0

:error
set "_OVRTX_EXIT_CODE=%ERRORLEVEL%"
if "%_OVRTX_EXIT_CODE%" == "0" set "_OVRTX_EXIT_CODE=1"
if exist "%DOXYGEN_ARCHIVE%" del /Q "%DOXYGEN_ARCHIVE%"
echo Failed to install the project-local Doxygen copy.
popd
exit /b %_OVRTX_EXIT_CODE%
