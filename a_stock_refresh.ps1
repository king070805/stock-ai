# A-Stock Data Auto Refresh Script (Backup Mechanism)
# Executes every 10 minutes during trading hours
# Data source: Tencent API (fallback from East Money API)

param(
    [string]$ApiUrl = "http://localhost:5000/api/stocks?market=a&sort=change",
    [string]$LogDir = "$PSScriptRoot\logs"
)

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogFile = Join-Path $LogDir "a_stock_refresh_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8
    Write-Host $logEntry
}

# Check if within A-Stock trading hours
function Test-TradingHours {
    $now = Get-Date
    $dayOfWeek = $now.DayOfWeek
    
    # No trading on weekends
    if ($dayOfWeek -eq 'Saturday' -or $dayOfWeek -eq 'Sunday') {
        return $false
    }
    
    $time = $now.TimeOfDay
    $morningStart = New-TimeSpan -Hours 9 -Minutes 30
    $morningEnd = New-TimeSpan -Hours 11 -Minutes 30
    $afternoonStart = New-TimeSpan -Hours 13 -Minutes 0
    $afternoonEnd = New-TimeSpan -Hours 15 -Minutes 0
    
    # Morning session 9:30-11:30
    if ($time -ge $morningStart -and $time -le $morningEnd) {
        return $true
    }
    # Afternoon session 13:00-15:00
    if ($time -ge $afternoonStart -and $time -le $afternoonEnd) {
        return $true
    }
    
    return $false
}

# Call API to refresh data
function Invoke-StockRefresh {
    try {
        Write-Log "Calling API to refresh A-Stock data: $ApiUrl"
        
        $response = Invoke-WebRequest -Uri $ApiUrl -Method GET -TimeoutSec 30 -UseBasicParsing
        
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            $stockCount = if ($data -is [array]) { $data.Count } else { 1 }
            Write-Log "A-Stock data refresh successful, got $stockCount stocks" "SUCCESS"
            return $true
        } else {
            Write-Log "API returned non-200 status: $($response.StatusCode)" "ERROR"
            return $false
        }
    } catch {
        Write-Log "Refresh failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Main logic
Write-Log "====== A-Stock Backup Refresh Task Started ======"

if (-not (Test-TradingHours)) {
    Write-Log "Not in trading hours, skipping refresh" "WARN"
    exit 0
}

$success = Invoke-StockRefresh
if ($success) {
    Write-Log "====== Refresh Completed ======"
    exit 0
} else {
    Write-Log "====== Refresh Failed ======" "ERROR"
    exit 1
}
