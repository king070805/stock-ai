@echo off
REM A股自动刷新 - 管理脚本
REM 用法: double-click to start, or run from CMD

echo ========================================
echo   股小智 - A股数据自动刷新管理工具
echo ========================================
echo.

:menu
echo 请选择操作:
echo   [1] 启动自动刷新（新窗口运行）
echo   [2] 停止自动刷新
echo   [3] 查看运行状态
echo   [4] 查看日志
echo   [5] 注册开机自启
echo   [6] 退出
echo.

set /p choice="请输入数字 (1-6): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto status
if "%choice%"=="4" goto logs
if "%choice%"=="5" goto autostart
if "%choice%"=="6" goto end
goto menu

:start
echo [INFO] 启动自动刷新脚本...
start "A-Stock Auto Refresh" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0a_stock_auto_refresh.ps1"
echo [OK] 脚本已启动（新窗口）
goto end

:stop
echo [INFO] 停止自动刷新...
taskkill /FI "WINDOWTITLE eq A-Stock Auto Refresh" /T /F 2>nul
if %errorlevel%==0 (
    echo [OK] 已停止
) else (
    echo [INFO] 未找到运行中的脚本
)
goto end

:status
echo [INFO] 检查运行状态...
tasklist /FI "WINDOWTITLE eq A-Stock Auto Refresh" 2>nul | findstr /i "powershell" >nul
if %errorlevel%==0 (
    echo [OK] 自动刷新脚本正在运行
) else (
    echo [INFO] 自动刷新脚本未运行
)
goto end

:logs
echo [INFO] 日志文件位于: %~dp0logs\
if exist "%~dp0logs" (
    dir /b "%~dp0logs\*.log" 2>nul
    if %errorlevel%==0 (
        echo.
        echo 最新日志:
        for /f %%f in ('dir /b /o-d "%~dp0logs\*.log"') do (
            echo ===== %%~nf.log =====
            type "%~dp0logs\%%f" 2>nul
            goto end
        )
    ) else (
        echo [INFO] 暂无日志文件
    )
) else (
    echo [INFO] 日志目录不存在
)
goto end

:autostart
echo [INFO] 注册开机自启...
schtasks /CREATE /SC ONLOGON /TN "Guxiaozhi-AStockAutoRefresh" /TR "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File '%~dp0a_stock_auto_refresh.ps1'" /DELAY 0001:00 /F 2>nul
if %errorlevel%==0 (
    echo [OK] 开机自启已注册（登录1分钟后启动）
) else (
    echo [ERROR] 注册失败，请以管理员身份运行
)
goto end

:end
echo.
pause