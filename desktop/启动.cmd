@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PORT=8787"
set "URL=http://127.0.0.1:%PORT%/"

where node >nul 2>nul
if errorlevel 1 goto nonode

rem ---- 找浏览器：优先 Edge（Windows 自带），其次 Chrome ----
set "BROWSER="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"

rem ---- 已经在跑就不重复启动 ----
netstat -ano | findstr "LISTENING" | findstr ":%PORT%" >nul 2>nul
if not errorlevel 1 goto open

echo 正在启动本地服务…
start "vocab-extractor" /min node server.js
timeout /t 2 /nobreak >nul

:open
if defined BROWSER (
  start "" "%BROWSER%" "--app=%URL%"
) else (
  start "" "%URL%"
)
exit /b 0

:nonode
echo.
echo   [x] 未检测到 Node.js，无法启动本地服务。
echo.
echo   方案一：装好 Node.js 后重新双击本文件   https://nodejs.org/
echo   方案二：直接用在线版（无需安装）        http://154.8.220.104:8080/
echo.
pause
exit /b 1
