# services/stock_service.py - 股票数据服务
import requests
import json
import re
import time
import os
os.environ["no_proxy"] = "*"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/"
}

# 市场参数
MARKETS = {
    "a": "m:0+t:6,m:0+t:7",       # A股（沪深）
    "sh": "m:1+t:2",               # 上证
    "sz": "m:0+t:6,m:0+t:7",       # 深证
    "us": "m:105+t:3,m:106+t:3",   # 美股
    "hk": "m:128+t:3",             # 港股
}

# 字段映射 push2 API
FIELDS = "f2,f3,f4,f5,f6,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f100,f124"

def get_stock_list(market="a", sort_by="change", page=1, size=20):
    """获取股票列表/排行"""
    fs = MARKETS.get(market, MARKETS["a"])
    
    # 排序字段
    sort_fid = {
        "change": "f3",      # 涨跌幅
        "volume": "f5",      # 成交量
        "amount": "f6",      # 成交额
        "hot": "f10",        # 量比
        "pe": "f9",          # 市盈率
    }.get(sort_by, "f3")
    
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": page, "pz": size,
        "po": "1" if sort_by in ("pe","change") else "0",  # PE升序，其他降序
        "np": "1", "fltt": "2", "invt": "2",
        "fid": sort_fid, "fs": fs,
        "fields": FIELDS,
        "_": int(time.time() * 1000)
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10, proxies={"http": None, "https": None})
        data = resp.json()
        
        stocks = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                price_val = item.get("f2")
                prev_close = item.get("f18")
                # Accept if has price OR has previous close (market closed)
                has_data = (price_val is not None and price_val != "" and price_val != "-") or (prev_close is not None and prev_close != "" and prev_close != "-")
                if not has_data:
                    continue
                # Use prev_close as price when market closed
                if price_val is None or price_val == "" or price_val == "-":
                    price_val = prev_close
                # Stock price from API is in fen (分), convert to yuan
                raw_price = item.get("f2")
                if raw_price and raw_price != "-":
                    try:
                        raw_price = str(float(raw_price) / 100)
                    except:
                        pass
                stocks.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": fmt(raw_price),
                    "change_pct": fmt(item.get("f3")),
                    "change_amt": fmt(item.get("f4")),
                    "volume": fmt_vol(item.get("f5")),
                    "amount": fmt_amt(item.get("f6")),
                    "turnover_rate": fmt(item.get("f8")),
                    "pe": fmt(item.get("f9")),
                    "volume_ratio": fmt(item.get("f10")),
                    "high": fmt(item.get("f15")),
                    "low": fmt(item.get("f16")),
                    "open": fmt(item.get("f17")),
                    "prev_close": fmt(item.get("f18")),
                    "market_cap": fmt_mcap(item.get("f20")),
                    "circ_market_cap": fmt_mcap(item.get("f21")),
                    "pb": fmt(item.get("f23")),
                    "change_60d": fmt(item.get("f24")),
                    "change_1y": fmt(item.get("f25")),
                    "industry": item.get("f100", ""),
                    "update_time": item.get("f124", ""),
                })
        return stocks
    except Exception as e:
        print(f"stock_service error: {e}")
        return []


def search_stock(keyword):
    """搜索股票"""
    url = "https://searchadapter.eastmoney.com/api/suggest/get"
    params = {
        "input": keyword,
        "type": "14",
        "token": "D43BF722C8E33BDC906FB84D85E326E8",
        "count": "10"
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10, proxies={"http": None, "https": None})
        data = resp.json()
        
        stocks = []
        if data.get("QuotationCodeTable", {}).get("Data"):
            for item in data["QuotationCodeTable"]["Data"]:
                code = item.get("Code", "")
                market_id = item.get("MktNum", "")
                # 补全市场前缀
                if market_id and not code.startswith(("0", "3", "6", "4", "8")):
                    pass  # 保持原样
                price_val = item.get("f2")
                prev_close = item.get("f18")
                # Accept if has price OR has previous close (market closed)
                has_data = (price_val is not None and price_val != "" and price_val != "-") or (prev_close is not None and prev_close != "" and prev_close != "-")
                if not has_data:
                    continue
                # Use prev_close as price when market closed
                if price_val is None or price_val == "" or price_val == "-":
                    price_val = prev_close
                stocks.append({
                    "code": code,
                    "name": item.get("Name", ""),
                    "market": item.get("Market", ""),
                    "market_id": market_id,
                })
        return stocks[:10]
    except:
        return []


def get_stock_detail(code):
    """获取单只股票实时行情"""
    # 判断市场
    secid = get_secid(code)
    if not secid:
        return None
    
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": secid,
        "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171",
        "_": int(time.time() * 1000)
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10, proxies={"http": None, "https": None})
        data = resp.json()
        if data.get("data"):
            d = data["data"]
            return {
                "code": d.get("f57", code),
                "name": d.get("f58", ""),
                "price": str(float(d.get("f43", 0)) / 100) if d.get("f43") else "",
                "high": d.get("f44", ""),
                "low": d.get("f45", ""),
                "open": d.get("f46", ""),
                "volume": fmt_vol(d.get("f47")),
                "amount": fmt_amt(d.get("f48")),
                "change_pct": d.get("f170", ""),
                "change_amt": d.get("f169", ""),
                "turnover_rate": d.get("f168", ""),
                "pe": d.get("f162", ""),
                "market_cap": fmt_mcap(d.get("f116")),
                "circ_market_cap": fmt_mcap(d.get("f117")),
                "amplitude": d.get("f50", ""),
                "volume_ratio": d.get("f167", ""),
                "prev_close": d.get("f60", ""),
            }
        return None
    except:
        return None


def get_stock_history(code, days=30):
    """获取股票K线数据"""
    secid = get_secid(code)
    if not secid:
        return []
    
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日K
        "fqt": "1",    # 前复权
        "end": "20500101",
        "lmt": str(days),
        "_": int(time.time() * 1000)
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10, proxies={"http": None, "https": None})
        data = resp.json()
        
        history = []
        if data.get("data") and data["data"].get("klines"):
            for line in data["data"]["klines"]:
                parts = line.split(",")
                if len(parts) >= 8:
                    history.append({
                        "date": parts[0],
                        "open": parts[1],
                        "close": parts[2],
                        "high": parts[3],
                        "low": parts[4],
                        "volume": parts[5],
                        "amount": parts[6],
                        "change_pct": parts[8] if len(parts) > 8 else "",
                    })
        return history
    except:
        return []


def get_secid(code):
    """根据代码推断市场secid"""
    c = str(code).strip()
    if not c:
        return None
    # 纯数字：A股
    if c.isdigit():
        if c.startswith(("6", "9")):
            return f"1.{c}"      # 上海
        elif c.startswith(("0", "3", "2")):
            return f"0.{c}"      # 深圳
        elif c.startswith(("4", "8")):
            return f"0.{c}"      # 北交所
    # 含字母：港股/美股
    if c.startswith("HK"):
        return f"116.{c[2:]}" if len(c) > 2 else None
    # 美股（纯字母代码）
    if c.isalpha():
        return f"105.{c}"  # 默认纳斯达克
    return None


# 格式化函数
def fmt(v):
    if v is None or v == "" or v == "-":
        return "-"
    try:
        n = float(v)
        if n == int(n):
            return str(int(n))
        return f"{n:.2f}"
    except:
        return str(v)

def fmt_vol(v):
    """成交量格式化"""
    if v is None or v == "" or v == "-":
        return "-"
    try:
        n = float(v)
        if n >= 1e8:
            return f"{n/1e8:.1f}亿"
        elif n >= 1e4:
            return f"{n/1e4:.1f}万"
        return str(int(n))
    except:
        return str(v)

def fmt_amt(v):
    """成交额格式化"""
    if v is None or v == "" or v == "-":
        return "-"
    try:
        n = float(v)
        if n >= 1e8:
            return f"{n/1e8:.1f}亿"
        elif n >= 1e4:
            return f"{n/1e4:.1f}万"
        return str(int(n))
    except:
        return str(v)

def fmt_mcap(v):
    """市值格式化"""
    if v is None or v == "" or v == "-":
        return "-"
    try:
        n = float(v)
        if n >= 1e12:
            return f"{n/1e12:.2f}万亿"
        elif n >= 1e8:
            return f"{n/1e8:.0f}亿"
        return str(int(n))
    except:
        return str(v)

print("stock_service OK")