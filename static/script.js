var currentMarket = 'a';
var currentSort = 'amount';
var watchlist = loadWatchlist();
var currentStockData = null;

document.addEventListener('DOMContentLoaded', function() {
    loadStocks();
    loadBriefing();
    setupSearch();
    setupTabs();
    renderWatchlistBar();
});

// ========== Watchlist (localStorage) ==========
function loadWatchlist() {
    try { return JSON.parse(localStorage.getItem('stockWatchlist') || '[]'); }
    catch(e) { return []; }
}
function saveWatchlist() { localStorage.setItem('stockWatchlist', JSON.stringify(watchlist)); }
function toggleWatchlistStar(code, name, btn) {
    var idx = watchlist.findIndex(function(w) { return w.code === code; });
    if (idx >= 0) {
        watchlist.splice(idx, 1);
        if (btn) { btn.classList.remove('starred'); btn.textContent = '☆'; }
    } else {
        if (watchlist.length >= 20) { showToast('自选股最多20只'); return; }
        watchlist.push({code: code, name: name});
        if (btn) { btn.classList.add('starred'); btn.textContent = '★'; }
    }
    saveWatchlist();
    renderWatchlistBar();
}
function isStarred(code) { return watchlist.some(function(w) { return w.code === code; }); }

function toggleWatchlist() {
    var bar = document.getElementById('watchlistBar');
    bar.style.display = bar.style.display === 'none' ? 'block' : 'none';
    renderWatchlistBar();
}
function renderWatchlistBar() {
    var el = document.getElementById('watchlistItems');
    var count = document.getElementById('watchlistCount');
    count.textContent = watchlist.length;
    if (watchlist.length === 0) {
        el.innerHTML = '<span class="empty-hint">点击股票行的 ☆ 添加自选</span>';
        return;
    }
    el.innerHTML = watchlist.map(function(w) {
        return '<span class="watchlist-tag" data-code="' + w.code + '" onclick="analyzeStock(\'' + w.code + '\')">' +
            escHtml(w.name) + ' <span class="remove" onclick="event.stopPropagation();removeFromWatchlist(\'' + w.code + '\')">×</span></span>';
    }).join('');
}
function removeFromWatchlist(code) {
    watchlist = watchlist.filter(function(w) { return w.code !== code; });
    saveWatchlist();
    renderWatchlistBar();
    loadStocks();
}

// ========== Stock List ==========
function loadStocks() {
    var tbody = document.getElementById('stockTableBody');
    var statusEl = document.getElementById('marketStatus');
    tbody.innerHTML = '<tr><td colspan="9" class="loading-row">加载中...</td></tr>';
    statusEl.innerHTML = '<span class="status-dot"></span><span class="status-text">加载中...</span>';

    fetch('/api/stocks?market=' + currentMarket + '&sort=' + currentSort)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) { throw new Error(data.error); }
            if (!data.stocks || data.stocks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="loading-row">暂无数据，可能是非交易时段</td></tr>';
                statusEl.innerHTML = '<span class="status-dot closed"></span><span class="status-text">休市中</span>';
                return;
            }
            statusEl.innerHTML = '<span class="status-dot open"></span><span class="status-text">数据已更新</span>';
            
            var rows = '';
            data.stocks.forEach(function(s, i) {
                var change = parseFloat(s.change_pct) || 0;
                var cls = change > 0 ? 'up' : change < 0 ? 'down' : '';
                var sign = change > 0 ? '+' : '';
                var starred = isStarred(s.code);
                var starIcon = starred ? '★' : '☆';
                var starCls = starred ? 'starred' : '';

                rows += '<tr class="stock-row" data-code="' + s.code + '">' +
                    '<td class="col-wl"><button class="btn-star ' + starCls + '" data-code="' + s.code + '" data-name="' + escHtml(s.name) + '">' + starIcon + '</button></td>' +
                    '<td class="col-rank">' + (i + 1) + '</td>' +
                    '<td class="col-name"><span class="stock-name">' + escHtml(s.name) + '</span><span class="stock-code">' + s.code + '</span></td>' +
                    '<td class="col-price">' + (s.price || '-') + '</td>' +
                    '<td class="col-change ' + cls + '">' + sign + (s.change_pct || '-') + '%</td>' +
                    '<td class="col-change hide-mobile">' + (s.amount || '-') + '</td>' +
                    '<td class="col-change hide-mobile">' + (s.turnover_rate || '-') + '%</td>' +
                    '<td class="col-change hide-mobile">' + (s.pe || '-') + '</td>' +
                    '<td class="col-action"><button class="btn-analyze" data-code="' + s.code + '">AI分析</button></td>' +
                    '</tr>';
            });
            tbody.innerHTML = rows;

            // Star buttons
            document.querySelectorAll('.btn-star').forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    toggleWatchlistStar(btn.getAttribute('data-code'), btn.getAttribute('data-name'), btn);
                });
            });
            // Analyze buttons
            document.querySelectorAll('.btn-analyze').forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    analyzeStock(btn.getAttribute('data-code'));
                });
            });
            // Row click
            document.querySelectorAll('.stock-row').forEach(function(row) {
                row.addEventListener('click', function() { analyzeStock(row.getAttribute('data-code')); });
            });
        })
        .catch(function(err) {
            tbody.innerHTML = '<tr><td colspan="9" class="loading-row">数据加载失败，<a href="#" onclick="loadStocks()" style="color:var(--accent)">点击重试</a></td></tr>';
            statusEl.innerHTML = '<span class="status-dot error"></span><span class="status-text">连接失败，请重试</span>';
        });
}

// ========== Briefing ==========
function loadBriefing() {
    var el = document.getElementById('briefingContent');
    fetch('/api/briefing')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.briefing) { el.innerHTML = data.briefing.replace(/\n/g, '<br>'); }
            else { el.innerHTML = '市场简报生成中...'; }
        })
        .catch(function() { el.innerHTML = '简报暂不可用'; });
}

// ========== AI Analysis + K-line ==========
function analyzeStock(code) {
    var card = document.getElementById('analysisCard');
    var nameEl = document.getElementById('analysisStockName');
    var infoEl = document.getElementById('stockQuickInfo');
    var bodyEl = document.getElementById('analysisBody');
    var chartCanvas = document.getElementById('klineChart');
    var shareBtn = document.getElementById('btnShare');

    card.style.display = 'block';
    nameEl.textContent = '分析中...';
    infoEl.innerHTML = '';
    bodyEl.innerHTML = '<span class="loading-text">AI正在深度分析，约需5秒...</span>';
    shareBtn.style.display = 'none';
    
    // Clear chart
    var ctx = chartCanvas.getContext('2d');
    ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);

    fetch('/api/analyze?code=' + code)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                bodyEl.innerHTML = '<span style="color:var(--down)">' + escHtml(data.error) + '</span>';
                return;
            }
            currentStockData = data;
            var s = data.stock;
            nameEl.textContent = s.name + ' (' + s.code + ')';

            var change = parseFloat(s.change_pct) || 0;
            var cCls = change > 0 ? 'up' : change < 0 ? 'down' : '';
            var sign = change > 0 ? '+' : '';

            infoEl.innerHTML =
                '<div class="quick-stats">' +
                '<span class="stat">价格 <strong>' + (s.price || '-') + '</strong></span>' +
                '<span class="stat ' + cCls + '">涨跌 <strong>' + sign + (s.change_pct || '-') + '%</strong></span>' +
                '<span class="stat">成交 <strong>' + (s.amount || '-') + '</strong></span>' +
                '<span class="stat">PE <strong>' + (s.pe || '-') + '</strong></span>' +
                '</div>';

            bodyEl.innerHTML = data.analysis.replace(/\n/g, '<br>');
            shareBtn.style.display = 'block';

            // Draw K-line if history available
            if (data.history && data.history.length >= 3) {
                drawKline(chartCanvas, data.history);
            } else if (data.stock) {
                // Draw simple price bar from available data
                drawSimpleBar(chartCanvas, s);
            }

            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        })
        .catch(function() {
            bodyEl.innerHTML = '<span style="color:var(--down)">分析失败，请重试</span>';
        });
}

function drawKline(canvas, history) {
    var w = canvas.parentElement.clientWidth - 16;
    canvas.width = w;
    canvas.height = 180;
    var ctx = canvas.getContext('2d');
    var data = history.slice(-30);

    var highs = data.map(function(d) { return parseFloat(d.high) || 0; }).filter(function(v) { return v > 0; });
    var lows = data.map(function(d) { return parseFloat(d.low) || 0; }).filter(function(v) { return v > 0; });
    if (highs.length === 0) return;

    var max = Math.max.apply(null, highs) * 1.02;
    var min = Math.min.apply(null, lows) * 0.98;
    var range = max - min || 1;
    var padding = { top: 20, bottom: 25, left: 50, right: 10 };
    var plotW = w - padding.left - padding.right;
    var plotH = canvas.height - padding.top - padding.bottom;
    var barWidth = Math.max(2, Math.min(8, plotW / data.length * 0.7));
    var gap = plotW / data.length;

    // Background
    ctx.fillStyle = 'rgba(0,0,0,0.2)';
    ctx.fillRect(padding.left, padding.top, plotW, plotH);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 0.5;
    for (var i = 0; i <= 4; i++) {
        var y = padding.top + (plotH / 4) * i;
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(padding.left + plotW, y); ctx.stroke();
        var val = max - (range / 4) * i;
        ctx.fillStyle = '#8b949e'; ctx.font = '10px sans-serif';
        ctx.fillText(val.toFixed(2), 4, y + 3);
    }

    // Candles
    data.forEach(function(d, i) {
        var o = parseFloat(d.open) || 0;
        var c = parseFloat(d.close) || 0;
        var h = parseFloat(d.high) || 0;
        var l = parseFloat(d.low) || 0;
        if (o === 0 || c === 0) return;

        var x = padding.left + i * gap + (gap - barWidth) / 2;
        var yOpen = padding.top + (max - o) / range * plotH;
        var yClose = padding.top + (max - c) / range * plotH;
        var yHigh = padding.top + (max - h) / range * plotH;
        var yLow = padding.top + (max - l) / range * plotH;

        var isUp = c >= o;
        ctx.fillStyle = isUp ? '#3fb950' : '#f85149';
        ctx.strokeStyle = isUp ? '#3fb950' : '#f85149';

        // Wick
        ctx.beginPath(); ctx.moveTo(x + barWidth/2, yHigh); ctx.lineTo(x + barWidth/2, yLow); ctx.stroke();
        // Body
        var bodyH = Math.max(1, Math.abs(yClose - yOpen));
        ctx.fillRect(x, Math.min(yOpen, yClose), barWidth, bodyH);
    });

    // X-axis dates
    ctx.fillStyle = '#8b949e';
    ctx.font = '9px sans-serif';
    var step = Math.max(1, Math.floor(data.length / 4));
    for (var j = 0; j < data.length; j += step) {
        var date = (data[j].date || '').slice(5);
        ctx.fillText(date, padding.left + j * gap + (gap - barWidth) / 2 - 8, canvas.height - 4);
    }
}

function drawSimpleBar(canvas, stock) {
    var w = canvas.parentElement.clientWidth - 16;
    canvas.width = w;
    canvas.height = 180;
    var ctx = canvas.getContext('2d');

    // Draw a simple price bar
    var price = parseFloat(stock.price) || 0;
    var open = parseFloat(stock.open) || price;
    var high = parseFloat(stock.high) || price * 1.02;
    var low = parseFloat(stock.low) || price * 0.98;
    var prevClose = parseFloat(stock.prev_close) || price;

    var allVals = [open, price, high, low, prevClose].filter(function(v) { return v > 0; });
    var max = Math.max.apply(null, allVals) * 1.02;
    var min = Math.min.apply(null, allVals) * 0.98;
    var range = max - min || 1;

    var padding = { top: 20, bottom: 10, left: 50, right: 10 };
    var plotH = canvas.height - padding.top - padding.bottom;
    var barX = padding.left + 40;
    var barW = 30;

    ctx.fillStyle = 'rgba(0,0,0,0.2)';
    ctx.fillRect(padding.left, padding.top, canvas.width - padding.left - padding.right, plotH);

    // Price labels
    ctx.fillStyle = '#8b949e'; ctx.font = '10px sans-serif';
    for (var i = 0; i <= 3; i++) {
        var y = padding.top + (plotH / 3) * i;
        var val = max - (range / 3) * i;
        ctx.fillText(val.toFixed(2), 4, y + 3);
    }

    function toY(v) { return padding.top + (max - v) / range * plotH; }

    // High-low line
    ctx.strokeStyle = '#8b949e'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(barX + barW/2, toY(high)); ctx.lineTo(barX + barW/2, toY(low)); ctx.stroke();

    // Candle body
    var isUp = price >= open;
    ctx.fillStyle = isUp ? '#3fb950' : '#f85149';
    ctx.fillRect(barX, Math.min(toY(open), toY(price)), barW, Math.max(1, Math.abs(toY(price) - toY(open))));

    // Labels
    ctx.fillStyle = '#8b949e'; ctx.font = '10px sans-serif';
    ctx.fillText('H:' + high.toFixed(2), barX + barW + 8, toY(high) + 4);
    ctx.fillText('L:' + low.toFixed(2), barX + barW + 8, toY(low) + 4);
    ctx.fillText('O:' + open.toFixed(2), barX - 38, toY(open) + 4);
    ctx.fillText('C:' + price.toFixed(2), barX - 38, toY(price) + 4);

    ctx.fillStyle = '#8b949e'; ctx.font = '9px sans-serif';
    ctx.fillText('日K', padding.left + 5, padding.top - 2);
}

function closeAnalysis() {
    document.getElementById('analysisCard').style.display = 'none';
    currentStockData = null;
}

function shareAnalysis() {
    if (!currentStockData) return;
    // Generate share text
    var s = currentStockData.stock;
    var analysis = currentStockData.analysis;
    var text = '📈 ' + s.name + '(' + s.code + ')\n' +
        '价格:' + s.price + ' 涨跌:' + (s.change_pct || '-') + '%\n\n' +
        '🤖 AI分析:\n' + analysis.slice(0, 200) + '\n\n' +
        '免费测你的股票 → [链接]';
    
    // Copy to clipboard
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('已复制分享文案，可粘贴到小红书/微信');
        });
    } else {
        showToast('分享文案已生成，请手动复制');
    }
}

// ========== Search ==========
function setupSearch() {
    var input = document.getElementById('searchInput');
    var results = document.getElementById('searchResults');
    var timeout;

    input.addEventListener('input', function() {
        clearTimeout(timeout);
        var q = input.value.trim();
        if (q.length < 1) { results.classList.remove('show'); return; }
        timeout = setTimeout(function() { searchStocks(q, results); }, 300);
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-box')) { results.classList.remove('show'); }
    });
}

function searchStocks(q, resultsEl) {
    resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--text-muted)">搜索中...</div>';
    resultsEl.classList.add('show');

    fetch('/api/search?q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.results || data.results.length === 0) {
                resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--text-muted)">未找到匹配股票</div>';
                return;
            }
            var html = '';
            data.results.forEach(function(s) {
                html += '<div class="search-result-item" data-code="' + s.code + '">' +
                    '<span class="sr-name">' + escHtml(s.name) + '</span>' +
                    '<span class="sr-code">' + s.code + '</span></div>';
            });
            resultsEl.innerHTML = html;
            resultsEl.querySelectorAll('.search-result-item').forEach(function(item) {
                item.addEventListener('click', function() {
                    analyzeStock(item.getAttribute('data-code'));
                    resultsEl.classList.remove('show');
                    document.getElementById('searchInput').value = '';
                });
            });
        })
        .catch(function() {
            resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--down)">搜索失败</div>';
        });
}

// ========== Tabs ==========
function setupTabs() {
    document.querySelectorAll('.tab').forEach(function(tab) {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
            tab.classList.add('active');
            currentMarket = tab.getAttribute('data-market');
            currentSort = tab.getAttribute('data-sort');
            loadStocks();
        });
    });
}

// ========== Payment ==========
function showPay() { document.getElementById('payModal').style.display = 'flex'; }
function closePay() { document.getElementById('payModal').style.display = 'none'; }

// ========== Toast ==========
function showToast(msg) {
    var toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(function() { toast.classList.remove('show'); }, 2500);
}

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}