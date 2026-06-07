#!/usr/bin/env python3
"""
美股热门数据抓取脚本
数据源优先级: Yahoo Finance 网页 -> yfinance API -> Mock 数据
"""

import argparse
import json
import os
import re
import sys
import random
from datetime import datetime

# ============ 配置 ============
DEFAULT_OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "us_stocks.json")
YAHOO_URL = "https://finance.yahoo.com/markets/active-us/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# 热门美股代码列表（用于 yfinance 回退和 mock 数据）
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "WMT", "MA", "PG", "UNH", "HD", "DIS", "BAC",
    "XOM", "PFE", "CRM", "AMD", "NFLX", "INTC", "BA", "NIO", "PDD",
    "BABA", "JD", "KO", "PEP", "CSCO", "ADBE", "MRK", "ABT", "CVX",
    "MCD", "TMO",
]


def parse_number(s):
    """解析 Yahoo Finance 中的数字字符串"""
    if not s or s.strip() in ("-", "N/A", ""):
        return None
    s = s.strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def format_volume(n):
    """格式化成交量"""
    if n is None:
        return "-"
    if n >= 1e9:
        return f"{n / 1e9:.1f}B"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.1f}K"
    return str(int(n))


def format_market_cap(n):
    """格式化市值"""
    if n is None:
        return "-"
    if n >= 1e12:
        return f"{n / 1e12:.2f}T"
    if n >= 1e9:
        return f"{n / 1e9:.1f}B"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    return str(int(n))


def fetch_from_yahoo_web(size=20):
    """从 Yahoo Finance 网页抓取热门美股数据"""
    import requests

    print(f"[1] 正在从 Yahoo Finance 网页抓取数据...")
    print(f"    URL: {YAHOO_URL}")

    resp = requests.get(YAHOO_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    html = resp.text

    # 尝试从网页中提取 JSON 数据（Yahoo Finance 通常在 script 标签中嵌入数据）
    # 方法1: 查找 embedded JSON data
    pattern = r'<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>'
    match = re.search(pattern, html, re.DOTALL)

    if match:
        try:
            raw_json = match.group(1)
            # Yahoo 可能使用 undefined, 需要替换
            raw_json = raw_json.replace("undefined", "null")
            data = json.loads(raw_json)
            stocks = parse_yahoo_initial_state(data, size)
            if stocks:
                print(f"    成功从 __INITIAL_STATE__ 提取 {len(stocks)} 只股票")
                return stocks
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"    解析 __INITIAL_STATE__ 失败: {e}")

    # 方法2: 查找其他 JSON 数据结构
    pattern2 = r'"activeSymbols":\s*(\[.*?\])'
    match2 = re.search(pattern2, html, re.DOTALL)
    if match2:
        try:
            raw_json = match2.group(1)
            raw_json = raw_json.replace("undefined", "null")
            data = json.loads(raw_json)
            stocks = parse_yahoo_active_symbols(data, size)
            if stocks:
                print(f"    成功从 activeSymbols 提取 {len(stocks)} 只股票")
                return stocks
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"    解析 activeSymbols 失败: {e}")

    # 方法3: 尝试从 HTML 表格中解析
    stocks = parse_yahoo_html_table(html, size)
    if stocks:
        print(f"    成功从 HTML 表格提取 {len(stocks)} 只股票")
        return stocks

    print("    网页抓取未能提取到有效数据")
    return None


def parse_yahoo_initial_state(data, size):
    """解析 Yahoo Finance __INITIAL_STATE__ 数据"""
    stocks = []

    try:
        # 尝试多种路径找到活跃股票列表
        # 路径1: data -> markets -> activeStocks
        if "data" in data:
            markets = data["data"].get("markets", {})
            active = markets.get("activeStocks", [])
            if not active:
                active = markets.get("mostActive", [])
            if not active:
                active = markets.get("active", [])

            for item in active[:size]:
                stock = extract_stock_from_yahoo_item(item)
                if stock:
                    stocks.append(stock)

        # 路径2: 直接在顶层查找
        if not stocks:
            for key in ["activeStocks", "mostActive", "active", "trending"]:
                if key in data:
                    items = data[key] if isinstance(data[key], list) else []
                    for item in items[:size]:
                        stock = extract_stock_from_yahoo_item(item)
                        if stock:
                            stocks.append(stock)
                    if stocks:
                        break
    except Exception as e:
        print(f"    解析 INITIAL_STATE 出错: {e}")

    return stocks


def extract_stock_from_yahoo_item(item):
    """从 Yahoo 数据项中提取股票信息"""
    try:
        code = item.get("symbol", item.get("ticker", ""))
        name = item.get("name", item.get("shortName", item.get("longName", "")))
        price = item.get("regularMarketPrice", item.get("price", item.get("lastSalePrice")))
        change_pct = item.get("regularMarketChangePercent", item.get("changePercent", item.get("pctChange")))
        change_amt = item.get("regularMarketChange", item.get("change", item.get("lastSalePrice")))
        volume = item.get("regularMarketVolume", item.get("volume"))
        market_cap = item.get("marketCap", item.get("market_cap"))
        pe = item.get("trailingPE", item.get("peRatio"))
        high = item.get("regularMarketDayHigh", item.get("dayHigh", item.get("high")))
        low = item.get("regularMarketDayLow", item.get("dayLow", item.get("low")))
        open_price = item.get("regularMarketOpen", item.get("open"))
        prev_close = item.get("regularMarketPreviousClose", item.get("previousClose", item.get("prevClose")))

        if not code or price is None:
            return None

        return {
            "code": code,
            "name": name or code,
            "price": f"{float(price):.2f}",
            "change_pct": format_change_pct(change_pct),
            "change_amt": format_change_amt(change_amt),
            "volume": format_volume(volume),
            "amount": format_market_cap(None),  # Yahoo 通常不直接提供成交额
            "market_cap": format_market_cap(market_cap),
            "pe": format_pe(pe),
            "high": format_price(high),
            "low": format_price(low),
            "open": format_price(open_price),
            "prev_close": format_price(prev_close),
        }
    except Exception:
        return None


def parse_yahoo_active_symbols(data, size):
    """解析 activeSymbols 数据"""
    stocks = []
    for item in data[:size]:
        stock = extract_stock_from_yahoo_item(item)
        if stock:
            stocks.append(stock)
    return stocks


def parse_yahoo_html_table(html, size):
    """从 HTML 表格中解析股票数据"""
    stocks = []

    # 查找表格行
    # Yahoo Finance 使用 data-symbol 属性
    pattern = r'<tr[^>]*data-symbol="([^"]*)"[^>]*>(.*?)</tr>'
    rows = re.findall(pattern, html, re.DOTALL)

    if not rows:
        # 尝试另一种模式
        pattern = r'<a[^>]*href="/quote/([^/]+)/"[^>]*>.*?</a>'
        symbols = re.findall(pattern, html, re.DOTALL)
        rows = [(s, "") for s in symbols[:size]]

    for symbol, row_html in rows[:size]:
        try:
            # 从行中提取价格和变化
            price_match = re.search(r'(\d+\.\d{2})', row_html)
            change_match = re.search(r'[+-]?\d+\.\d{2}\s*\([+-]?\d+\.\d+%?\)', row_html)

            price = float(price_match.group(1)) if price_match else None
            if not price:
                continue

            change_pct = 0
            change_amt = 0
            if change_match:
                change_text = change_match.group(0)
                pct_match = re.search(r'([+-]?\d+\.\d+)%', change_text)
                amt_match = re.search(r'([+-]?\d+\.\d+)', change_text)
                if pct_match:
                    change_pct = float(pct_match.group(1))
                if amt_match:
                    change_amt = float(amt_match.group(1))

            stocks.append({
                "code": symbol,
                "name": symbol,
                "price": f"{price:.2f}",
                "change_pct": format_change_pct(change_pct),
                "change_amt": format_change_amt(change_amt),
                "volume": "-",
                "amount": "-",
                "market_cap": "-",
                "pe": "-",
                "high": "-",
                "low": "-",
                "open": "-",
                "prev_close": "-",
            })
        except Exception:
            continue

    return stocks


def fetch_from_yfinance(size=20):
    """使用 yfinance API 获取数据"""
    try:
        import yfinance as yf
    except ImportError:
        print("[2] yfinance 未安装，尝试安装...")
        import subprocess
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "yfinance", "-q"
        ])
        import yfinance as yf

    print(f"[2] 正在使用 yfinance 获取 {size} 只热门美股数据...")

    tickers = DEFAULT_TICKERS[:size + 10]  # 多取一些以防有无效的
    data = yf.download(tickers, period="1d", group_by="ticker", threads=True)

    stocks = []
    valid_tickers = []

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                price_data = data
            else:
                price_data = data.get(ticker)
            if price_data is None or price_data.empty:
                continue

            info = yf.Ticker(ticker).info
            last_close = price_data["Close"].iloc[-1]
            prev_close = price_data["Close"].iloc[-2] if len(price_data) >= 2 else info.get("previousClose", last_close)
            change_amt = last_close - prev_close
            change_pct = (change_amt / prev_close * 100) if prev_close else 0

            stocks.append({
                "code": ticker,
                "name": info.get("shortName", info.get("longName", ticker)),
                "price": f"{last_close:.2f}",
                "change_pct": format_change_pct(change_pct),
                "change_amt": format_change_amt(change_amt),
                "volume": format_volume(info.get("volume")),
                "amount": format_market_cap(info.get("averageDailyVolume3Month")),
                "market_cap": format_market_cap(info.get("marketCap")),
                "pe": format_pe(info.get("trailingPE")),
                "high": format_price(price_data["High"].iloc[-1]),
                "low": format_price(price_data["Low"].iloc[-1]),
                "open": format_price(price_data["Open"].iloc[-1]),
                "prev_close": format_price(prev_close),
            })
            valid_tickers.append(ticker)
        except Exception as e:
            print(f"    跳过 {ticker}: {e}")
            continue

    print(f"    成功获取 {len(stocks)} 只股票数据")
    return stocks


def generate_mock_data(size=20):
    """生成模拟数据（最后回退方案）"""
    print(f"[3] 使用模拟数据生成 {size} 只热门美股...")

    mock_stocks = [
        ("NVDA", "NVIDIA Corp.", 875.28, 2.15, 68.20, 2.15e12, 41.0e6),
        ("AAPL", "Apple Inc.", 198.42, 1.29, 30.50, 3.05e12, 52.0e6),
        ("MSFT", "Microsoft Corp.", 420.15, 0.39, 35.10, 3.12e12, 21.0e6),
        ("AMZN", "Amazon.com Inc.", 185.60, 0.85, 58.30, 1.93e12, 35.0e6),
        ("GOOGL", "Alphabet Inc.", 142.65, 1.03, 25.80, 1.76e12, 28.0e6),
        ("META", "Meta Platforms", 505.75, 2.10, 28.40, 1.29e12, 18.0e6),
        ("TSLA", "Tesla Inc.", 248.50, -1.51, 52.00, 790.0e9, 98.0e6),
        ("BRK-B", "Berkshire Hathaway", 412.80, 0.15, 9.80, 890.0e9, 3.5e6),
        ("JPM", "JPMorgan Chase", 205.30, 0.68, 12.10, 590.0e9, 8.0e6),
        ("V", "Visa Inc.", 282.40, 0.32, 31.50, 580.0e9, 6.0e6),
        ("AMD", "Advanced Micro Devices", 168.50, 2.30, 280.00, 270.0e9, 42.0e6),
        ("NFLX", "Netflix Inc.", 628.90, 1.85, 44.20, 270.0e9, 5.0e6),
        ("CRM", "Salesforce Inc.", 255.60, 0.75, 48.30, 250.0e9, 5.0e6),
        ("BABA", "Alibaba Group", 78.65, -0.95, 10.20, 200.0e9, 12.0e6),
        ("DIS", "Walt Disney Co.", 112.40, -0.45, 72.50, 205.0e9, 7.0e6),
        ("PDD", "PDD Holdings", 132.80, 1.60, 18.50, 170.0e9, 9.0e6),
        ("INTC", "Intel Corp.", 30.15, -0.66, None, 130.0e9, 32.0e6),
        ("BA", "Boeing Co.", 178.90, 1.25, None, 110.0e9, 5.0e6),
        ("NIO", "NIO Inc.", 5.82, 3.20, None, 9.8e9, 45.0e6),
        ("JD", "JD.com Inc.", 35.20, 0.86, 11.80, 55.0e9, 8.0e6),
    ]

    stocks = []
    now = datetime.now()

    for code, name, base_price, base_change_pct, pe, mcap, vol in mock_stocks[:size]:
        # 添加小幅随机波动使数据看起来更真实
        price_offset = base_price * random.uniform(-0.005, 0.005)
        price = base_price + price_offset
        change_pct = base_change_pct + random.uniform(-0.3, 0.3)
        change_amt = price * change_pct / 100
        prev_close = price - change_amt

        stocks.append({
            "code": code,
            "name": name,
            "price": f"{price:.2f}",
            "change_pct": format_change_pct(change_pct),
            "change_amt": format_change_amt(change_amt),
            "volume": format_volume(vol + random.randint(-int(vol * 0.1), int(vol * 0.1))),
            "amount": format_market_cap(price * vol),
            "market_cap": format_market_cap(mcap),
            "pe": format_pe(pe),
            "high": f"{price * 1.008:.2f}",
            "low": f"{price * 0.992:.2f}",
            "open": f"{price + random.uniform(-1, 1):.2f}",
            "prev_close": f"{prev_close:.2f}",
        })

    return stocks


def format_change_pct(val):
    """格式化涨跌幅百分比"""
    if val is None:
        return "-"
    return f"{val:+.2f}"


def format_change_amt(val):
    """格式化涨跌额"""
    if val is None:
        return "-"
    return f"{val:+.2f}"


def format_price(val):
    """格式化价格"""
    if val is None:
        return "-"
    return f"{float(val):.2f}"


def format_pe(val):
    """格式化市盈率"""
    if val is None:
        return "-"
    return f"{float(val):.2f}"


def sort_stocks(stocks, sort_by="change"):
    """对股票列表排序"""
    if sort_by == "change":
        stocks.sort(key=lambda s: float(s["change_pct"]) if s["change_pct"] != "-" else 0, reverse=True)
    elif sort_by == "volume":
        stocks.sort(key=lambda s: s["volume"], reverse=True)
    elif sort_by == "name":
        stocks.sort(key=lambda s: s["code"])
    elif sort_by == "price_desc":
        stocks.sort(key=lambda s: float(s["price"]) if s["price"] != "-" else 0, reverse=True)
    elif sort_by == "price_asc":
        stocks.sort(key=lambda s: float(s["price"]) if s["price"] != "-" else 0)
    return stocks


def main():
    parser = argparse.ArgumentParser(description="美股热门数据抓取脚本")
    parser.add_argument("--sort", default="change", choices=["change", "volume", "name", "price_desc", "price_asc"],
                        help="排序方式 (默认: change)")
    parser.add_argument("--size", type=int, default=20, help="获取股票数量 (默认: 20)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="输出文件路径")
    parser.add_argument("--source", default="auto", choices=["auto", "web", "yfinance", "mock"],
                        help="数据源 (默认: auto)")
    args = parser.parse_args()

    print("=" * 60)
    print("  美股热门数据抓取工具")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  排序: {args.sort} | 数量: {args.size} | 数据源: {args.source}")
    print("=" * 60)

    stocks = None

    # 尝试数据源
    if args.source in ("auto", "web"):
        try:
            stocks = fetch_from_yahoo_web(size=args.size)
        except Exception as e:
            print(f"    网页抓取失败: {e}")

    if not stocks and args.source in ("auto", "yfinance"):
        try:
            stocks = fetch_from_yfinance(size=args.size)
        except Exception as e:
            print(f"    yfinance 获取失败: {e}")

    if not stocks:
        stocks = generate_mock_data(size=args.size)

    # 排序
    stocks = sort_stocks(stocks, args.sort)

    # 构建输出数据
    output = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sort": args.sort,
        "stocks": stocks,
    }

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # 保存文件
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"  数据已保存到: {args.output}")
    print(f"  共 {len(stocks)} 只股票")
    if stocks:
        print(f"  涨幅最大: {stocks[0]['code']} ({stocks[0]['change_pct']}%)")
        if len(stocks) > 1:
            print(f"  涨幅最小: {stocks[-1]['code']} ({stocks[-1]['change_pct']}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
