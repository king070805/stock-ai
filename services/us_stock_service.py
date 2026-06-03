# services/us_stock_service.py - 美股数据服务 (Yahoo Finance)
import json
import time

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def get_quote(symbol):
    """获取美股实时行情"""
    symbol = symbol.upper().strip()
    
    if not YFINANCE_AVAILABLE:
        return _mock_quote(symbol)
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="5d")
        
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
        prev_close = info.get("previousClose", price)
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        
        # 5-day change
        if len(hist) >= 2:
            hist_close_5d_ago = hist["Close"].iloc[0]
            change_5d = ((price - hist_close_5d_ago) / hist_close_5d_ago * 100)
        else:
            change_5d = 0
        
        # Volume trend
        if len(hist) >= 5:
            avg_vol = hist["Volume"].mean()
            latest_vol = hist["Volume"].iloc[-1]
            vol_trend = "上升" if latest_vol > avg_vol * 1.2 else "下降" if latest_vol < avg_vol * 0.8 else "平稳"
        else:
            vol_trend = "平稳"
        
        # News
        news_list = ticker.news[:3] if ticker.news else []
        news_summary = "; ".join([n.get("title", "")[:60] for n in news_list]) if news_list else "暂无新闻"
        
        return {
            "symbol": symbol,
            "name": info.get("shortName") or info.get("longName", symbol),
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": f"{change_pct:+.2f}",
            "change_5d": f"{change_5d:+.2f}",
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE", "N/A"),
            "market_cap": _fmt_mcap(info.get("marketCap", 0)),
            "volume_trend": vol_trend,
            "news": news_summary,
            "market": "us",
        }
    except Exception as e:
        print(f"yfinance error for {symbol}: {e}")
        # Fallback: try mock if API fails
        return _mock_quote(symbol)


def _fmt_mcap(val):
    if not val:
        return "N/A"
    val = float(val)
    if val >= 1e12:
        return f"{val/1e12:.1f}万亿"
    elif val >= 1e8:
        return f"{val/1e8:.0f}亿"
    else:
        return str(int(val))


def _mock_quote(symbol):
    """离线/失败时的模拟数据"""
    mock_data = {
        "AAPL": { "name": "Apple Inc.", "price": 198.42, "prev_close": 195.89, "change_pct": "+1.29", "pe_ratio": 30.5, "market_cap": "3.1万亿", "news": "Apple发布新AI功能，市场看好长期增长" },
        "TSLA": { "name": "Tesla Inc.", "price": 248.50, "prev_close": 252.30, "change_pct": "-1.51", "pe_ratio": 52.0, "market_cap": "7900亿", "news": "特斯拉Q4交付量超预期" },
        "NVDA": { "name": "NVIDIA Corp.", "price": 875.28, "prev_close": 860.11, "change_pct": "+1.76", "pe_ratio": 68.2, "market_cap": "2.2万亿", "news": "AI芯片需求持续暴涨" },
        "GOOGL": { "name": "Alphabet Inc.", "price": 142.65, "prev_close": 141.20, "change_pct": "+1.03", "pe_ratio": 25.8, "market_cap": "1.8万亿", "news": "Google发布新一代AI模型" },
        "MSFT": { "name": "Microsoft Corp.", "price": 420.15, "prev_close": 418.50, "change_pct": "+0.39", "pe_ratio": 35.1, "market_cap": "3.1万亿", "news": "Azure云业务增速超预期" },
    }
    
    s = mock_data.get(symbol, {
        "name": symbol,
        "price": 100.00, "prev_close": 99.00, "change_pct": "+1.01",
        "pe_ratio": 20.0, "market_cap": "N/A", "news": "暂无新闻"
    })
    
    return {
        "symbol": symbol,
        "name": s["name"],
        "price": s["price"],
        "prev_close": s["prev_close"],
        "change_pct": s["change_pct"],
        "change_5d": "+2.5",
        "pe_ratio": s["pe_ratio"],
        "market_cap": s["market_cap"],
        "volume_trend": "平稳",
        "news": s["news"],
        "market": "us",
    }


if __name__ == "__main__":
    print(get_quote("AAPL"))
    print(get_quote("TSLA"))