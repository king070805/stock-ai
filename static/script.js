(function() {
"use strict";

var currentMarket = 'a';
var currentSort = 'amount';
var currentSector = 'all';
var watchlist = loadWatchlist();
var currentStockData = null;
var currentPayOrder = null;
var payCheckTimer = null;
var userId = localStorage.getItem('guxiaozhi_user_id') || '';
if (!userId) { userId = 'user_' + crypto.randomUUID().slice(0, 8); localStorage.setItem('guxiaozhi_user_id', userId); }

document.addEventListener('DOMContentLoaded', function() {
    setupReportForm();
    loadStocks();
    loadBriefing();
    loadSectorHeat();
    setupSearch();
    setupTabs();
    setupSectorFilter();
    renderWatchlistDrawer();
    bindGlobalButtons();
    setupWatchlistDrawer();
    setupChartCrosshair();
    setupFoldables();
    setupAutoRefresh();
    loadUserLimit();
    loadReportFromQuery();
});

// ========== 首页生成公开信息摘要 ==========
function setupReportForm() {
    var form = document.getElementById('reportForm');
    var input = document.getElementById('reportInput');
    var error = document.getElementById('reportFormError');
    var submit = document.getElementById('reportSubmit');
    var example = document.getElementById('exampleReportBtn');
    if (!form || !input || !submit) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var code = (input.value || '').trim();
        if (!code) {
            if (error) error.textContent = '请输入股票代码或股票名称';
            input.focus();
            return;
        }
        if (error) error.textContent = '';
        submit.textContent = '正在整理公开信息...';
        resolveStockInput(code)
            .then(function(resolvedCode) {
                window.location.href = '/report?stock=' + encodeURIComponent(resolvedCode);
            })
            .catch(function() {
                if (error) error.textContent = '未找到匹配股票，可试试：600519、贵州茅台、NVDA、英伟达';
            })
            .finally(function() {
                setTimeout(function() { submit.textContent = '生成 AI 股票报告'; }, 800);
            });
    });

    if (example) {
        example.addEventListener('click', function() {
            input.value = 'NVDA';
            if (error) error.textContent = '';
            analyzeStock('NVDA');
        });
    }
}

function loadReportFromQuery() {
    var params = new URLSearchParams(window.location.search);
    var stock = params.get('stock');
    if (stock) {
        var input = document.getElementById('reportInput');
        if (input) input.value = stock;
        analyzeStock(stock);
    }
}

function resolveStockInput(value) {
    var q = (value || '').trim();
    if (/^[A-Za-z.]{1,8}$/.test(q) || /^\d{6}$/.test(q)) {
        return Promise.resolve(q.toUpperCase());
    }
    return fetch('/api/search?q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.results && data.results.length && data.results[0].code) {
                return data.results[0].code;
            }
            throw new Error('not found');
        });
}

// ========== 用户次数限制 ==========
function loadUserLimit() {
    fetch('/api/user/limit?user_id=' + userId)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                var info = data.limit_info;
                var limitText = document.getElementById('limitText');
                if (limitText) {
                    if (info.is_member) {
                        limitText.innerHTML = '✨ 会员 · 今日剩余 ' + info.remaining + '/' + info.limit + ' 次';
                        limitText.style.color = '#667eea';
                    } else {
                        limitText.innerHTML = '🔥 免费 · 今日剩余 ' + info.remaining + '/' + info.limit + ' 次';
                        if (info.remaining <= 0) {
                            limitText.style.color = '#ff6b6b';
                        }
                    }
                }
            }
        })
        .catch(function(e) { console.error('获取次数信息失败', e); });
}

// ========== Auto Refresh ==========
function setupAutoRefresh() {
    // A股交易时段: 周一到周五 9:30-15:00 (北京时间)
    // 美股交易时段: 周一到周五 21:30-04:00 (北京时间)
    function isTradingHours() {
        var now = new Date();
        var day = now.getDay();
        if (day === 0 || day === 6) return false; // 周末不刷新
        var h = now.getHours();
        var m = now.getMinutes();
        var t = h * 60 + m;
        // A股: 9:30-15:00
        if (t >= 570 && t <= 900) return true;
        // 美股: 21:30-04:00 (次日)
        if (t >= 1290 || t <= 240) return true;
        return false;
    }

    // 交易时段每5分钟刷新一次，非交易时段不自动刷新
    setInterval(function() {
        if (isTradingHours()) {
            loadStocks();
            // 更新状态栏显示刷新时间
            var st = document.getElementById('marketStatus');
            if (st) {
                var now = new Date();
                var timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
                st.innerHTML = '<span class="status-dot open"></span><span class="status-text">实时数据 · ' + timeStr + ' 更新</span>';
            }
        }
    }, 5 * 60 * 1000); // 5分钟
}

// ========== Sector Filter ==========
function setupSectorFilter() {
    document.querySelectorAll('.sector-filter-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.sector-filter-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentSector = btn.getAttribute('data-sector');
            loadStocks();
        });
    });
}

// ========== Sector Heat Card ==========
function loadSectorHeat() {
    var card = document.getElementById('sectorHeatCard');
    var list = document.getElementById('sectorHeatList');
    if (!card || !list) return;
    fetch('/api/sector-heat').then(function(r) { return r.json(); }).then(function(data) {
        if (!data.sectors || !data.sectors.length) return;
        card.style.display = 'block';
        list.innerHTML = data.sectors.map(function(s) {
            return '<div class="sector-heat-item"><div class="sh-name">' + escHtml(s.name) + '</div><div class="sh-stocks">热度 <span>' + (s.heat || '-') + '</span></div></div>';
        }).join('');
    }).catch(function() {});
}

// ========== Foldables ==========
function setupFoldables() {
    var newsToggle = document.getElementById('newsToggle');
    var newsList = document.getElementById('newsList');
    if (newsToggle) newsToggle.addEventListener('click', function() {
        var open = newsList.classList.toggle('open');
        newsToggle.classList.toggle('open', open);
    });
    var basisToggle = document.getElementById('basisToggle');
    var basisContent = document.getElementById('basisContent');
    if (basisToggle) basisToggle.addEventListener('click', function() {
        basisContent.classList.toggle('open');
    });
}

// ========== Global Button Bindings ==========
function bindGlobalButtons() {
    safeBind('btnWatchlist', 'click', openWatchlistDrawer);
    safeBind('btnCloseWatchlist', 'click', closeWatchlistDrawer);
    safeBind('btnCloseAnalysis', 'click', closeAnalysis);
    safeBind('btnShare', 'click', shareAnalysis);
    safeBind('btnMemory', 'click', toggleMemory);
    safeBind('btnPremium', 'click', showPay);
    safeBind('btnClosePay', 'click', closePay);
    safeBind('watchlistOverlay', 'click', closeWatchlistDrawer);
    var paySub = document.getElementById('btnPaySubmit');
    if (paySub) paySub.addEventListener('click', createReportOrder);
}
function safeBind(id, event, fn) { var el = document.getElementById(id); if (el) el.addEventListener(event, fn); }

// ========== Watchlist (Drawer) ==========
function loadWatchlist() { try { return JSON.parse(localStorage.getItem('stockWatchlist') || '[]'); } catch(e) { return []; } }
function saveWatchlist() { localStorage.setItem('stockWatchlist', JSON.stringify(watchlist)); }
function openWatchlistDrawer() { document.getElementById('watchlistDrawer').classList.add('open'); document.getElementById('watchlistOverlay').classList.add('open'); renderWatchlistDrawer(); }
function closeWatchlistDrawer() { document.getElementById('watchlistDrawer').classList.remove('open'); document.getElementById('watchlistOverlay').classList.remove('open'); }
function toggleWatchlistStar(code, name, btn) {
    var idx = watchlist.findIndex(function(w) { return w.code === code; });
    if (idx >= 0) { watchlist.splice(idx, 1); if (btn) { btn.classList.remove('starred'); btn.textContent = '\u2606'; } }
    else { if (watchlist.length >= 20) { showToast('最多20只'); return; } watchlist.push({code: code, name: name}); if (btn) { btn.classList.add('starred'); btn.textContent = '\u2605'; } }
    saveWatchlist(); renderWatchlistDrawer(); updateTableStars();
}
function isStarred(code) { return watchlist.some(function(w) { return w.code === code; }); }
function updateTableStars() { document.querySelectorAll('.btn-star').forEach(function(b) { var c = b.getAttribute('data-code'); var s = isStarred(c); b.classList.toggle('starred', s); b.textContent = s ? '\u2605' : '\u2606'; }); }
function renderWatchlistDrawer() {
    var body = document.getElementById('watchlistDrawerBody'); var cnt = document.getElementById('watchlistCount'); var empty = document.getElementById('watchlistEmpty');
    cnt.textContent = watchlist.length;
    if (watchlist.length === 0) { body.innerHTML = ''; if (empty) empty.style.display = 'block'; return; }
    if (empty) empty.style.display = 'none';
    body.innerHTML = watchlist.map(function(w) { return '<div class="watchlist-drawer-item" data-code="' + escHtml(w.code) + '"><span class="wd-code">' + escHtml(w.code) + '</span><span class="wd-name">' + escHtml(w.name) + '</span><span class="wd-change" id="wdChg_' + escHtml(w.code) + '">-</span><button class="wd-remove" data-code="' + escHtml(w.code) + '" aria-label="移除">\u00d7</button></div>'; }).join('');
    body.querySelectorAll('.wd-remove').forEach(function(btn) { btn.addEventListener('click', function(e) { e.stopPropagation(); var code = btn.getAttribute('data-code'); var name = watchlist.find(function(w) { return w.code === code; }); removeFromWatchlistWithUndo(code, name ? name.name : code); }); });
    body.querySelectorAll('.watchlist-drawer-item').forEach(function(item) { item.addEventListener('click', function() { analyzeStock(item.getAttribute('data-code')); closeWatchlistDrawer(); }); });
}
function removeFromWatchlistWithUndo(code, name) {
    var item = watchlist.find(function(w) { return w.code === code; }); if (!item) return;
    watchlist = watchlist.filter(function(w) { return w.code !== code; }); saveWatchlist(); renderWatchlistDrawer(); updateTableStars();
    showUndoToast('已移除 ' + escHtml(name || code), function() { watchlist.push(item); saveWatchlist(); renderWatchlistDrawer(); updateTableStars(); });
}
function removeFromWatchlist(code) { watchlist = watchlist.filter(function(w) { return w.code !== code; }); saveWatchlist(); renderWatchlistDrawer(); updateTableStars(); loadStocks(); }

// ========== Util: Sector / Dividend / Heat helpers ==========
function getSectorTag(code) {
    // AI算力产业链（50只）- 覆盖芯片、光模块、服务器、液冷、PCB、CPO等
    var aiCodes = [
        // AI芯片
        '002230','300033','688111','688256','688981','688012','688041','688525',
        // 光模块/CPO
        '300502','300308','300394','300548','002281','000938',
        // AI服务器
        '000977','603019','601138','002236',
        // 液冷/散热
        '002837','300499','301018','603912',
        // PCB/覆铜板
        '002463','600183','603228','300739',
        // 存储芯片
        '603986','688110','300223','000021',
        // 电源/变压器
        '300274','002335','600885',
        // CPO/光引擎
        '601231','603306','002384','300620',
        // 算力租赁/IDC
        '600845','600728','300017',
        // 半导体设备
        '002371','688082','688072',
    ];
    // 低空经济（25只）
    var evCodes = [
        '002085','600760','688568','300696','688297','002389','600118',
        '000768','600316','002013','600038','300900','002151',
        '300114','002025','600372','600391','300159','002179',
        '600967','300424','002933','300411','603261','688070',
    ];
    // 高股息（40只）
    var divCodes = [
        '601398','601939','601288','600036','600900','601088','600585',
        '601318','600028','601857','600019','601988','601328','600016',
        '601998','601818','601186','601668','601390','601728','600048',
        '600104','600887','600690','600741','600660','600276','600309',
        '600406','600089','600115','601111','600029','600377','600350',
        '600018','600017','600508','601699','601225',
    ];
    if (aiCodes.indexOf(code) >= 0) return {cls:'ai', label:'AI算力'};
    if (evCodes.indexOf(code) >= 0) return {cls:'ev', label:'低空经济'};
    if (divCodes.indexOf(code) >= 0) return {cls:'dividend', label:'高股息'};
    return {cls:'other', label:'其他'};
}
function getDividendRate(code) {
    var rates = {
        '601398':'5.2','601939':'5.0','601288':'4.8','600036':'3.5',
        '600900':'3.8','601088':'6.1','600585':'4.2','601857':'5.5',
        '600028':'5.3','600019':'4.5','601988':'4.9','601328':'5.1',
        '600016':'4.3','601998':'4.7','601818':'4.1','601186':'3.9',
        '601668':'3.2','601390':'3.0','601728':'2.8','600048':'3.6',
    };
    return rates[code] || null;
}
function getHeatLevel(code) {
    var hot = ['002230','300033','002085','601398'];
    var warm = ['688111','300502','600760','688568','600036','600900'];
    if (hot.indexOf(code) >= 0) return {cls:'hot', icon:'\uD83D\uDD25'};
    if (warm.indexOf(code) >= 0) return {cls:'warm', icon:'\uD83D\uDD25'};
    return {cls:'cool', icon:'\uD83D\uDD25'};
}
function matchesSector(code) {
    if (currentSector === 'all') return true;
    var tag = getSectorTag(code);
    return tag.cls === currentSector;
}
function formatRelativeTime(dateStr) {
    if (!dateStr) return '';
    try { var d = new Date(dateStr); var now = new Date(); var diff = Math.floor((now - d) / 1000);
        if (diff < 60) return '刚刚'; if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + '小时前'; return Math.floor(diff / 86400) + '天前';
    } catch(e) { return dateStr; }
}
function formatUpdateTime() { var now = new Date(); return now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0'); }

// ========== Market Overview ==========
function updateMarketOverview(stocks) {
    if (!stocks || !stocks.length) return;
    var upCount = 0, downCount = 0, totalChange = 0;
    stocks.forEach(function(s) {
        var chg = parseFloat(s.change_pct) || 0;
        if (chg > 0) upCount++;
        else if (chg < 0) downCount++;
        totalChange += chg;
    });
    var total = upCount + downCount;
    var avgChange = total > 0 ? (totalChange / stocks.length).toFixed(2) : 0;
    var upPct = total > 0 ? (upCount / total * 100).toFixed(1) : 50;
    var downPct = total > 0 ? (downCount / total * 100).toFixed(1) : 50;

    var shIndex = document.getElementById('shIndex');
    var shChange = document.getElementById('shChange');
    var barUp = document.getElementById('barUp');
    var barDown = document.getElementById('barDown');
    var statUp = document.getElementById('statUp');
    var statDown = document.getElementById('statDown');
    var sentiment = document.getElementById('sentiment');
    var sentimentLabel = document.getElementById('sentimentLabel');
    var updateTime = document.getElementById('updateTime');

    if (shIndex) shIndex.textContent = avgChange > 0 ? '+' + avgChange + '%' : avgChange + '%';
    if (shChange) {
        shChange.textContent = (avgChange >= 0 ? '+' : '') + avgChange + '%';
        shChange.className = 'overview-change ' + (avgChange >= 0 ? 'up' : 'down');
    }
    if (barUp) barUp.style.width = upPct + '%';
    if (barDown) barDown.style.width = downPct + '%';
    if (statUp) statUp.textContent = upCount + ' 涨';
    if (statDown) statDown.textContent = downCount + ' 跌';

    if (sentiment && sentimentLabel) {
        var sentimentText = '', sentimentEmoji = '';
        if (avgChange > 1) { sentimentEmoji = '↑'; sentimentText = '上行较多'; }
        else if (avgChange > 0.3) { sentimentEmoji = '↑'; sentimentText = '小幅上行'; }
        else if (avgChange > -0.3) { sentimentEmoji = '·'; sentimentText = '变化不大'; }
        else if (avgChange > -1) { sentimentEmoji = '↓'; sentimentText = '小幅回落'; }
        else { sentimentEmoji = '↓'; sentimentText = '回落较多'; }
        sentiment.textContent = sentimentEmoji;
        sentimentLabel.textContent = sentimentText;
    }

    if (updateTime) updateTime.textContent = '更新于 ' + formatUpdateTime();
}

// ========== Sector Stock Pools ==========
function getSectorStockCodes(sector) {
    if (sector === 'ai') return [
        '002230','300033','688111','688256','688981','688012','688041','688525',
        '300502','300308','300394','300548','002281','000938',
        '000977','603019','601138','002236',
        '002837','300499','301018','603912',
        '002463','600183','603228','300739',
        '603986','688110','300223','000021',
        '300274','002335','600885',
        '601231','603306','002384','300620',
        '600845','600728','300017',
        '002371','688082','688072',
    ];
    if (sector === 'ev') return [
        '002085','600760','688568','300696','688297','002389','600118',
        '000768','600316','002013','600038','300900','002151',
        '300114','002025','600372','600391','300159','002179',
        '600967','300424','002933','300411','603261','688070',
    ];
    if (sector === 'dividend') return [
        '601398','601939','601288','600036','600900','601088','600585',
        '601318','600028','601857','600019','601988','601328','600016',
        '601998','601818','601186','601668','601390','601728','600048',
        '600104','600887','600690','600741','600660','600276','600309',
        '600406','600089','600115','601111','600029','600377','600350',
        '600018','600017','600508','601699','601225',
    ];
    return [];
}

// ========== Stock List ==========
function loadStocks() {
    var tbody = document.getElementById('stockTableBody'); var st = document.getElementById('marketStatus');
    var banner = document.getElementById('usDataBanner');
    tbody.innerHTML = '<tr><td colspan="11" class="loading-row">加载中...</td></tr>';
    st.innerHTML = '<span class="status-dot"></span><span class="status-text">加载中...</span>';
    if (banner) banner.style.display = 'none';

    // 当选择特定分区且为A股时，直接获取该分区所有股票
    if (currentMarket === 'a' && currentSector !== 'all') {
        loadSectorStocks(currentSector);
        return;
    }

    fetch('/api/stocks?market=' + currentMarket + '&sort=' + currentSort)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) throw new Error(data.error);
            var isUS = currentMarket === 'us';
            if (isUS && banner) banner.style.display = 'block';
            if (!data.stocks || data.stocks.length === 0) {
                var msg = isUS ? '数据暂不可用' : '暂无数据';
                tbody.innerHTML = '<tr><td colspan="11" class="loading-row">' + escHtml(msg) + '</td></tr>';
                st.innerHTML = '<span class="status-dot closed"></span><span class="status-text">休市中</span>'; return;
            }
            st.innerHTML = '<span class="status-dot open"></span><span class="status-text">实时数据</span>';
            updateMarketOverview(data.stocks);
            renderStockRows(data.stocks, false);
        })
        .catch(function() { tbody.innerHTML = '<tr><td colspan="11" class="loading-row">加载失败，<a href="#" id="retryLink" style="color:var(--accent)">重试</a></td></tr>'; st.innerHTML = '<span class="status-dot error"></span><span class="status-text">连接失败</span>'; var rl = document.getElementById('retryLink'); if (rl) rl.addEventListener('click', function(e) { e.preventDefault(); loadStocks(); }); if (currentMarket === 'us' && banner) banner.style.display = 'block'; });
}

function loadSectorStocks(sector) {
    var tbody = document.getElementById('stockTableBody'); var st = document.getElementById('marketStatus');
    
    // 通过后端API获取赛道数据（避免跨域问题）
    fetch('/api/sector-stocks?sector=' + sector + '&sort=' + currentSort)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) throw new Error(data.error);
            if (!data.stocks || data.stocks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="11" class="loading-row">该赛道暂无匹配股票</td></tr>';
                st.innerHTML = '<span class="status-dot closed"></span><span class="status-text">暂无数据</span>';
                return;
            }
            st.innerHTML = '<span class="status-dot open"></span><span class="status-text">实时数据</span>';
            updateMarketOverview(data.stocks);
            renderStockRows(data.stocks, true);
        })
        .catch(function() {
            tbody.innerHTML = '<tr><td colspan="11" class="loading-row">加载失败，<a href="#" id="retryLink" style="color:var(--accent)">重试</a></td></tr>';
            st.innerHTML = '<span class="status-dot error"></span><span class="status-text">连接失败</span>';
            var rl = document.getElementById('retryLink');
            if (rl) rl.addEventListener('click', function(e) { e.preventDefault(); loadSectorStocks(sector); });
        });
}

function renderStockRows(stocks, isSectorView) {
    var tbody = document.getElementById('stockTableBody');
    var rows = '';
    var displayCount = 0;
    stocks.forEach(function(s, i) {
        if (!isSectorView && !matchesSector(s.code)) return;
        displayCount++;
        var chg = parseFloat(s.change_pct) || 0; var cls = chg > 0 ? 'up' : chg < 0 ? 'down' : '';
        var sign = chg > 0 ? '+' : ''; var starred = isStarred(s.code);
        var absChg = Math.abs(chg);
        var trendBar = absChg > 0 ? '<span class="mini-trend-bar" style="width:' + Math.min(60, absChg * 6) + 'px;background:' + (chg > 0 ? 'var(--up)' : 'var(--down)') + '"></span>' : '';
        var priceArrow = chg > 0 ? '<span class="price-arrow up">\u2191</span>' : chg < 0 ? '<span class="price-arrow down">\u2193</span>' : '';
        var tag = getSectorTag(s.code);
        var divRate = getDividendRate(s.code);
        var divHtml = divRate ? (parseFloat(divRate) > 3 ? '<span class="dividend-high">' + divRate + '%</span>' : divRate + '%') : '-';
        var heat = getHeatLevel(s.code);

        rows += '<tr class="stock-row" data-code="' + escHtml(s.code) + '">' +
            '<td class="col-wl"><button class="btn-star ' + (starred ? 'starred' : '') + '" data-code="' + escHtml(s.code) + '" data-name="' + escHtml(s.name) + '">' + (starred ? '\u2605' : '\u2606') + '</button></td>' +
            '<td class="col-rank">' + displayCount + '</td>' +
            '<td class="col-name"><span class="stock-name" data-tooltip="数据来源：东方财富">' + escHtml(s.name) + '</span><span class="stock-code">' + escHtml(s.code) + '</span></td>' +
            '<td class="col-tag"><span class="sector-tag ' + tag.cls + '">' + tag.label + '</span></td>' +
            '<td class="col-price" data-tooltip="数据来源：东方财富">' + escHtml(s.price || '-') + priceArrow + '</td>' +
            '<td class="col-change ' + cls + '">' + sign + escHtml(s.change_pct || '-') + '%' + trendBar + '</td>' +
            '<td class="col-change hide-mobile">' + escHtml(s.amount || '-') + '</td>' +
            '<td class="col-dividend hide-mobile">' + divHtml + '</td>' +
            '<td class="col-change hide-mobile">' + escHtml(s.pe || '-') + '</td>' +
            '<td class="col-heat"><span class="heat-icon ' + heat.cls + '">' + heat.icon + '</span></td>' +
            '<td class="col-action"><button class="btn-analyze" data-code="' + escHtml(s.code) + '">生成摘要</button></td></tr>';
    });
    if (!rows) rows = '<tr><td colspan="11" class="loading-row">该赛道暂无匹配股票</td></tr>';
    tbody.innerHTML = rows;
    document.querySelectorAll('.btn-star').forEach(function(b) { b.addEventListener('click', function(e) { e.stopPropagation(); toggleWatchlistStar(b.getAttribute('data-code'), b.getAttribute('data-name'), b); }); });
    document.querySelectorAll('.btn-analyze').forEach(function(b) { b.addEventListener('click', function(e) { e.stopPropagation(); analyzeStock(b.getAttribute('data-code'), b); }); });
    document.querySelectorAll('.stock-row').forEach(function(r) { r.addEventListener('click', function() { analyzeStock(r.getAttribute('data-code'), r); }); });
}

// ========== Briefing ==========
function loadBriefing() {
    var el = document.getElementById('briefingContent');
    fetch('/api/briefing').then(function(r) { return r.json(); }).then(function(d) {
        el.innerHTML = d.briefing ? escHtml(d.briefing).replace(/\n/g, '<br>') : '简报生成中...';
    }).catch(function() { el.innerHTML = '简报暂不可用'; });
}

// ========== AI Analysis ==========
function analyzeStock(code, btnOrRow, forceRefresh) {
    var card = document.getElementById('analysisCard'); var nameEl = document.getElementById('analysisStockName');
    var infoEl = document.getElementById('stockQuickInfo'); var bodyEl = document.getElementById('analysisBody');
    var chartCanvas = document.getElementById('klineChart'); var shareBtn = document.getElementById('btnShare');
    var verdictBadge = document.getElementById('analysisVerdictBadge');
    var benchmark = document.getElementById('dataBenchmark');
    var policyWind = document.getElementById('policyWind');
    var pwText = document.getElementById('pwText');
    var relatedNews = document.getElementById('relatedNews');
    var newsList = document.getElementById('newsList');
    var analysisBasis = document.getElementById('analysisBasis');
    var basisContent = document.getElementById('basisContent');

    card.style.display = 'block'; nameEl.textContent = '分析中...'; infoEl.innerHTML = '';
    bodyEl.innerHTML = '<span style="color:var(--text-muted)">AI正在深度分析，约需5秒...</span>';
    shareBtn.style.display = 'none'; verdictBadge.style.display = 'none';
    if (benchmark) benchmark.style.display = 'none';
    if (policyWind) policyWind.style.display = 'none';
    if (relatedNews) relatedNews.style.display = 'none';
    if (analysisBasis) analysisBasis.style.display = 'none';
    card.classList.add('entering');

    var triggerBtn = btnOrRow && btnOrRow.classList && btnOrRow.classList.contains('btn-analyze') ? btnOrRow : null;
    var triggerRow = btnOrRow && btnOrRow.classList && btnOrRow.classList.contains('stock-row') ? btnOrRow : null;
    if (triggerBtn) { triggerBtn.classList.add('loading'); triggerBtn.textContent = ''; }
    if (triggerRow) triggerRow.classList.add('loading-row-state');

    var ctx = chartCanvas.getContext('2d'); ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);

    var refreshParam = forceRefresh ? '&refresh=true' : '';
    fetch('/api/analyze?code=' + code + '&user_id=' + userId + refreshParam)
        .then(function(r) { 
            if (r.status === 403) {
                // 次数用完
                return r.json().then(function(data) {
                    if (triggerBtn) { triggerBtn.classList.remove('loading'); triggerBtn.textContent = '生成摘要'; }
                    if (triggerRow) triggerRow.classList.remove('loading-row-state');
                    card.classList.remove('entering');
                    card.style.display = 'block';
                    nameEl.textContent = '次数已用完';
                    bodyEl.innerHTML = 
                        '<div style="text-align:center;padding:20px;">' +
                        '<div style="font-size:48px;margin-bottom:10px;">😅</div>' +
                        '<div style="color:var(--down);font-weight:600;margin-bottom:8px;font-size:16px;">' + escHtml(data.error) + '</div>' +
                        '<div style="color:var(--text-secondary);font-size:13px;margin-bottom:16px;">' + escHtml(data.message) + '</div>' +
                        '<a href="/subscribe" style="display:inline-block;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">' +
                        '开通信息整理服务' +
                        '</a>' +
                        '</div>';
                    return null;
                });
            }
            return r.json();
        })
        .then(function(data) {
            if (!data) return; // 次数用完的情况已处理
            if (triggerBtn) { triggerBtn.classList.remove('loading'); triggerBtn.textContent = '生成摘要'; }
            if (triggerRow) triggerRow.classList.remove('loading-row-state');
            card.classList.remove('entering');
            if (data.error) { bodyEl.innerHTML = '<div style="color:var(--down);font-weight:600;margin-bottom:4px">报告生成失败，请稍后重试</div><div style="color:var(--text-secondary);font-size:12px">' + escHtml(data.error) + '<br>本工具仅整理公开信息，不构成投资建议。</div>'; return; }
            currentStockData = data; var s = data.stock;
            var stockCode = s.code || s.symbol || code;
            var peValue = s.pe || s.pe_ratio || '-';
            nameEl.textContent = s.name + ' (' + stockCode + ')';
            var chg = parseFloat(s.change_pct) || 0; var cCls = chg > 0 ? 'up' : chg < 0 ? 'down' : '';
            var sign = chg > 0 ? '+' : '';

            infoEl.innerHTML =
                '<div class="stock-info-item"><span class="info-label">最新价</span><span class="info-value">' + escHtml(s.price || '-') + '</span></div>' +
                '<div class="stock-info-item"><span class="info-label">变动比例</span><span class="info-value ' + cCls + '">' + sign + escHtml(s.change_pct || '-') + '%</span></div>' +
                '<div class="stock-info-item"><span class="info-label">成交额</span><span class="info-value">' + escHtml(s.amount || '-') + '</span></div>' +
                '<div class="stock-info-item"><span class="info-label">市盈率</span><span class="info-value">' + escHtml(peValue) + '</span></div>';

            // 显示缓存提示（如果是缓存结果）
            var cacheHtml = '';
            if (data.cached) {
                cacheHtml = 
                    '<div style="background:linear-gradient(135deg,#667eea08 0%,#764ba208 100%);border:1px solid #667eea30;border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;">' +
                    '<div style="display:flex;align-items:center;gap:8px;">' +
                    '<span style="font-size:18px;">📋</span>' +
                    '<div>' +
                    '<div style="font-size:12px;color:#667eea;font-weight:600;">' + escHtml(data.message) + '</div>' +
                    '<div style="font-size:11px;color:var(--text-muted);margin-top:2px;">股价可能已变化，可重新整理最新公开信息</div>' +
                    '</div>' +
                    '</div>' +
                    '<button onclick="analyzeStock(\'' + escHtml(stockCode) + '\', null, true)" style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;padding:6px 14px;border-radius:5px;cursor:pointer;font-size:12px;font-weight:bold;white-space:nowrap;">' +
                    '🔄 重新分析' +
                    '</button>' +
                    '</div>';
            }
            
            bodyEl.innerHTML = cacheHtml + buildReportPreviewHtml(data);
            shareBtn.style.display = 'block';

            if (benchmark) { benchmark.style.display = 'block'; benchmark.textContent = '基于06-04收盘数据分析'; }

            if (data.policy && policyWind) {
                policyWind.style.display = 'block';
                var pwStance = data.policy.stance || 'neutral';
                policyWind.className = 'policy-wind ' + pwStance;
                pwText.textContent = data.policy.text || '暂无政策关联信息';
            }

            var verdict = data.verdict || '';
            if (verdict && verdictBadge) {
                verdictBadge.textContent = verdict; verdictBadge.style.display = 'inline-flex';
                if (verdict === '\u4fe1\u606f\u5173\u6ce8' || verdict === '\u5173\u6ce8') { verdictBadge.style.background = 'rgba(0,212,170,0.12)'; verdictBadge.style.color = '#00D4AA'; }
                else if (verdict === '\u98ce\u9669\u63d0\u793a' || verdict === '\u8b66\u60d5') { verdictBadge.style.background = 'rgba(255,71,87,0.12)'; verdictBadge.style.color = '#FF4757'; }
                else { verdictBadge.style.background = 'rgba(210,153,29,0.12)'; verdictBadge.style.color = '#d2991d'; }
            }

            if (data.news && data.news.length && relatedNews) {
                relatedNews.style.display = 'block';
                newsList.className = 'related-news-list';
                document.getElementById('newsToggle').classList.remove('open');
                newsList.innerHTML = data.news.slice(0, 5).map(function(n) {
                    return '<div class="related-news-item"><span class="rn-time">' + escHtml(formatRelativeTime(n.time)) + '</span><span class="rn-title">' + escHtml(n.title || '') + '</span></div>';
                }).join('');
            }

            if (data.basis && analysisBasis) {
                analysisBasis.style.display = 'block';
                basisContent.className = 'analysis-basis-content';
                basisContent.innerHTML = escHtml(data.basis);
            }

            if (data.history && data.history.length >= 3) drawKline(chartCanvas, data.history);
            else drawSimpleBar(chartCanvas, s);
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            card.focus();
        })
        .catch(function() {
            if (triggerBtn) { triggerBtn.classList.remove('loading'); triggerBtn.textContent = '生成摘要'; }
            if (triggerRow) triggerRow.classList.remove('loading-row-state');
            card.classList.remove('entering');
            bodyEl.innerHTML = '<div style="color:var(--down);font-weight:600;margin-bottom:4px">报告生成失败，请稍后重试</div><div style="color:var(--text-secondary);font-size:12px">本工具仅整理公开信息，不构成投资建议。</div>';
        });
}
window.analyzeStock = analyzeStock;

function closeAnalysis() { document.getElementById('analysisCard').style.display = 'none'; currentStockData = null; }
window.closeAnalysisPublic = closeAnalysis;

function buildReportPreviewHtml(data) {
    var s = data.stock || {};
    var state = data.unlock_state || 'login_required';
    var isPaid = state === 'paid';
    var reportId = data.report_id || '';
    var modules = normalizeReportModules(data);
    var validText = data.valid_until ? '当前报告已解锁，可在 ' + data.valid_until + ' 前重复查看。' : '解锁后有效期内可重复查看。';
    var unlockTitle = isPaid ? '完整报告已解锁' : (state === 'login_required' ? '登录后解锁完整报告' : '解锁完整报告');
    var unlockButton = isPaid
        ? '<button class="btn-unlock-report is-paid" type="button">查看完整报告</button>'
        : (state === 'login_required'
            ? '<a class="btn-unlock-report" href="/login?next=' + encodeURIComponent(window.location.pathname + window.location.search) + '">登录后解锁完整报告</a>'
            : '<button class="btn-unlock-report" type="button" onclick="showPay()">解锁完整报告</button>');
    var previewKeys = ['basic_info', 'recent_summary', 'news', 'announcements'];
    var moduleHtml = modules.map(function(module) {
        var lockedClass = (!isPaid && previewKeys.indexOf(module.key) < 0) ? ' is-preview-locked' : '';
        var content = (!isPaid && previewKeys.indexOf(module.key) < 0)
            ? '完整内容需解锁后查看。暂无可整理的信息时会保留占位。'
            : (module.content || '暂无可整理的信息');
        return '<div class="report-section' + lockedClass + '"><h4>' + escHtml(module.title) + '</h4><p>' + escHtml(content).replace(/\n/g, '<br>') + '</p></div>';
    }).join('');

    return '' +
        '<div class="report-preview">' +
        moduleHtml +
        '<div class="locked-report">' +
        '<h4>' + escHtml(unlockTitle) + '</h4>' +
        '<p>以较低成本获取更完整的公开信息整理，帮助节省资料查找时间。查看完整新闻、公告、公开市场数据、风险提示和 AI 公开信息摘要。</p>' +
        '<p>报告编号：' + escHtml(reportId || '生成中') + '</p>' +
        '<div class="locked-list">' +
        '<span>新闻动态完整整理</span>' +
        '<span>公司公告完整整理</span>' +
        '<span>资金动向整理</span>' +
        '<span>股价表现概览</span>' +
        '<span>市场关注点</span>' +
        '<span>潜在风险提示</span>' +
        '<span>AI 公开信息摘要</span>' +
        '<span>免责声明</span>' +
        '</div>' +
        unlockButton +
        '<p style="margin:8px 0 0;color:var(--text-muted);font-size:11px;">' + escHtml(validText) + ' 本报告仅基于公开信息整理，不构成投资建议。</p>' +
        '</div>' +
        '</div>';
}

function normalizeReportModules(data) {
    var modules = Array.isArray(data.report_modules) ? data.report_modules : [];
    var byKey = {};
    modules.forEach(function(module) {
        if (module && module.key) byKey[module.key] = module;
    });
    var s = data.stock || {};
    var analysis = data.analysis || '暂无可整理的信息';
    var news = Array.isArray(data.news) ? data.news.slice(0, 5).map(function(n) { return n.title || '暂无可整理的信息'; }).join('；') : '暂无可整理的信息';
    var policyText = data.policy && data.policy.text ? data.policy.text : '暂无可整理的信息';
    var fallback = [
        {key: 'basic_info', title: '股票基础信息', content: (s.name || '-') + '（' + (s.code || s.symbol || '-') + '）｜最新价 ' + (s.price || '-') + '｜公开行情变动比例 ' + (s.change_pct || '-') + '%'},
        {key: 'recent_summary', title: '近期重点摘要', content: analysis},
        {key: 'news', title: '新闻动态整理', content: news || '暂无可整理的信息'},
        {key: 'announcements', title: '公司公告整理', content: policyText},
        {key: 'capital_flow', title: '资金动向整理', content: data.basis || '暂无可整理的信息'},
        {key: 'price_overview', title: '股价表现概览', content: '最新价 ' + (s.price || '暂无可整理的信息') + '，公开行情变动比例 ' + (s.change_pct || '暂无可整理的信息') + '%。'},
        {key: 'market_attention', title: '市场关注点', content: '围绕新闻、公告和公开市场数据整理近期关注维度。'},
        {key: 'risk_notice', title: '潜在风险提示', content: '需关注数据延迟、公告变化、行业波动和公司基本面变化。'},
        {key: 'ai_summary', title: 'AI 总结：这只股票最近主要发生了什么', content: analysis},
        {key: 'disclaimer', title: '免责声明', content: '本报告仅基于公开信息整理，不构成投资建议。投资有风险，请独立判断。'}
    ];
    return fallback.map(function(item) {
        var module = byKey[item.key] || item;
        return {
            key: item.key,
            title: module.title || item.title,
            content: module.content || item.content || '暂无可整理的信息'
        };
    });
}

// ========== K-line Chart ==========
function setupChartCrosshair() {
    var chartContainer = document.getElementById('chartContainer'); var canvas = document.getElementById('klineChart');
    var cx = document.getElementById('crosshairX'); var cy = document.getElementById('crosshairY'); var cl = document.getElementById('crosshairLabel');
    if (!chartContainer || !canvas) return;
    canvas.addEventListener('mousemove', function(e) {
        if (!currentStockData) return; var rect = canvas.getBoundingClientRect(); var x = e.clientX - rect.left; var y = e.clientY - rect.top;
        cx.style.display = 'block'; cx.style.top = y + 'px'; cy.style.display = 'block'; cy.style.left = x + 'px';
        cl.style.display = 'block'; cl.style.left = (x + 12) + 'px'; cl.style.top = (y - 24) + 'px'; cl.textContent = 'x:' + Math.round(x) + ' y:' + Math.round(y);
    });
    canvas.addEventListener('mouseleave', function() { if (cx) cx.style.display = 'none'; if (cy) cy.style.display = 'none'; if (cl) cl.style.display = 'none'; });
}

function drawKline(canvas, history) {
    var w = canvas.parentElement.clientWidth - 20; canvas.width = w; canvas.height = 200;
    var ctx = canvas.getContext('2d'); var data = history.slice(-30);
    var highs = data.map(function(d) { return parseFloat(d.high) || 0; }).filter(function(v) { return v > 0; });
    var lows = data.map(function(d) { return parseFloat(d.low) || 0; }).filter(function(v) { return v > 0; });
    if (highs.length === 0) return;
    var max = Math.max.apply(null, highs) * 1.02; var min = Math.min.apply(null, lows) * 0.98;
    var range = max - min || 1; var pad = { top: 22, bottom: 26, left: 48, right: 8 };
    var plotW = w - pad.left - pad.right; var plotH = canvas.height - pad.top - pad.bottom;
    var barW = Math.max(3, Math.min(10, plotW / data.length * 0.7)); var gap = plotW / data.length;
    ctx.fillStyle = 'rgba(255,255,255,0.02)'; ctx.fillRect(pad.left, pad.top, plotW, plotH);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 0.5; ctx.setLineDash([4, 6]);
    for (var i = 0; i <= 4; i++) { var y = pad.top + (plotH / 4) * i; ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + plotW, y); ctx.stroke(); }
    ctx.setLineDash([]);
    ctx.fillStyle = '#666'; ctx.font = '10px sans-serif';
    for (var i = 0; i <= 4; i++) { var val = max - (range / 4) * i; var y = pad.top + (plotH / 4) * i; ctx.fillText(val.toFixed(2), 2, y + 3); }
    data.forEach(function(d, i) {
        var o = parseFloat(d.open) || 0, c = parseFloat(d.close) || 0, h = parseFloat(d.high) || 0, l = parseFloat(d.low) || 0;
        if (!o || !c) return; var x = pad.left + i * gap + (gap - barW) / 2;
        var yO = pad.top + (max - o) / range * plotH, yC = pad.top + (max - c) / range * plotH;
        var yH = pad.top + (max - h) / range * plotH, yL = pad.top + (max - l) / range * plotH;
        var isUp = c >= o;
        ctx.strokeStyle = isUp ? '#00D4AA' : '#FF4757'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x + barW/2, yH); ctx.lineTo(x + barW/2, yL); ctx.stroke();
        var bodyH = Math.max(1, Math.abs(yC - yO));
        var grad = ctx.createLinearGradient(x, Math.min(yO, yC), x, Math.min(yO, yC) + bodyH);
        if (isUp) { grad.addColorStop(0, '#00D4AA'); grad.addColorStop(1, 'rgba(0,212,170,0.6)'); }
        else { grad.addColorStop(0, '#FF4757'); grad.addColorStop(1, 'rgba(255,71,87,0.6)'); }
        ctx.fillStyle = grad;
        var rx = Math.min(barW/2, 3), ry = Math.min(bodyH/2, 3); var xb = Math.floor(x), yb = Math.floor(Math.min(yO, yC)); var bw = Math.ceil(barW), bh = Math.ceil(bodyH);
        ctx.beginPath(); ctx.moveTo(xb + rx, yb); ctx.lineTo(xb + bw - rx, yb); ctx.quadraticCurveTo(xb + bw, yb, xb + bw, yb + ry);
        ctx.lineTo(xb + bw, yb + bh - ry); ctx.quadraticCurveTo(xb + bw, yb + bh, xb + bw - rx, yb + bh);
        ctx.lineTo(xb + rx, yb + bh); ctx.quadraticCurveTo(xb, yb + bh, xb, yb + bh - ry); ctx.lineTo(xb, yb + ry); ctx.quadraticCurveTo(xb, yb, xb + rx, yb);
        ctx.fill();
    });
    ctx.fillStyle = '#666'; ctx.font = '9px sans-serif';
    var maxLabels = Math.floor(plotW / 50); var skip = Math.max(1, Math.ceil(data.length / maxLabels));
    for (var j = 0; j < data.length; j += skip) { ctx.fillText((data[j].date || '').slice(5), pad.left + j * gap - 10, canvas.height - 4); }
}

function drawSimpleBar(canvas, stock) {
    var w = canvas.parentElement.clientWidth - 20; canvas.width = w; canvas.height = 200; var ctx = canvas.getContext('2d');
    var price = parseFloat(stock.price) || 0, open = parseFloat(stock.open) || price, high = parseFloat(stock.high) || price * 1.02, low = parseFloat(stock.low) || price * 0.98;
    var all = [open, price, high, low].filter(function(v) { return v > 0; });
    var max = Math.max.apply(null, all) * 1.02, min = Math.min.apply(null, all) * 0.98, range = max - min || 1;
    var pad = { top: 20, bottom: 10, left: 48, right: 8 }, plotH = canvas.height - pad.top - pad.bottom; var barX = pad.left + 40, barW = 30;
    ctx.fillStyle = 'rgba(255,255,255,0.02)'; ctx.fillRect(pad.left, pad.top, w - pad.left - pad.right, plotH);
    function toY(v) { return pad.top + (max - v) / range * plotH; }
    ctx.strokeStyle = '#666'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(barX + barW/2, toY(high)); ctx.lineTo(barX + barW/2, toY(low)); ctx.stroke();
    var isUp = price >= open; var grad = ctx.createLinearGradient(barX, Math.min(toY(open), toY(price)), barX, Math.max(toY(open), toY(price)));
    if (isUp) { grad.addColorStop(0, '#00D4AA'); grad.addColorStop(1, 'rgba(0,212,170,0.5)'); } else { grad.addColorStop(0, '#FF4757'); grad.addColorStop(1, 'rgba(255,71,87,0.5)'); }
    ctx.fillStyle = grad; var bh = Math.max(1, Math.abs(toY(price) - toY(open))); var r = Math.min(barW/2, 3);
    ctx.beginPath(); ctx.moveTo(barX + r, Math.min(toY(open), toY(price))); ctx.lineTo(barX + barW - r, Math.min(toY(open), toY(price)));
    ctx.quadraticCurveTo(barX + barW, Math.min(toY(open), toY(price)), barX + barW, Math.min(toY(open), toY(price)) + r);
    ctx.lineTo(barX + barW, Math.min(toY(open), toY(price)) + bh - r);
    ctx.quadraticCurveTo(barX + barW, Math.min(toY(open), toY(price)) + bh, barX + barW - r, Math.min(toY(open), toY(price)) + bh);
    ctx.lineTo(barX + r, Math.min(toY(open), toY(price)) + bh);
    ctx.quadraticCurveTo(barX, Math.min(toY(open), toY(price)) + bh, barX, Math.min(toY(open), toY(price)) + bh - r);
    ctx.lineTo(barX, Math.min(toY(open), toY(price)) + r);
    ctx.quadraticCurveTo(barX, Math.min(toY(open), toY(price)), barX + r, Math.min(toY(open), toY(price)));
    ctx.fill();
    ctx.fillStyle = '#666'; ctx.font = '10px sans-serif';
    ctx.fillText('H:' + high.toFixed(2), barX + barW + 8, toY(high) + 4); ctx.fillText('L:' + low.toFixed(2), barX + barW + 8, toY(low) + 4);
    ctx.fillText('O:' + open.toFixed(2), barX - 42, toY(open) + 4); ctx.fillText('C:' + price.toFixed(2), barX - 42, toY(price) + 4);
}

// ========== Share / Memory / Search / Tabs ==========
function shareAnalysis() {
    if (!currentStockData) return; var s = currentStockData.stock; var a = currentStockData.analysis;
    var shareCode = s.code || s.symbol || '';
    var text = '\uD83D\uDCC8 ' + s.name + '(' + shareCode + ')\n\n\uD83E\uDD16 公开信息摘要:\n' + (a || '').slice(0, 200) + '\n\n仅基于公开信息整理，不构成投资建议。';
    if (navigator.clipboard) { navigator.clipboard.writeText(text).then(function() { showToast('已复制分享文本'); }); } else showToast('请手动复制');
}
function toggleMemory() {
    var panel = document.getElementById('memoryPanel');
    if (panel.style.display === 'none' || !panel.style.display) { panel.style.display = 'block'; loadMemory(); } else panel.style.display = 'none';
}
function loadMemory() {
    var el = document.getElementById('memoryContent'); el.innerHTML = '<span style="color:var(--text-muted)">加载中...</span>';
    fetch('/api/user/memory?user_id=' + userId).then(function(r) { return r.json(); }).then(function(data) {
        if (!data.queries || !data.queries.length) { el.innerHTML = '<span style="color:var(--text-muted)">暂无记录</span>'; return; }
        var html = ''; data.queries.slice(-10).reverse().forEach(function(q) {
            var vCls = q.verdict === '\u5173\u6ce8' ? 'up' : q.verdict === '\u8b66\u60d5' ? 'down' : '';
            html += '<div class="memory-item"><span class="memory-date">' + escHtml(q.date || '') + '</span><span class="memory-symbol">' + escHtml(q.symbol) + '</span><span class="memory-verdict ' + vCls + '">' + escHtml(q.verdict || '') + '</span><span class="memory-summary">' + escHtml((q.summary || '').slice(0, 50)) + '</span></div>';
        }); el.innerHTML = html;
    }).catch(function() { el.innerHTML = '<span style="color:var(--down)">加载失败</span>'; });
}
function setupSearch() {
    var input = document.getElementById('searchInput'), results = document.getElementById('searchResults'), timeout;
    input.addEventListener('input', function() { clearTimeout(timeout); var q = input.value.trim(); if (q.length < 1) { results.classList.remove('show'); return; } timeout = setTimeout(function() { searchStocks(q, results); }, 300); });
    document.addEventListener('click', function(e) { if (!e.target.closest('.search-box')) results.classList.remove('show'); });
}
function searchStocks(q, resultsEl) {
    resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--text-muted)">搜索中...</div>'; resultsEl.classList.add('show');
    fetch('/api/search?q=' + encodeURIComponent(q)).then(function(r) { return r.json(); }).then(function(data) {
        if (!data.results || !data.results.length) {
            var examples = (data.examples && data.examples.length) ? data.examples.join('、') : '600519、贵州茅台、NVDA、英伟达';
            resultsEl.innerHTML = '<div class="search-result-item search-guidance">未找到匹配股票。<br>可试试：' + escHtml(examples) + '</div>';
            return;
        }
        resultsEl.innerHTML = data.results.map(function(s) { return '<div class="search-result-item" data-code="' + escHtml(s.code) + '" role="option"><span class="sr-name">' + escHtml(s.name) + '</span><span class="sr-code">' + escHtml(s.code) + '</span></div>'; }).join('');
        resultsEl.querySelectorAll('.search-result-item').forEach(function(item) { item.addEventListener('click', function() { analyzeStock(item.getAttribute('data-code')); resultsEl.classList.remove('show'); document.getElementById('searchInput').value = ''; }); });
    }).catch(function() { resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--down)">搜索失败</div>'; });
}
function setupTabs() {
    document.querySelectorAll('.tab').forEach(function(tab) { tab.addEventListener('click', function(e) { e.preventDefault(); document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); }); tab.classList.add('active'); tab.setAttribute('aria-selected', 'true'); currentMarket = tab.getAttribute('data-market'); currentSort = tab.getAttribute('data-sort'); loadStocks(); }); });
}
function setupWatchlistDrawer() {
    document.addEventListener('keydown', function(e) { if (e.key === 'Escape') { var drawer = document.getElementById('watchlistDrawer'); if (drawer && drawer.classList.contains('open')) closeWatchlistDrawer(); } });
}

// ========== Payment ==========
function showPay() {
    var modal = document.getElementById('payModal');
    var status = document.getElementById('payStatusText');
    var submit = document.getElementById('btnPaySubmit');
    if (status) status.textContent = '将为当前账号创建月卡订单，支付成功后自动刷新完整报告。本工具仅整理公开信息，不构成投资建议。';
    if (submit) { submit.disabled = false; submit.textContent = '解锁完整报告'; }
    if (modal) modal.style.display = 'flex';
}
window.showPay = showPay;
function closePay() {
    var modal = document.getElementById('payModal');
    if (modal) modal.style.display = 'none';
    if (payCheckTimer) { clearInterval(payCheckTimer); payCheckTimer = null; }
}

function createReportOrder() {
    var submit = document.getElementById('btnPaySubmit');
    var status = document.getElementById('payStatusText');
    var qrBox = document.getElementById('payQrBox');
    if (!currentStockData) {
        showToast('请先生成报告预览');
        return;
    }
    if (submit) { submit.disabled = true; submit.textContent = '正在创建订单...'; }
    if (status) status.textContent = '正在创建订单，请稍候。';
    fetch('/api/create_order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            plan_id: 'monthly',
            pay_type: 'wxpay',
            user_id: userId
        })
    }).then(function(r) { return r.json(); }).then(function(data) {
        if (!data.success) throw new Error(data.error || '创建订单失败');
        currentPayOrder = data.order_no;
        if (qrBox) {
            qrBox.innerHTML =
                '<img src="' + escHtml(data.qr_code || '') + '" alt="支付二维码" style="width:160px;height:160px;border-radius:8px;background:#fff;padding:8px;">' +
                '<p>订单号：' + escHtml(data.order_no) + '</p>' +
                '<p>金额：¥' + escHtml(data.amount) + '</p>';
        }
        if (status) status.textContent = '订单已创建。支付成功后页面会自动刷新完整报告。';
        if (submit) submit.textContent = '等待支付完成';
        startOrderPolling(data.order_no);
    }).catch(function(err) {
        if (submit) { submit.disabled = false; submit.textContent = '解锁完整报告'; }
        if (status) status.textContent = '创建订单失败，请稍后重试。' + (err && err.message ? err.message : '');
    });
}

function startOrderPolling(orderNo) {
    if (payCheckTimer) clearInterval(payCheckTimer);
    payCheckTimer = setInterval(function() {
        fetch('/api/check_order/' + encodeURIComponent(orderNo))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success && data.order && data.order.status === 'PAID') {
                    clearInterval(payCheckTimer);
                    payCheckTimer = null;
                    closePay();
                    showToast('支付已确认，正在刷新完整报告');
                    var stock = currentStockData && currentStockData.stock ? (currentStockData.stock.code || currentStockData.stock.symbol) : '';
                    if (stock) analyzeStock(stock, null, true);
                }
            })
            .catch(function() {});
    }, 3000);
}

// ========== Toast ==========
function showToast(msg) { var t = document.getElementById('toast'); t.textContent = msg; t.className = 'toast show'; setTimeout(function() { t.classList.remove('show'); }, 2500); }
function showUndoToast(msg, undoFn) {
    var t = document.getElementById('toast'); t.innerHTML = msg + '<span class="undo-link">撤销</span>'; t.className = 'toast show undo-toast';
    var undoLink = t.querySelector('.undo-link'); var timer = setTimeout(function() { t.classList.remove('show'); t.className = 'toast'; }, 4000);
    if (undoLink) undoLink.addEventListener('click', function() { clearTimeout(timer); if (undoFn) undoFn(); t.classList.remove('show'); t.className = 'toast'; t.textContent = ''; });
}

// ========== Util ==========
function escHtml(s) { if (s === null || s === undefined) return ''; return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
})();
