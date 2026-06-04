(function() {
"use strict";

var currentMarket = 'a';
var currentSort = 'amount';
var watchlist = loadWatchlist();
var currentStockData = null;
var userId = localStorage.getItem('guxiaozhi_user_id') || '';
if (!userId) {
    userId = 'user_' + crypto.randomUUID().slice(0, 8);
    localStorage.setItem('guxiaozhi_user_id', userId);
}

document.addEventListener('DOMContentLoaded', function() {
    loadStocks();
    loadBriefing();
    setupSearch();
    setupTabs();
    renderWatchlistBar();
    bindGlobalButtons();
});

// ========== Global Button Bindings (replace inline onclick) ==========
function bindGlobalButtons() {
    var btnWatchlist = document.getElementById('btnWatchlist');
    if (btnWatchlist) btnWatchlist.addEventListener('click', toggleWatchlist);

    var btnCloseWatchlist = document.getElementById('btnCloseWatchlist');
    if (btnCloseWatchlist) btnCloseWatchlist.addEventListener('click', toggleWatchlist);

    var btnCloseAnalysis = document.getElementById('btnCloseAnalysis');
    if (btnCloseAnalysis) btnCloseAnalysis.addEventListener('click', closeAnalysis);

    var btnShare = document.getElementById('btnShare');
    if (btnShare) btnShare.addEventListener('click', shareAnalysis);

    var btnMemory = document.getElementById('btnMemory');
    if (btnMemory) btnMemory.addEventListener('click', toggleMemory);

    var btnPremium = document.getElementById('btnPremium');
    if (btnPremium) btnPremium.addEventListener('click', showPay);

    var btnClosePay = document.getElementById('btnClosePay');
    if (btnClosePay) btnClosePay.addEventListener('click', closePay);
}

// ========== Watchlist ==========
function loadWatchlist() { try { return JSON.parse(localStorage.getItem('stockWatchlist') || '[]'); } catch(e) { return []; } }
function saveWatchlist() { localStorage.setItem('stockWatchlist', JSON.stringify(watchlist)); }
function toggleWatchlistStar(code, name, btn) {
    var idx = watchlist.findIndex(function(w) { return w.code === code; });
    if (idx >= 0) { watchlist.splice(idx, 1); if (btn) { btn.classList.remove('starred'); btn.textContent = '\u2606'; } }
    else {
        if (watchlist.length >= 20) { showToast('最多20只'); return; }
        watchlist.push({code: code, name: name});
        if (btn) { btn.classList.add('starred'); btn.textContent = '\u2605'; }
    }
    saveWatchlist(); renderWatchlistBar();
}
function isStarred(code) { return watchlist.some(function(w) { return w.code === code; }); }
function toggleWatchlist() { var bar = document.getElementById('watchlistBar'); bar.style.display = bar.style.display === 'none' ? 'block' : 'none'; renderWatchlistBar(); }
function renderWatchlistBar() {
    var el = document.getElementById('watchlistItems'); var cnt = document.getElementById('watchlistCount'); cnt.textContent = watchlist.length;
    if (watchlist.length === 0) { el.innerHTML = '<span class="empty-hint">点击股票行的 ☆ 添加自选</span>'; return; }
    el.innerHTML = watchlist.map(function(w) {
        return '<span class="watchlist-tag" data-code="' + escHtml(w.code) + '"><span class="tag-name" data-code="' + escHtml(w.code) + '">' + escHtml(w.name) + '</span> <span class="remove" data-code="' + escHtml(w.code) + '">\u00d7</span></span>';
    }).join('');
    el.querySelectorAll('.tag-name').forEach(function(span) {
        span.addEventListener('click', function() { analyzeStock(span.getAttribute('data-code')); });
    });
    el.querySelectorAll('.remove').forEach(function(span) {
        span.addEventListener('click', function(e) { e.stopPropagation(); removeFromWatchlist(span.getAttribute('data-code')); });
    });
}
function removeFromWatchlist(code) { watchlist = watchlist.filter(function(w) { return w.code !== code; }); saveWatchlist(); renderWatchlistBar(); loadStocks(); }

// ========== Stock List ==========
function loadStocks() {
    var tbody = document.getElementById('stockTableBody'); var st = document.getElementById('marketStatus');
    tbody.innerHTML = '<tr><td colspan="8" class="loading-row">加载中...</td></tr>';
    st.innerHTML = '<span class="status-dot"></span><span class="status-text">加载中...</span>';

    fetch('/api/stocks?market=' + currentMarket + '&sort=' + currentSort)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) throw new Error(data.error);
            if (!data.stocks || data.stocks.length === 0) {
                var msg = currentMarket === 'us' ? '数据暂不可用' : '暂无数据';
                var statusIcon = currentMarket === 'us' ? 'closed' : 'closed';
                tbody.innerHTML = '<tr><td colspan="8" class="loading-row">' + escHtml(msg) + '</td></tr>';
                st.innerHTML = '<span class="status-dot ' + statusIcon + '"></span><span class="status-text">休市中</span>'; return;
            }
            st.innerHTML = '<span class="status-dot open"></span><span class="status-text">实时数据</span>';
            var rows = '';
            data.stocks.forEach(function(s, i) {
                var chg = parseFloat(s.change_pct) || 0; var cls = chg > 0 ? 'up' : chg < 0 ? 'down' : '';
                var sign = chg > 0 ? '+' : ''; var starred = isStarred(s.code);
                rows += '<tr class="stock-row" data-code="' + escHtml(s.code) + '">' +
                    '<td class="col-wl"><button class="btn-star ' + (starred ? 'starred' : '') + '" data-code="' + escHtml(s.code) + '" data-name="' + escHtml(s.name) + '">' + (starred ? '\u2605' : '\u2606') + '</button></td>' +
                    '<td class="col-rank">' + (i + 1) + '</td>' +
                    '<td class="col-name"><span class="stock-name">' + escHtml(s.name) + '</span><span class="stock-code">' + escHtml(s.code) + '</span></td>' +
                    '<td class="col-price">' + escHtml(s.price || '-') + '</td>' +
                    '<td class="col-change ' + cls + '">' + sign + escHtml(s.change_pct || '-') + '%</td>' +
                    '<td class="col-change hide-mobile">' + escHtml(s.amount || '-') + '</td>' +
                    '<td class="col-change hide-mobile">' + escHtml(s.pe || '-') + '</td>' +
                    '<td class="col-action"><button class="btn-analyze" data-code="' + escHtml(s.code) + '">AI分析</button></td></tr>';
            });
            tbody.innerHTML = rows;
            document.querySelectorAll('.btn-star').forEach(function(b) { b.addEventListener('click', function(e) { e.stopPropagation(); toggleWatchlistStar(b.getAttribute('data-code'), b.getAttribute('data-name'), b); }); });
            document.querySelectorAll('.btn-analyze').forEach(function(b) { b.addEventListener('click', function(e) { e.stopPropagation(); analyzeStock(b.getAttribute('data-code'), b); }); });
            document.querySelectorAll('.stock-row').forEach(function(r) { r.addEventListener('click', function() { analyzeStock(r.getAttribute('data-code')); }); });
        })
        .catch(function() { tbody.innerHTML = '<tr><td colspan="8" class="loading-row">加载失败，<a href="#" id="retryLink" style="color:var(--accent)">重试</a></td></tr>'; st.innerHTML = '<span class="status-dot error"></span><span class="status-text">连接失败</span>'; var rl = document.getElementById('retryLink'); if (rl) rl.addEventListener('click', function(e) { e.preventDefault(); loadStocks(); }); });
}

// ========== Briefing ==========
function loadBriefing() {
    var el = document.getElementById('briefingContent');
    fetch('/api/briefing').then(function(r) { return r.json(); }).then(function(d) {
        el.innerHTML = d.briefing ? escHtml(d.briefing).replace(/\n/g, '<br>') : '简报生成中...';
    }).catch(function() { el.innerHTML = '简报暂不可用'; });
}

// ========== AI Analysis ==========
function analyzeStock(code, btnEl) {
    var card = document.getElementById('analysisCard'); var nameEl = document.getElementById('analysisStockName');
    var infoEl = document.getElementById('stockQuickInfo'); var bodyEl = document.getElementById('analysisBody');
    var chartCanvas = document.getElementById('klineChart'); var shareBtn = document.getElementById('btnShare');
    var verdictBadge = document.getElementById('analysisVerdictBadge');

    card.style.display = 'block'; nameEl.textContent = '分析中...'; infoEl.innerHTML = '';
    bodyEl.innerHTML = '<span style="color:var(--text-muted)">AI正在深度分析，约需5秒...</span>';
    shareBtn.style.display = 'none'; verdictBadge.style.display = 'none';

    // Loading animation on the triggering button
    var triggerBtn = btnEl || document.querySelector('.btn-analyze[data-code="' + code + '"]');
    if (triggerBtn) { triggerBtn.classList.add('loading'); triggerBtn.textContent = ''; }

    var ctx = chartCanvas.getContext('2d'); ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);

    fetch('/api/analyze?code=' + code + '&user_id=' + userId)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (triggerBtn) { triggerBtn.classList.remove('loading'); triggerBtn.textContent = 'AI分析'; }
            if (data.error) {
                bodyEl.innerHTML = '<div style="color:var(--down);font-weight:600;margin-bottom:4px">⚠️ 分析失败</div><div style="color:var(--text-secondary);font-size:12px">' + escHtml(data.error) + '</div>';
                return;
            }
            currentStockData = data; var s = data.stock;
            nameEl.textContent = s.name + ' (' + s.code + ')';
            var chg = parseFloat(s.change_pct) || 0; var cCls = chg > 0 ? 'up' : chg < 0 ? 'down' : '';
            var sign = chg > 0 ? '+' : '';

            infoEl.innerHTML =
                '<div class="stock-info-item"><span class="info-label">最新价</span><span class="info-value">' + escHtml(s.price || '-') + '</span></div>' +
                '<div class="stock-info-item"><span class="info-label">涨跌幅</span><span class="info-value ' + cCls + '">' + sign + escHtml(s.change_pct || '-') + '%</span></div>' +
                '<div class="stock-info-item"><span class="info-label">成交额</span><span class="info-value">' + escHtml(s.amount || '-') + '</span></div>' +
                '<div class="stock-info-item"><span class="info-label">市盈率</span><span class="info-value">' + escHtml(s.pe || '-') + '</span></div>';

            bodyEl.innerHTML = escHtml(data.analysis || '暂无分析结果').replace(/\n/g, '<br>');
            shareBtn.style.display = 'block';

            var verdict = data.verdict || '';
            if (verdict && verdictBadge) {
                verdictBadge.textContent = verdict; verdictBadge.style.display = 'inline';
                if (verdict === '\u5173\u6ce8') { verdictBadge.style.background = 'rgba(63,185,80,0.15)'; verdictBadge.style.color = '#3fb950'; }
                else if (verdict === '\u8b66\u60d5') { verdictBadge.style.background = 'rgba(248,81,73,0.15)'; verdictBadge.style.color = '#f85149'; }
                else { verdictBadge.style.background = 'rgba(210,153,29,0.12)'; verdictBadge.style.color = '#d2991d'; }
            }

            if (data.history && data.history.length >= 3) drawKline(chartCanvas, data.history);
            else drawSimpleBar(chartCanvas, s);
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        })
        .catch(function() {
            if (triggerBtn) { triggerBtn.classList.remove('loading'); triggerBtn.textContent = 'AI分析'; }
            bodyEl.innerHTML = '<div style="color:var(--down);font-weight:600;margin-bottom:4px">⚠️ 军师离线</div><div style="color:var(--text-secondary);font-size:12px">AI服务暂时不可用，请稍后重试</div>';
        });
}

function closeAnalysis() { document.getElementById('analysisCard').style.display = 'none'; currentStockData = null; }

function drawKline(canvas, history) {
    var w = canvas.parentElement.clientWidth - 20; canvas.width = w; canvas.height = 200;
    var ctx = canvas.getContext('2d'); var data = history.slice(-30);
    var highs = data.map(function(d) { return parseFloat(d.high) || 0; }).filter(function(v) { return v > 0; });
    var lows = data.map(function(d) { return parseFloat(d.low) || 0; }).filter(function(v) { return v > 0; });
    if (highs.length === 0) return;
    var max = Math.max.apply(null, highs) * 1.02; var min = Math.min.apply(null, lows) * 0.98;
    var range = max - min || 1; var pad = { top: 22, bottom: 26, left: 48, right: 8 };
    var plotW = w - pad.left - pad.right; var plotH = canvas.height - pad.top - pad.bottom;
    var barW = Math.max(2, Math.min(8, plotW / data.length * 0.7)); var gap = plotW / data.length;
    ctx.fillStyle = 'rgba(255,255,255,0.02)'; ctx.fillRect(pad.left, pad.top, plotW, plotH);
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 0.5;
    for (var i = 0; i <= 4; i++) { var y = pad.top + (plotH / 4) * i; ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + plotW, y); ctx.stroke(); }
    ctx.fillStyle = '#666'; ctx.font = '10px sans-serif';
    for (var i = 0; i <= 4; i++) { var val = max - (range / 4) * i; var y = pad.top + (plotH / 4) * i; ctx.fillText(val.toFixed(2), 2, y + 3); }
    data.forEach(function(d, i) {
        var o = parseFloat(d.open) || 0, c = parseFloat(d.close) || 0, h = parseFloat(d.high) || 0, l = parseFloat(d.low) || 0;
        if (!o || !c) return;
        var x = pad.left + i * gap + (gap - barW) / 2;
        var yO = pad.top + (max - o) / range * plotH, yC = pad.top + (max - c) / range * plotH;
        var yH = pad.top + (max - h) / range * plotH, yL = pad.top + (max - l) / range * plotH;
        var isUp = c >= o; ctx.fillStyle = isUp ? '#3fb950' : '#f85149'; ctx.strokeStyle = isUp ? '#3fb950' : '#f85149';
        ctx.beginPath(); ctx.moveTo(x + barW/2, yH); ctx.lineTo(x + barW/2, yL); ctx.stroke();
        var bodyH = Math.max(1, Math.abs(yC - yO)); ctx.fillRect(x, Math.min(yO, yC), barW, bodyH);
    });
    ctx.fillStyle = '#666'; ctx.font = '9px sans-serif';
    for (var j = 0; j < data.length; j += Math.max(1, Math.floor(data.length / 4))) { ctx.fillText((data[j].date || '').slice(5), pad.left + j * gap - 10, canvas.height - 4); }
}

function drawSimpleBar(canvas, stock) {
    var w = canvas.parentElement.clientWidth - 20; canvas.width = w; canvas.height = 200;
    var ctx = canvas.getContext('2d');
    var price = parseFloat(stock.price) || 0, open = parseFloat(stock.open) || price;
    var high = parseFloat(stock.high) || price * 1.02, low = parseFloat(stock.low) || price * 0.98;
    var all = [open, price, high, low].filter(function(v) { return v > 0; });
    var max = Math.max.apply(null, all) * 1.02, min = Math.min.apply(null, all) * 0.98, range = max - min || 1;
    var pad = { top: 20, bottom: 10, left: 48, right: 8 }, plotH = canvas.height - pad.top - pad.bottom;
    var barX = pad.left + 40, barW = 30;
    ctx.fillStyle = 'rgba(255,255,255,0.02)'; ctx.fillRect(pad.left, pad.top, w - pad.left - pad.right, plotH);
    function toY(v) { return pad.top + (max - v) / range * plotH; }
    ctx.strokeStyle = '#666'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(barX + barW/2, toY(high)); ctx.lineTo(barX + barW/2, toY(low)); ctx.stroke();
    var isUp = price >= open; ctx.fillStyle = isUp ? '#3fb950' : '#f85149';
    ctx.fillRect(barX, Math.min(toY(open), toY(price)), barW, Math.max(1, Math.abs(toY(price) - toY(open))));
    ctx.fillStyle = '#666'; ctx.font = '10px sans-serif';
    ctx.fillText('H:' + high.toFixed(2), barX + barW + 8, toY(high) + 4);
    ctx.fillText('L:' + low.toFixed(2), barX + barW + 8, toY(low) + 4);
    ctx.fillText('O:' + open.toFixed(2), barX - 42, toY(open) + 4);
    ctx.fillText('C:' + price.toFixed(2), barX - 42, toY(price) + 4);
}

function shareAnalysis() {
    if (!currentStockData) return;
    var s = currentStockData.stock; var a = currentStockData.analysis;
    var text = '\uD83D\uDCC8 ' + s.name + '(' + s.code + ')\n价格:' + s.price + ' 涨跌:' + (s.change_pct || '-') + '%\n\n\uD83E\uDD16 AI分析:\n' + (a || '').slice(0, 200) + '\n\n免费测你的股票 \u2192 https://stock-ai-6plg.onrender.com';
    if (navigator.clipboard) { navigator.clipboard.writeText(text).then(function() { showToast('已复制，可粘贴到小红书/微信'); }); }
    else showToast('请手动复制');
}

// ========== Memory ==========
function toggleMemory() {
    var panel = document.getElementById('memoryPanel');
    if (panel.style.display === 'none' || !panel.style.display) { panel.style.display = 'block'; loadMemory(); }
    else panel.style.display = 'none';
}
function loadMemory() {
    var el = document.getElementById('memoryContent'); el.innerHTML = '<span style="color:var(--text-muted)">加载中...</span>';
    fetch('/api/user/memory?user_id=' + userId).then(function(r) { return r.json(); }).then(function(data) {
        if (!data.queries || !data.queries.length) { el.innerHTML = '<span style="color:var(--text-muted)">暂无记录</span>'; return; }
        var html = '';
        data.queries.slice(-10).reverse().forEach(function(q) {
            var vCls = q.verdict === '\u5173\u6ce8' ? 'up' : q.verdict === '\u8b66\u60d5' ? 'down' : '';
            html += '<div class="memory-item"><span class="memory-date">' + escHtml(q.date || '') + '</span><span class="memory-symbol">' + escHtml(q.symbol) + '</span><span class="memory-verdict ' + vCls + '">' + escHtml(q.verdict || '') + '</span><span class="memory-summary">' + escHtml((q.summary || '').slice(0, 50)) + '</span></div>';
        });
        el.innerHTML = html;
    }).catch(function() { el.innerHTML = '<span style="color:var(--down)">加载失败</span>'; });
}

// ========== Search ==========
function setupSearch() {
    var input = document.getElementById('searchInput'), results = document.getElementById('searchResults'), timeout;
    input.addEventListener('input', function() { clearTimeout(timeout); var q = input.value.trim(); if (q.length < 1) { results.classList.remove('show'); return; } timeout = setTimeout(function() { searchStocks(q, results); }, 300); });
    document.addEventListener('click', function(e) { if (!e.target.closest('.search-box')) results.classList.remove('show'); });
}
function searchStocks(q, resultsEl) {
    resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--text-muted)">搜索中...</div>'; resultsEl.classList.add('show');
    fetch('/api/search?q=' + encodeURIComponent(q)).then(function(r) { return r.json(); }).then(function(data) {
        if (!data.results || !data.results.length) { resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--text-muted)">未找到</div>'; return; }
        resultsEl.innerHTML = data.results.map(function(s) { return '<div class="search-result-item" data-code="' + escHtml(s.code) + '" role="option"><span class="sr-name">' + escHtml(s.name) + '</span><span class="sr-code">' + escHtml(s.code) + '</span></div>'; }).join('');
        resultsEl.querySelectorAll('.search-result-item').forEach(function(item) { item.addEventListener('click', function() { analyzeStock(item.getAttribute('data-code')); resultsEl.classList.remove('show'); document.getElementById('searchInput').value = ''; }); });
    }).catch(function() { resultsEl.innerHTML = '<div class="search-result-item" style="color:var(--down)">搜索失败</div>'; });
}

// ========== Tabs ==========
function setupTabs() {
    document.querySelectorAll('.tab').forEach(function(tab) { tab.addEventListener('click', function(e) { e.preventDefault(); document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); }); tab.classList.add('active'); tab.setAttribute('aria-selected', 'true'); currentMarket = tab.getAttribute('data-market'); currentSort = tab.getAttribute('data-sort'); loadStocks(); }); });
}

// ========== Payment ==========
function showPay() { document.getElementById('payModal').style.display = 'flex'; }
function closePay() { document.getElementById('payModal').style.display = 'none'; }

// ========== Toast ==========
function showToast(msg) { var t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(function() { t.classList.remove('show'); }, 2500); }

// ========== Util ==========
function escHtml(s) { if (!s) return ''; return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

})();
