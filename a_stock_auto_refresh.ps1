# A股数据自动刷新脚本（备用刷新机制）
# 功能：在A股交易时段每10分钟调用本地API刷新数据
# 注意：前端已有每5分钟自动刷新，此脚本作为备用机制
# ============================================
# v2.0 - 增强版
# - 文件日志记录
# - 失败自动重试（最多3次）
# - 交易时段智能判断
# - 涨跌异动摘要输出
# ============================================

param(
    [int]$IntervalMinutes = 10,
    [string]$ApiUrl = "http://localhost:5000/api/stocks?market=a&sort=change",
    [string]$LogDir = "$PSScriptRoot\logs"
)

# ========== 日志配置 ==========
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$logFile = Join-Path $LogDir "auto_refresh_$(Get-Date -Format 'yyyyMM').log"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # 控制台输出
    Write-Host $logEntry
    
    # 文件日志
    "$logEntry" | Out-File -FilePath $logFile -Encoding utf8 -Append
}

function Test-IsTradingTime {
    $now = Get-Date
    $dayOfWeek = $now.DayOfWeek

    # 周六/周日休市
    if ($dayOfWeek -eq "Saturday" -or $dayOfWeek -eq "Sunday") {
        return $false
    }

    $today = Get-Date -Hour 0 -Minute 0 -Second 0
    
    # 上午盘: 09:30 - 11:30
    $morningStart = $today.AddHours(9).AddMinutes(30)
    $morningEnd   = $today.AddHours(11).AddMinutes(30)
    
    # 下午盘: 13:00 - 15:00
    $afternoonStart = $today.AddHours(13)
    $afternoonEnd   = $today.AddHours(15)

    $inMorning   = ($now -ge $morningStart) -and ($now -le $morningEnd)
    $inAfternoon = ($now -ge $afternoonStart) -and ($now -le $afternoonEnd)

    return $inMorning -or $inAfternoon
}

function Invoke-StockRefresh {
    param(
        [int]$MaxRetries = 3,
        [int]$RetryDelaySec = 5
    )

    $lastError = $null

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            if ($attempt -gt 1) {
                Write-Log "Retry attempt $attempt/$MaxRetries..." "WARN"
                Start-Sleep -Seconds $RetryDelaySec
            }

            $response = Invoke-WebRequest -Uri $ApiUrl -UseBasicParsing -TimeoutSec 30
            $data = $response.Content | ConvertFrom-Json
            $stockCount = ($data.stocks | Measure-Object).Count
            $responseSize = $response.RawContentLength

            Write-Log "Refresh OK | Status: $($response.StatusCode) | Stocks: $stockCount | Size: ${responseSize}bytes"

            # 输出前3名异动股摘要
            if ($stockCount -gt 0) {
                $topGainer = $data.stocks | Sort-Object { [double]$_.change_pct } -Descending | Select-Object -First 1
                $topLoser  = $data.stocks | Sort-Object { [double]$_.change_pct } | Select-Object -First 1
                Write-Log "Top Gainer: $($topGainer.name)($($topGainer.code)) $($topGainer.change_pct)% @ $($topGainer.price)"
                Write-Log "Top Loser : $($topLoser.name)($($topLoser.code)) $($topLoser.change_pct)% @ $($topLoser.price)"
            }

            return $true
        } catch {
            $lastError = $_
            Write-Log "Refresh attempt $attempt/$MaxRetries failed: $_" "ERROR"
        }
    }

    Write-Log "All $MaxRetries retries exhausted. Last error: $lastError" "ERROR"
    return $false
}

# ========== 启动信息 ==========
Write-Log "================================================================"
Write-Log "A-Stock Auto Refresh Script v2.0 Started"
Write-Log "API URL: $ApiUrl"
Write-Log "Refresh Interval: ${IntervalMinutes} minutes (${IntervalMinutes}min × 60s = $($IntervalMinutes * 60)s)"
Write-Log "Trading Hours: Mon-Fri 09:30-11:30, 13:00-15:00"
Write-Log "Log File: $logFile"
Write-Log "================================================================"

# ========== 主循环 ==========
$cycleCount = 0
while ($true) {
    $cycleCount++
    Write-Log "--- Cycle #$cycleCount ---"

    if (Test-IsTradingTime) {
        Invoke-StockRefresh
    } else {
        $now = Get-Date
        $dayOfWeek = $now.DayOfWeek
        if ($dayOfWeek -eq "Saturday" -or $dayOfWeek -eq "Sunday") {
            Write-Log "Weekend ($dayOfWeek) - skip refresh, next check in ${IntervalMinutes}min"
        } else {
            Write-Log "Non-trading hours - skip refresh, next check in ${IntervalMinutes}min"
        }
    }

    Write-Log "Next refresh in ${IntervalMinutes} minutes..."
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}