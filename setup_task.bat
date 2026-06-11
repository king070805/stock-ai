@echo off
chcp 65001 >nul
echo Creating A-Stock auto refresh scheduled tasks...

set SCRIPT_PATH=C:\Users\lenovo\Documents\daliy\a_stock_refresh.ps1

schtasks /Delete /TN "AStock_Refresh_Backup_AM" /F >nul 2>&1
schtasks /Delete /TN "AStock_Refresh_Backup_PM" /F >nul 2>&1

echo Creating AM session task (9:30-11:30 every 10 min)...
schtasks /Create /TN "AStock_Refresh_Backup_AM" /TR "powershell.exe -ExecutionPolicy Bypass -File %SCRIPT_PATH%" /SC DAILY /ST 09:30 /RI 10 /DU 02:00 /F

echo Creating PM session task (13:00-15:00 every 10 min)...
schtasks /Create /TN "AStock_Refresh_Backup_PM" /TR "powershell.exe -ExecutionPolicy Bypass -File %SCRIPT_PATH%" /SC DAILY /ST 13:00 /RI 10 /DU 02:00 /F

echo.
echo Tasks created successfully!
pause
