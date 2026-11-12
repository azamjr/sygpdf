@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>&1
if errorlevel 1 (
    echo Install Docker Desktop first. See README.md.
    goto failed
)
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
) else if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" (
    start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
) else (
    echo Open Docker Desktop, then try again.
    goto failed
)
for /l %%i in (1,1,60) do (
    docker info >nul 2>&1
    if not errorlevel 1 goto docker_ready
    timeout /t 2 /nobreak >nul
)
echo Docker did not become ready. Open Docker Desktop and retry.
goto failed

:docker_ready
docker compose version >nul 2>&1
if errorlevel 1 (
    echo Update Docker Desktop to include Docker Compose.
    goto failed
)
echo Starting sygpdf. The first build can take several minutes.
docker compose up --build -d
if errorlevel 1 goto failed
for /l %%i in (1,1,30) do (
    docker compose exec -T sygpdf python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=2)" >nul 2>&1
    if not errorlevel 1 goto ready
    timeout /t 2 /nobreak >nul
)
docker compose logs --tail=50 sygpdf
echo The app did not become ready. Review the logs above.
goto failed

:ready
start "" "http://127.0.0.1:8765"
echo sygpdf is running locally. Stop it with docker compose stop.
pause
exit /b 0

:failed
echo Startup failed. See the output above and README.md.
pause
exit /b 1
