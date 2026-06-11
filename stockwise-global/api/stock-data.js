/**
 * StockWise - Stock Data API
 * Fetches real-time stock data from Yahoo Finance
 */

const YAHOO_FINANCE_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/';

// Top US stocks to track
const TRACKED_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
    'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'UNH', 'HD',
    'BAC', 'ABBV', 'PFE', 'KO', 'PEP', 'AVGO', 'COST',
    'DIS', 'NFLX', 'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL',
    'UBER', 'LYFT', 'SNOW', 'ZM', 'SHOP', 'SQ', 'ROKU'
];

async function fetchStockData(symbol) {
    try {
        const response = await fetch(`${YAHOO_FINANCE_URL}${symbol}?interval=1d&range=1d`);
        const data = await response.json();
        
        if (data.chart && data.chart.result && data.chart.result[0]) {
            const result = data.chart.result[0];
            const meta = result.meta;
            const quote = result.indicators.quote[0];
            
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
                high: meta.regularMarketDayHigh || currentPrice,
                low: meta.regularMarketDayLow || currentPrice,
                timestamp: new Date().toISOString()
            };
        }
        return null;
    } catch (error) {
        console.error(`Error fetching ${symbol}:`, error);
        return null;
    }
}

async function fetchAllStocks() {
    const stocks = [];
    
    for (const symbol of TRACKED_STOCKS) {
        const data = await fetchStockData(symbol);
        if (data) {
            stocks.push(data);
        }
        // Small delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return stocks;
}

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

// Dividend yield mapping (approximate)
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

// P/E ratio mapping (approximate)
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

async function getStocksData() {
    const rawData = await fetchAllStocks();
    
    return rawData.map(stock => ({
        symbol: stock.symbol,
        name: getCompanyName(stock.symbol),
        sector: SECTOR_MAP[stock.symbol] || 'Technology',
        price: stock.price,
        change: stock.change,
        volume: formatVolume(stock.volume),
        dividend: DIVIDEND_MAP[stock.symbol] || '0.00%',
        pe: PE_MAP[stock.symbol] || 'N/A',
        heat: calculateHeat(stock.change, stock.volume)
    }));
}

function getCompanyName(symbol) {
    const names = {
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
    return names[symbol] || symbol;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getStocksData, fetchStockData };
}
