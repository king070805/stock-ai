/**
 * StockWise - Global Version
 * Main JavaScript functionality with real-time stock data
 */

// ============================================
// STOCK DATA API INTEGRATION
// ============================================
const YAHOO_FINANCE_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/';

// Top US stocks to track
const TRACKED_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
    'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'UNH', 'HD',
    'BAC', 'ABBV', 'PFE', 'KO', 'PEP', 'AVGO', 'COST',
    'DIS', 'NFLX', 'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL',
    'UBER', 'LYFT', 'SNOW', 'ZM', 'SHOP', 'SQ', 'ROKU'
];

// Company names mapping
const COMPANY_NAMES = {
    'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft Corp.', 'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.', 'NVDA': 'NVIDIA Corp.', 'META': 'Meta Platforms',
    'TSLA': 'Tesla Inc.', 'JPM': 'JPMorgan Chase', 'V': 'Visa Inc.',
    'JNJ': 'Johnson & Johnson', 'WMT': 'Walmart Inc.', 'PG': 'Procter & Gamble',
    'MA': 'Mastercard Inc.', 'UNH': 'UnitedHealth Group', 'HD': 'Home Depot',
    'BAC': 'Bank of America', 'ABBV': 'AbbVie Inc.', 'PFE': 'Pfizer Inc.',
    'KO': 'Coca-Cola Co.', 'PEP': 'PepsiCo Inc.', 'AVGO': 'Broadcom Inc.',
    'COST': 'Costco Wholesale', 'DIS': 'Walt Disney Co.', 'NFLX': 'Netflix Inc.',
    'AMD': 'AMD Inc.', 'INTC': 'Intel Corp.', 'CRM': 'Salesforce Inc.',
    'ADBE': 'Adobe Inc.', 'PYPL': 'PayPal Holdings', 'UBER': 'Uber Technologies',
    'LYFT': 'Lyft Inc.', 'SNOW': 'Snowflake Inc.', 'ZM': 'Zoom Video',
    'SHOP': 'Shopify Inc.', 'SQ': 'Block Inc.', 'ROKU': 'Roku Inc.'
};

// Sector mapping
const SECTOR_MAP = {
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
    'AMZN': 'Technology', 'NVDA': 'Technology', 'META': 'Technology',
    'TSLA': 'Automotive', 'AMD': 'Technology', 'INTC': 'Technology',
    'CRM': 'Technology', 'ADBE': 'Technology', 'NFLX': 'Technology',
    'JPM': 'Finance', 'V': 'Finance', 'MA': 'Finance', 'BAC': 'Finance',
    'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'ABBV': 'Healthcare', 'PFE': 'Healthcare',
    'WMT': 'Retail', 'HD': 'Retail', 'COST': 'Retail',
    'PG': 'Consumer', 'KO': 'Consumer', 'PEP': 'Consumer',
    'DIS': 'Entertainment', 'UBER': 'Technology', 'LYFT': 'Technology',
    'SNOW': 'Technology', 'ZM': 'Technology', 'SHOP': 'Technology',
    'SQ': 'Finance', 'ROKU': 'Technology', 'PYPL': 'Finance',
    'AVGO': 'Technology'
};

// Dividend yield mapping
const DIVIDEND_MAP = {
    'AAPL': '0.52%', 'MSFT': '0.72%', 'GOOGL': '0.00%', 'AMZN': '0.00%',
    'NVDA': '0.03%', 'META': '0.00%', 'TSLA': '0.00%', 'JPM': '2.35%',
    'V': '0.75%', 'JNJ': '2.95%', 'WMT': '1.38%', 'PG': '2.42%',
    'MA': '0.54%', 'UNH': '1.32%', 'HD': '2.15%', 'BAC': '2.68%',
    'ABBV': '3.52%', 'PFE': '5.68%', 'KO': '3.05%', 'PEP': '2.82%',
    'AVGO': '1.85%', 'COST': '0.65%', 'DIS': '0.85%', 'NFLX': '0.00%',
    'AMD': '0.00%', 'INTC': '1.25%', 'CRM': '0.00%', 'ADBE': '0.00%',
    'PYPL': '0.00%', 'UBER': '0.00%', 'LYFT': '0.00%', 'SNOW': '0.00%',
    'ZM': '0.00%', 'SHOP': '0.00%', 'SQ': '0.00%', 'ROKU': '0.00%'
};

// P/E ratio mapping
const PE_MAP = {
    'AAPL': '28.5', 'MSFT': '35.2', 'GOOGL': '24.8', 'AMZN': '58.3',
    'NVDA': '65.1', 'META': '32.6', 'TSLA': '72.4', 'JPM': '10.8',
    'V': '30.2', 'JNJ': '15.4', 'WMT': '25.6', 'PG': '24.8',
    'MA': '35.8', 'UNH': '22.1', 'HD': '19.8', 'BAC': '11.2',
    'ABBV': '17.5', 'PFE': '9.2', 'KO': '23.4', 'PEP': '25.1',
    'AVGO': '28.3', 'COST': '42.1', 'DIS': '24.5', 'NFLX': '45.2',
    'AMD': '38.5', 'INTC': '15.2', 'CRM': '62.1', 'ADBE': '35.8',
    'PYPL': '18.5', 'UBER': '45.2', 'LYFT': '0.00', 'SNOW': '0.00',
    'ZM': '18.5', 'SHOP': '85.2', 'SQ': '42.1', 'ROKU': '0.00'
};

// ============================================
// STATE
// ============================================
let currentMarket = 'us';
let currentCategory = 'all';
let watchlist = ['AAPL', 'MSFT', 'NVDA'];
let currentSort = { field: null, direction: 'asc' };
let stocksData = [];
let isLoading = false;

// ============================================
// DOM ELEMENTS
// ============================================
const stockTableBody = document.getElementById('stockTableBody');
const stockSearch = document.getElementById('stockSearch');
const watchlistStocks = document.getElementById('watchlistStocks');
const toggleWatchlist = document.getElementById('toggleWatchlist');
const watchlistContent = document.getElementById('watchlistContent');
const aiAnalysisModal = document.getElementById('aiAnalysisModal');
const closeModal = document.getElementById('closeModal');
const analysisContent = document.getElementById('analysisContent');

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    loadStocksData();
    renderWatchlist();
    setupEventListeners();
    setupAutoRefresh();
});

// ============================================
// STOCK DATA FETCHING
// ============================================
async function fetchStockData(symbol) {
    try {
        const response = await fetch(`${YAHOO_FINANCE_URL}${symbol}?interval=1d&range=1d`);
        const data = await response.json();
        
        if (data.chart && data.chart.result && data.chart.result[0]) {
            const result = data.chart.result[0];
            const meta = result.meta;
            
            const currentPrice = meta.regularMarketPrice || meta.previousClose;
            const previousClose = meta.previousClose || meta.chartPreviousClose;
            const change = currentPrice - previousClose;
            const changePercent = (change / previousClose) * 100;
            
            return {
                symbol: symbol,
                price: currentPrice,
                change: changePercent,
                volume: meta.regularMarketVolume || 0,
                previousClose: previousClose,
                timestamp: new Date().toISOString()
            };
        }
        return null;
    } catch (error) {
        console.error(`Error fetching ${symbol}:`, error);
        return null;
    }
}

async function loadStocksData() {
    if (isLoading) return;
    isLoading = true;
    
    // Show loading state
    if (stockTableBody) {
        stockTableBody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 2rem;"><i class="fas fa-spinner fa-spin"></i> Loading stock data...</td></tr>';
    }
    
    const stocks = [];
    
    for (const symbol of TRACKED_STOCKS) {
        const data = await fetchStockData(symbol);
        if (data) {
            stocks.push({
                symbol: data.symbol,
                name: COMPANY_NAMES[data.symbol] || data.symbol,
                sector: SECTOR_MAP[data.symbol] || 'Technology',
                price: data.price,
                change: data.change,
                volume: formatVolume(data.volume),
                dividend: DIVIDEND_MAP[data.symbol] || '0.00%',
                pe: PE_MAP[data.symbol] || 'N/A',
                heat: calculateHeat(data.change, data.volume)
            });
        }
        // Small delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    stocksData = stocks;
    isLoading = false;
    renderStockTable();
}

function formatVolume(volume) {
    if (volume >= 1000000) {
        return (volume / 1000000).toFixed(1) + 'M';
    } else if (volume >= 1000) {
        return (volume / 1000).toFixed(1) + 'K';
    }
    return volume.toString();
}

function calculateHeat(change, volume) {
    let heat = 1;
    if (Math.abs(change) > 2) heat += 2;
    else if (Math.abs(change) > 1) heat += 1;
    
    if (volume > 50000000) heat += 2;
    else if (volume > 20000000) heat += 1;
    
    return Math.min(heat, 5);
}

// ============================================
// AUTO REFRESH
// ============================================
function setupAutoRefresh() {
    // Refresh every 5 minutes during market hours
    setInterval(() => {
        const now = new Date();
        const hour = now.getHours();
        const day = now.getDay();
        
        // Market hours: Mon-Fri, 9:30 AM - 4:00 PM EST
        if (day >= 1 && day <= 5 && hour >= 9 && hour <= 16) {
            console.log('Auto-refreshing stock data...');
            loadStocksData();
        }
    }, 5 * 60 * 1000); // 5 minutes
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    // Market tabs
    document.querySelectorAll('.market-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.market-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentMarket = tab.dataset.market;
            renderStockTable();
        });
    });

    // Watchlist category tabs
    document.querySelectorAll('.tab-btn').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentCategory = tab.dataset.category;
            renderWatchlist();
        });
    });

    // Toggle watchlist
    toggleWatchlist?.addEventListener('click', () => {
        watchlistContent.classList.toggle('collapsed');
        const icon = toggleWatchlist.querySelector('i');
        icon.classList.toggle('fa-chevron-down');
        icon.classList.toggle('fa-chevron-up');
    });

    // Search
    stockSearch?.addEventListener('input', (e) => {
        renderStockTable(e.target.value);
    });

    // Sort
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (currentSort.field === field) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.direction = 'asc';
            }
            renderStockTable();
        });
    });

    // Modal
    closeModal?.addEventListener('click', () => {
        aiAnalysisModal.classList.remove('active');
    });

    aiAnalysisModal?.addEventListener('click', (e) => {
        if (e.target === aiAnalysisModal) {
            aiAnalysisModal.classList.remove('active');
        }
    });
}

// ============================================
// RENDER FUNCTIONS
// ============================================
function renderStockTable(searchQuery = '') {
    let stocks = [...stocksData];

    // Search filter
    if (searchQuery) {
        const query = searchQuery.toLowerCase();
        stocks = stocks.filter(s => 
            s.symbol.toLowerCase().includes(query) || 
            s.name.toLowerCase().includes(query)
        );
    }

    // Sort
    if (currentSort.field) {
        stocks = stocks.sort((a, b) => {
            let aVal, bVal;
            switch (currentSort.field) {
                case 'name': aVal = a.symbol; bVal = b.symbol; break;
                case 'price': aVal = a.price; bVal = b.price; break;
                case 'change': aVal = a.change; bVal = b.change; break;
                default: return 0;
            }
            if (currentSort.direction === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });
    }

    if (stocks.length === 0) {
        stockTableBody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 2rem;">未找到相关股票</td></tr>';
        return;
    }

    stockTableBody.innerHTML = stocks.map((stock, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>
                <div class="stock-name-cell">
                    <div class="stock-logo">${stock.symbol.slice(0, 2)}</div>
                    <div class="stock-details">
                        <span class="stock-symbol">${stock.symbol}</span>
                        <span class="stock-fullname">${stock.name}</span>
                    </div>
                </div>
            </td>
            <td><span class="sector-tag">${stock.sector}</span></td>
            <td class="price">$${stock.price.toFixed(2)}</td>
            <td class="change ${stock.change >= 0 ? 'up' : 'down'}">
                ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(2)}%
            </td>
            <td class="volume">${stock.volume}</td>
            <td class="dividend">${stock.dividend}</td>
            <td class="pe">${stock.pe}</td>
            <td>
                <div class="heat-indicator">
                    ${Array(5).fill(0).map((_, i) => `
                        <div class="heat-dot ${i < stock.heat ? 'active' : ''}"></div>
                    `).join('')}
                </div>
            </td>
            <td>
                <div style="display: flex; gap: 8px;">
                    <button class="btn-action btn-analyze" onclick="showAIAnalysis('${stock.symbol}')">
                        AI 整理
                    </button>
                    <button class="btn-action btn-star ${watchlist.includes(stock.symbol) ? 'active' : ''}" 
                            onclick="toggleWatchlistStock('${stock.symbol}')">
                        <i class="${watchlist.includes(stock.symbol) ? 'fas' : 'far'} fa-star"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderWatchlist() {
    let stocks = stocksData.filter(s => watchlist.includes(s.symbol));

    // Category filter
    if (currentCategory !== 'all') {
        const categoryMap = {
            'tech': 'Technology',
            'finance': 'Finance',
            'dividend': null
        };
        
        if (currentCategory === 'dividend') {
            stocks = stocks.filter(s => parseFloat(s.dividend) > 2);
        } else {
            stocks = stocks.filter(s => s.sector === categoryMap[currentCategory]);
        }
    }

    watchlistStocks.innerHTML = stocks.map(stock => `
        <div class="watchlist-item">
            <div class="stock-info">
                <span class="stock-symbol">${stock.symbol}</span>
                <span class="stock-name">${stock.name}</span>
            </div>
            <div class="stock-price">
                <div class="price">$${stock.price.toFixed(2)}</div>
                <div class="change ${stock.change >= 0 ? 'up' : 'down'}">
                    ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(2)}%
                </div>
            </div>
        </div>
    `).join('') || '<p style="text-align: center; color: var(--text-muted); padding: 1rem;">暂无自选股票</p>';
}

// ============================================
// AI ANALYSIS
// ============================================
function showAIAnalysis(symbol) {
    const stock = stocksData.find(s => s.symbol === symbol);
    if (!stock) return;

    const peNumber = Number.parseFloat(stock.pe);
    const peLevel = Number.isFinite(peNumber)
        ? (peNumber < 15 ? '偏低' : peNumber < 30 ? '中等' : '偏高')
        : '暂无';
    const volumeLevel = stock.volume.includes('M') && parseFloat(stock.volume) > 20
        ? '相对活跃'
        : '常规';

    const analysisHTML = `
        <div class="analysis-result">
            <div class="analysis-header">
                <div class="stock-logo">${symbol.slice(0, 2)}</div>
                <div class="stock-title">
                    <h3>${stock.name}</h3>
                    <span>${symbol} · ${stock.sector}</span>
                </div>
            </div>

            <div class="analysis-score">
                <div class="score-circle">
                    <span>${stock.heat}/5</span>
                </div>
                <div class="score-label">
                    <span>公开信息热度</span>
                    <span>根据涨跌幅和成交量整理</span>
                </div>
            </div>

            <div class="analysis-section">
                <h4><i class="fas fa-chart-line"></i> 行情信息整理</h4>
                <p>当前涨跌幅为 ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(2)}%，成交量处于${volumeLevel}水平。
                该部分仅整理公开行情变化，帮助用户理解价格和成交量的同步情况。</p>
            </div>

            <div class="analysis-section">
                <h4><i class="fas fa-building"></i> 基础指标整理</h4>
                <p>${stock.name} 当前 P/E 为 ${stock.pe}，股息率为 ${stock.dividend}。
                这些指标适合与同行业公司、历史区间和公司公告一起对照查看，不能单独作为投资决策依据。</p>
            </div>

            <div class="analysis-section">
                <h4><i class="fas fa-newspaper"></i> 市场热度整理</h4>
                <p>系统根据涨跌幅和成交量给出 ${stock.heat}/5 的热度标记，用来提示近期关注度变化。
                热度不代表后续走势判断，也不构成买卖建议。</p>
            </div>

            <div class="analysis-metrics">
                <div class="metric-card">
                    <div class="metric-value">${stock.heat}/5</div>
                    <div class="metric-label">信息热度</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${stock.change >= 0 ? '上涨' : '下跌'}</div>
                    <div class="metric-label">当日方向</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${peLevel}</div>
                    <div class="metric-label">P/E 档位</div>
                </div>
            </div>

            <div class="analysis-disclaimer">
                AI 仅整理公开信息，不提供买卖点、仓位安排、价格预测，也不承诺收益。以上内容不构成投资建议。
            </div>
        </div>
    `;

    analysisContent.innerHTML = analysisHTML;
    aiAnalysisModal.classList.add('active');
}
// ============================================
// WATCHLIST FUNCTIONS
// ============================================
function toggleWatchlistStock(symbol) {
    const index = watchlist.indexOf(symbol);
    if (index > -1) {
        watchlist.splice(index, 1);
    } else {
        watchlist.push(symbol);
    }
    renderStockTable(stockSearch?.value || '');
    renderWatchlist();
}

// ============================================
// ALERT SUBSCRIPTION
// ============================================
document.querySelector('.btn-alert')?.addEventListener('click', () => {
    alert('AI 异动提醒功能即将上线：用于整理公开行情变化和提醒关注信息，不构成投资建议。');
});

// ============================================
// EXPORT FOR TESTING
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchStockData,
        loadStocksData,
        formatVolume,
        calculateHeat
    };
}
