/**
 * StockWise - Express Server
 * Handles API requests and serves static files
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const fetch = require('node-fetch');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Stock symbols to track
const TRACKED_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
    'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'UNH', 'HD',
    'BAC', 'ABBV', 'PFE', 'KO', 'PEP', 'AVGO', 'COST',
    'DIS', 'NFLX', 'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL',
    'UBER', 'LYFT', 'SNOW', 'ZM', 'SHOP', 'SQ', 'ROKU'
];

// Company data mapping
const COMPANY_DATA = {
    'AAPL': { name: 'Apple Inc.', sector: 'Technology', dividend: '0.52%', pe: '28.5' },
    'MSFT': { name: 'Microsoft Corp.', sector: 'Technology', dividend: '0.72%', pe: '35.2' },
    'GOOGL': { name: 'Alphabet Inc.', sector: 'Technology', dividend: '0.00%', pe: '24.8' },
    'AMZN': { name: 'Amazon.com Inc.', sector: 'Technology', dividend: '0.00%', pe: '58.3' },
    'NVDA': { name: 'NVIDIA Corp.', sector: 'Technology', dividend: '0.03%', pe: '65.1' },
    'META': { name: 'Meta Platforms', sector: 'Technology', dividend: '0.00%', pe: '32.6' },
    'TSLA': { name: 'Tesla Inc.', sector: 'Automotive', dividend: '0.00%', pe: '72.4' },
    'JPM': { name: 'JPMorgan Chase', sector: 'Finance', dividend: '2.35%', pe: '10.8' },
    'V': { name: 'Visa Inc.', sector: 'Finance', dividend: '0.75%', pe: '30.2' },
    'JNJ': { name: 'Johnson & Johnson', sector: 'Healthcare', dividend: '2.95%', pe: '15.4' },
    'WMT': { name: 'Walmart Inc.', sector: 'Retail', dividend: '1.38%', pe: '25.6' },
    'PG': { name: 'Procter & Gamble', sector: 'Consumer', dividend: '2.42%', pe: '24.8' },
    'MA': { name: 'Mastercard Inc.', sector: 'Finance', dividend: '0.54%', pe: '35.8' },
    'UNH': { name: 'UnitedHealth Group', sector: 'Healthcare', dividend: '1.32%', pe: '22.1' },
    'HD': { name: 'Home Depot', sector: 'Retail', dividend: '2.15%', pe: '19.8' },
    'BAC': { name: 'Bank of America', sector: 'Finance', dividend: '2.68%', pe: '11.2' },
    'ABBV': { name: 'AbbVie Inc.', sector: 'Healthcare', dividend: '3.52%', pe: '17.5' },
    'PFE': { name: 'Pfizer Inc.', sector: 'Healthcare', dividend: '5.68%', pe: '9.2' },
    'KO': { name: 'Coca-Cola Co.', sector: 'Consumer', dividend: '3.05%', pe: '23.4' },
    'PEP': { name: 'PepsiCo Inc.', sector: 'Consumer', dividend: '2.82%', pe: '25.1' },
    'AVGO': { name: 'Broadcom Inc.', sector: 'Technology', dividend: '1.85%', pe: '28.3' },
    'COST': { name: 'Costco Wholesale', sector: 'Retail', dividend: '0.65%', pe: '42.1' },
    'DIS': { name: 'Walt Disney Co.', sector: 'Entertainment', dividend: '0.85%', pe: '24.5' },
    'NFLX': { name: 'Netflix Inc.', sector: 'Technology', dividend: '0.00%', pe: '45.2' },
    'AMD': { name: 'AMD Inc.', sector: 'Technology', dividend: '0.00%', pe: '38.5' },
    'INTC': { name: 'Intel Corp.', sector: 'Technology', dividend: '1.25%', pe: '15.2' },
    'CRM': { name: 'Salesforce Inc.', sector: 'Technology', dividend: '0.00%', pe: '62.1' },
    'ADBE': { name: 'Adobe Inc.', sector: 'Technology', dividend: '0.00%', pe: '35.8' },
    'PYPL': { name: 'PayPal Holdings', sector: 'Finance', dividend: '0.00%', pe: '18.5' },
    'UBER': { name: 'Uber Technologies', sector: 'Technology', dividend: '0.00%', pe: '45.2' },
    'LYFT': { name: 'Lyft Inc.', sector: 'Technology', dividend: '0.00%', pe: '0.00' },
    'SNOW': { name: 'Snowflake Inc.', sector: 'Technology', dividend: '0.00%', pe: '0.00' },
    'ZM': { name: 'Zoom Video', sector: 'Technology', dividend: '0.00%', pe: '18.5' },
    'SHOP': { name: 'Shopify Inc.', sector: 'Technology', dividend: '0.00%', pe: '85.2' },
    'SQ': { name: 'Block Inc.', sector: 'Finance', dividend: '0.00%', pe: '42.1' },
    'ROKU': { name: 'Roku Inc.', sector: 'Technology', dividend: '0.00%', pe: '0.00' }
};

// Format volume
function formatVolume(volume) {
    if (volume >= 1000000) {
        return (volume / 1000000).toFixed(1) + 'M';
    } else if (volume >= 1000) {
        return (volume / 1000).toFixed(1) + 'K';
    }
    return volume.toString();
}

// Calculate heat score
function calculateHeat(change, volume) {
    let heat = 1;
    if (Math.abs(change) > 2) heat += 2;
    else if (Math.abs(change) > 1) heat += 1;
    
    if (volume > 50000000) heat += 2;
    else if (volume > 20000000) heat += 1;
    
    return Math.min(heat, 5);
}

// Fetch stock data from Yahoo Finance
async function fetchStockData(symbol) {
    try {
        const response = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`);
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

// API Routes

// Get all stocks data
app.get('/api/stocks', async (req, res) => {
    try {
        const stocks = [];
        
        for (const symbol of TRACKED_STOCKS) {
            const data = await fetchStockData(symbol);
            if (data) {
                const companyInfo = COMPANY_DATA[symbol] || { 
                    name: symbol, 
                    sector: 'Technology', 
                    dividend: '0.00%', 
                    pe: 'N/A' 
                };
                
                stocks.push({
                    symbol: data.symbol,
                    name: companyInfo.name,
                    sector: companyInfo.sector,
                    price: data.price,
                    change: data.change,
                    volume: formatVolume(data.volume),
                    dividend: companyInfo.dividend,
                    pe: companyInfo.pe,
                    heat: calculateHeat(data.change, data.volume),
                    timestamp: data.timestamp
                });
            }
            // Small delay to avoid rate limiting
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        res.json({
            success: true,
            count: stocks.length,
            data: stocks,
            lastUpdated: new Date().toISOString()
        });
    } catch (error) {
        console.error('Error fetching stocks:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to fetch stock data'
        });
    }
});

// Get single stock data
app.get('/api/stocks/:symbol', async (req, res) => {
    try {
        const { symbol } = req.params;
        const data = await fetchStockData(symbol.toUpperCase());
        
        if (data) {
            const companyInfo = COMPANY_DATA[symbol.toUpperCase()] || { 
                name: symbol, 
                sector: 'Technology', 
                dividend: '0.00%', 
                pe: 'N/A' 
            };
            
            res.json({
                success: true,
                data: {
                    ...data,
                    name: companyInfo.name,
                    sector: companyInfo.sector,
                    volume: formatVolume(data.volume),
                    dividend: companyInfo.dividend,
                    pe: companyInfo.pe,
                    heat: calculateHeat(data.change, data.volume)
                }
            });
        } else {
            res.status(404).json({
                success: false,
                error: 'Stock not found'
            });
        }
    } catch (error) {
        console.error('Error fetching stock:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to fetch stock data'
        });
    }
});

// Health check
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

// Serve main pages
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname, 'login.html'));
});

app.get('/pricing', (req, res) => {
    res.sendFile(path.join(__dirname, 'pricing.html'));
});

// Error handling
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({
        success: false,
        error: 'Internal server error'
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`StockWise server running on port ${PORT}`);
    console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});

module.exports = app;
