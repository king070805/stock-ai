#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股数据自动抓取脚本
使用 agent-browser 从东方财富网页抓取A股实时排行数据
支持三级回退：agent-browser -> AKShare -> 本地缓存
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 东方财富A股排行页面
EASTMONEY_URLS = {
    "change": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
    "amount": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
    "volume": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
}


def fetch_by_agent_browser(sort_by="change", size=20):
    """使用 agent-browser 从东方财富网页抓取A股数据"""
    url = EASTMONEY_URLS.get(sort_by, EASTMONEY_URLS["change"])
    
    # 构建 JavaScript 提取代码
    js_code = '''
const rows = document.querySelectorAll('.table-data tbody tr, .table-body tbody tr, #table_wrapper-table tbody tr');
const data = [];
for (let i = 0; i < Math.min(rows.length, 30); i++) {
    const cells = rows[i].querySelectorAll('td');
    if (cells.length >= 10) {
        data.push({
            code: cells[1]?.textContent?.trim() || '',
            name: cells[2]?.textContent?.trim() || '',
            price: cells[3]?.textContent?.trim() || '',
            change_pct: cells[4]?.textContent?.trim() || '',
            change_amt: cells[5]?.textContent?.trim() || '',
            volume: cells[6]?.textContent?.trim() || '',
            amount: cells[7]?.textContent?.trim() || '',
            amplitude: cells[8]?.textContent?.trim() || '',
            high: cells[9]?.textContent?.trim() || '',
            low: cells[10]?.textContent?.trim() || '',
            open: cells[11]?.textContent?.trim() || '',
            prev_close: cells[12]?.textContent?.trim() || '',
            pe: cells[13]?.textContent?.trim() || '',
        });
    }
}
JSON.stringify(data);
'''
    
    try:
        # Step 1: Open page
        result = subprocess.run(
            ["agent-browser", "open", url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"agent-browser open failed: {result.stderr}")
            return None
        
        # Step 2: Wait for load
        time.sleep(5)
        
        # Step 3: Extract data
        result = subprocess.run(
            ["agent-browser", "eval", js_code],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"agent-browser eval failed: {result.stderr}")
            return None
        
        # Parse JSON
        try:
            data = json.loads(result.stdout.strip())
        except:
            # Try to extract JSON from output
            text = result.stdout.strip()
            if '[' in text and ']' in text:
                start = text.index('[')
                end = text.rindex(']') + 1
                data = json.loads(text[start:end])
            else:
                return None
        
        # Step 4: Close browser
        subprocess.run(["agent-browser", "close"], capture_output=True, timeout=10)
        
        if data and len(data) > 0:
            stocks = []
            for item in data[:size]:
                if not item.get("code"):
                    continue
                stocks.append({
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "price": item.get("price", ""),
                    "change_pct": item.get("change_pct", "").replace("%", ""),
                    "change_amt": item.get("change_amt", ""),
                    "volume": item.get("volume", ""),
                    "amount": item.get("amount", ""),
                    "turnover_rate": "",
                    "pe": item.get("pe", ""),
                    "volume_ratio": "",
                    "high": item.get("high", ""),
                    "low": item.get("low", ""),
                    "open": item.get("open", ""),
                    "prev_close": item.get("prev_close", ""),
                    "market_cap": "",
                    "circ_market_cap": "",
                    "pb": "",
                    "change_60d": "",
                    "change_1y": "",
                    "industry": "",
                    "update_time": datetime.now().strftime("%H:%M:%S"),
                })
            return stocks
        
        return None
    except subprocess.TimeoutExpired:
        print("agent-browser timeout")
        subprocess.run(["agent-browser", "close"], capture_output=True)
        return None
    except Exception as e:
        print(f"agent-browser error: {e}")
        try:
            subprocess.run(["agent-browser", "close"], capture_output=True)
        except:
            pass
        return None


def fetch_by_akshare(sort_by="change", size=20):
    """使用 AKShare 获取A股数据"""
    try:
        import akshare as ak
        
        # 获取A股实时行情
        df = ak.stock_zh_a_spot_em()
        
        if df.empty:
            return None
        
        # 排序
        sort_col = {
            "change": "涨跌幅",
            "amount": "成交额",
            "volume": "成交量",
        }.get(sort_by, "涨跌幅")
        
        if sort_col in df.columns:
            df = df.sort_values(sort_col, ascending=False)
        
        stocks = []
        for _, row in df.head(size).iterrows():
            stocks.append({
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "price": str(row.get("最新价", "")),
                "change_pct": str(row.get("涨跌幅", "")).replace("%", ""),
                "change_amt": str(row.get("涨跌额", "")),
                "volume": str(row.get("成交量", "")),
                "amount": str(row.get("成交额", "")),
                "turnover_rate": str(row.get("换手率", "")),
                "pe": str(row.get("市盈率-动态", "")),
                "volume_ratio": str(row.get("量比", "")),
                "high": str(row.get("最高", "")),
                "low": str(row.get("最低", "")),
                "open": str(row.get("今开", "")),
                "prev_close": str(row.get("昨收", "")),
                "market_cap": str(row.get("总市值", "")),
                "circ_market_cap": str(row.get("流通市值", "")),
                "pb": str(row.get("市净率", "")),
                "change_60d": str(row.get("60日涨跌幅", "")),
                "change_1y": str(row.get("年初至今涨跌幅", "")),
                "industry": str(row.get("所属行业", "")),
                "update_time": datetime.now().strftime("%H:%M:%S"),
            })
        
        return stocks
    except ImportError:
        print("AKShare not installed")
        return None
    except Exception as e:
        print(f"AKShare error: {e}")
        return None


def save_to_cache(stocks, sort_by="change"):
    """保存数据到本地缓存"""
    cache_file = os.path.join(DATA_DIR, f"a_stocks_{sort_by}.json")
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sort": sort_by,
        "stocks": stocks,
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(stocks)} stocks to {cache_file}")


def load_from_cache(sort_by="change"):
    """从本地缓存读取数据"""
    cache_file = os.path.join(DATA_DIR, f"a_stocks_{sort_by}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="A股数据自动抓取")
    parser.add_argument("--sort", default="change", choices=["change", "amount", "volume"], help="排序方式")
    parser.add_argument("--size", type=int, default=20, help="获取数量")
    parser.add_argument("--source", default="auto", choices=["auto", "browser", "akshare", "cache"], help="数据源")
    args = parser.parse_args()
    
    print(f"Fetching A-share stocks: sort={args.sort}, size={args.size}, source={args.source}")
    
    stocks = None
    
    # Try sources in order
    if args.source in ("auto", "browser"):
        print("Trying agent-browser...")
        stocks = fetch_by_agent_browser(args.sort, args.size)
        if stocks:
            print(f"agent-browser success: {len(stocks)} stocks")
    
    if not stocks and args.source in ("auto", "akshare"):
        print("Trying AKShare...")
        stocks = fetch_by_akshare(args.sort, args.size)
        if stocks:
            print(f"AKShare success: {len(stocks)} stocks")
    
    if not stocks and args.source in ("auto", "cache"):
        print("Trying local cache...")
        cached = load_from_cache(args.sort)
        if cached:
            stocks = cached.get("stocks", [])
            print(f"Cache success: {len(stocks)} stocks (updated at {cached.get('update_time')})")
    
    if stocks:
        save_to_cache(stocks, args.sort)
        print(f"\nTop 5 stocks:")
        for s in stocks[:5]:
            print(f"  {s['code']} {s['name']} | {s['price']} | {s['change_pct']}%")
    else:
        print("Failed to fetch any data")
        sys.exit(1)


if __name__ == "__main__":
    main()
