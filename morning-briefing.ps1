# Morning Briefing Script - 晨间简报
# Runs on weekday mornings, generates AI news + fund recommendation report

$ErrorActionPreference = "SilentlyContinue"
$reportDir = "C:\Users\lenovo\Documents\daliy\briefings"
$dateStr = Get-Date -Format "yyyy-MM-dd"
$timeStr = Get-Date -Format "HH:mm"
$weekdayNames = @("日", "一", "二", "三", "四", "五", "六")
$weekday = $weekdayNames[(Get-Date).DayOfWeek.value__]
$reportPath = Join-Path $reportDir "briefing-$dateStr.md"

# Create report directory if it doesn't exist
if (-not (Test-Path $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

# ========== 1. Fetch AI News ==========
function Get-AINews {
    $newsItems = @()
    
    # OpenAI Blog RSS
    try {
        $openai = Invoke-RestMethod -Uri "https://openai.com/blog/rss.xml" -TimeoutSec 15
        foreach ($item in $openai.rss.channel.item | Select-Object -First 5) {
            $newsItems += [PSCustomObject]@{
                Source = "OpenAI"
                Title = ([string]$item.title).Trim()
                Link  = ([string]$item.link).Trim()
                Date  = ([string]$item.pubDate).Trim()
            }
        }
    } catch { }
    
    # MIT Technology Review - AI section
    try {
        $mit = Invoke-RestMethod -Uri "https://www.technologyreview.com/feed/" -TimeoutSec 15
        foreach ($item in $mit.rss.channel.item | Where-Object { $_.category -match "artificial.intelligence|AI|machine.learning" } | Select-Object -First 5) {
            $newsItems += [PSCustomObject]@{
                Source = "MIT Tech Review"
                Title = ([string]$item.title).Trim()
                Link  = ([string]$item.link).Trim()
                Date  = ([string]$item.pubDate).Trim()
            }
        }
    } catch { }
    
    # Hacker News (top AI-related)
    try {
        $hn = Invoke-RestMethod -Uri "https://hnrss.org/frontpage?q=AI+OR+LLM+OR+GPT+OR+OpenAI+OR+model" -TimeoutSec 15
        foreach ($item in $hn.rss.channel.item | Select-Object -First 8) {
            $newsItems += [PSCustomObject]@{
                Source = "Hacker News"
                Title = ([string]$item.title).Trim()
                Link  = ([string]$item.link).Trim()
                Date  = ([string]$item.pubDate).Trim()
            }
        }
    } catch { }

    # 机器之心 RSS
    try {
        $jqz = Invoke-RestMethod -Uri "https://www.jiqizhixin.com/rss" -TimeoutSec 15
        foreach ($item in $jqz.rss.channel.item | Select-Object -First 5) {
            $newsItems += [PSCustomObject]@{
                Source = "机器之心"
                Title = ([string]$item.title).Trim()
                Link  = ([string]$item.link).Trim()
                Date  = ([string]$item.pubDate).Trim()
            }
        }
    } catch { }
    
    return $newsItems
}

# ========== 2. Fetch Fund Data ==========
function Get-FundRecommendations {
    $funds = @()
    
    # Eastmoney fund ranking API - top performing funds
    try {
        $uri = "https://fundapi.eastmoney.com/fundtraditan/Api/FundRank?pageIndex=1&pageSize=10&ft=gp&sc=6m&st=desc"
        $result = Invoke-RestMethod -Uri $uri -TimeoutSec 15
        if ($result.Data) {
            foreach ($f in $result.Data) {
                $funds += [PSCustomObject]@{
                    Code     = $f.FCODE
                    Name     = $f.SHORTNAME
                    Type     = $f.FTYPE
                    NAV      = $f.DWJZ
                    OneMonth = $f.ONE_MONTH
                    ThreeMonth = $f.THREE_MONTH
                    SixMonth = $f.SIX_MONTH
                    OneYear  = $f.ONE_YEAR
                }
            }
        }
    } catch { }
    
    # Backup: use a simpler public API
    if ($funds.Count -eq 0) {
        try {
            $uri = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+s:3&fields=f12,f14,f2,f3,f4,f8,f15"
            $result = Invoke-RestMethod -Uri $uri -TimeoutSec 15
            if ($result.data.diff) {
                foreach ($f in $result.data.diff) {
                    $funds += [PSCustomObject]@{
                        Code     = $f.f12
                        Name     = $f.f14
                        NAV      = $f.f2
                        ChangePct = $f.f3
                        ChangeAmt = $f.f4
                        OneMonth  = $f.f8
                        OneYear   = $f.f15
                    }
                }
            }
        } catch { }
    }
    
    return $funds
}

# ========== 3. Generate Report ==========
$news = Get-AINews
$funds = Get-FundRecommendations

$report = @"
# 🌅 晨间简报 | 周$weekday $dateStr $timeStr

---

## 🤖 AI 最新资讯

"@

if ($news.Count -gt 0) {
    $seen = @{}
    $count = 0
    foreach ($item in $news) {
        $key = $item.Title.Substring(0, [Math]::Min(50, $item.Title.Length))
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        $count++
        if ($count -gt 15) { break }
        $report += "`n- **[$($item.Source)]** [$($item.Title)]($($item.Link))"
    }
} else {
    $report += "`n> ⚠️ 今日未能获取AI新闻，请检查网络连接。"
}

$report += @"

---

## 📈 基金参考

"@

if ($funds.Count -gt 0) {
    $report += "`n| 代码 | 名称 | 净值 | 近1月 | 近3月 | 近6月 | 近1年 |"
    $report += "`n|------|------|------|-------|-------|-------|-------|"
    foreach ($f in $funds | Select-Object -First 10) {
        $nav = if ($f.NAV) { [string]$f.NAV } else { "-" }
        $m1 = if ($f.OneMonth) { "$($f.OneMonth)%" } else { "-" }
        $m3 = if ($f.ThreeMonth) { "$($f.ThreeMonth)%" } else { "-" }
        $m6 = if ($f.SixMonth) { "$($f.SixMonth)%" } else { "-" }
        $y1 = if ($f.OneYear) { "$($f.OneYear)%" } else { "-" }
        $report += "`n| $($f.Code) | $($f.Name) | $nav | $m1 | $m3 | $m6 | $y1 |"
    }
} else {
    $report += "`n> ⚠️ 今日未能获取基金数据，请检查网络连接。"
}

$report += @"

---

> 📬 每日自动生成 | $dateStr
"@

$report | Out-File -FilePath $reportPath -Encoding UTF8
Write-Output "Briefing saved to: $reportPath"
