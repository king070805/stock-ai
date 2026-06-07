# services/stock_service.py - 股票数据服务
import requests
import json
import re
import time
from datetime import datetime
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

def get_stock_list(market="a", sort_by="change", page=1, size=60):
    """获取股票列表/排行（多级回退）"""
    
    # 美股使用 Yahoo Finance
    if market == "us":
        return get_us_stock_list(sort_by=sort_by, size=size)
    
    # A股/港股：先尝试读取本地缓存（5分钟内）
    if market in ("a", "sh", "sz"):
        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", f"a_stocks_{sort_by}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                update_time = cached.get("update_time", "")
                if update_time:
                    from datetime import datetime, timedelta
                    cached_time = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - cached_time < timedelta(minutes=5):
                        stocks = cached.get("stocks", [])
                        if stocks:
                            return stocks[:size]
            except:
                pass
    
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
        if stocks:
            return stocks
    except Exception as e:
        print(f"push2 clist error: {e}")
    
    # === Fallback 1: 腾讯行情 API ===
    print("push2 clist failed, falling back to Tencent API")
    tencent_stocks = _get_stock_list_tencent(sort_by, size)
    if tencent_stocks:
        return tencent_stocks
    
    # === Fallback 2: 新浪财经 API ===
    print("Tencent API failed, falling back to Sina API")
    sina_stocks = _get_stock_list_sina(sort_by, size)
    if sina_stocks:
        return sina_stocks
    
    # === Fallback 3: 本地缓存（即使过期）===
    print("Sina API failed, falling back to local cache")
    if market in ("a", "sh", "sz"):
        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", f"a_stocks_{sort_by}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                stocks = cached.get("stocks", [])
                if stocks:
                    return stocks[:size]
            except:
                pass
    
    return []


# 腾讯行情热门股代码池（覆盖AI算力/低空经济/高股息三大赛道 + 其他热门）
_TENCENT_HOT_STOCKS = {
    "amount": [
        # ========== 其他热门 ==========
        "sh600519","sz000858","sz300750","sh601318","sz000725",
        "sh600036","sz002594","sz300059","sh601012","sz000001",
        "sh600900","sz300274","sh601166","sz002475","sz300760",
        "sh600276","sz000625","sh601398","sz002415","sz300014",
        # ========== AI算力产业链（50只）==========
        # AI芯片
        "sz002230","sz300033","sh688111","sh688256","sh688981",
        "sh688012","sh688041","sh688525",
        # 光模块/CPO
        "sz300502","sz300308","sz300394","sz300548","sz002281",
        "sz000938",
        # AI服务器
        "sz000977","sh603019","sh601138","sz002236",
        # 液冷/散热
        "sz002837","sz300499","sz301018","sh603912",
        # PCB/覆铜板
        "sz002463","sh600183","sh603228","sz300739",
        # 存储芯片
        "sh603986","sh688110","sz300223","sz000021",
        # 电源/变压器
        "sz300274","sz002335","sh600885",
        # CPO/光引擎
        "sh601231","sh603306","sz002384","sz300620",
        # 算力租赁/IDC
        "sh600845","sh600728","sz300017",
        # 半导体设备
        "sz002371","sh688082","sh688072",
        # ========== 低空经济（25只）==========
        "sz002085","sh600760","sh688568","sz300696","sh688297",
        "sz002389","sh600118","sz000768","sh600316","sz002013",
        "sh600038","sz300900","sz002151","sz300114","sz002025",
        "sh600372","sh600391","sz300159","sz002179","sh600967",
        "sz300424","sz002933","sz300411","sh603261","sh688070",
        # ========== 高股息（40只）==========
        "sh601939","sh601288","sh601088","sh600585","sh600028",
        "sh601857","sh600019","sh601988","sh601328","sh600016",
        "sh601998","sh601818","sh601186","sh601668","sh601390",
        "sh601728","sh600048","sh600104","sh600887","sh600690",
        "sh600741","sh600660","sh600276","sh600309","sh600406",
        "sh600089","sh600115","sh601111","sh600029","sh600377",
        "sh600350","sh600018","sh600017","sh600508","sh601699",
        "sh601225","sh601088","sh600900","sh601398","sh600036",
    ],
    "change": [
        # ========== 其他热门 ==========
        "sz300750","sz000725","sz300059","sh601012","sz002594",
        "sz300274","sh601318","sz002475","sh600519","sz000858",
        "sz300760","sh600036","sh601166","sz000001","sh600900",
        "sh601398","sz002415","sh600276","sz000625","sz300014",
        # ========== AI算力产业链（50只）==========
        "sz002230","sz300033","sh688111","sh688256","sh688981",
        "sh688012","sh688041","sh688525","sz300502","sz300308",
        "sz300394","sz300548","sz002281","sz000938","sz000977",
        "sh603019","sh601138","sz002236","sz002837","sz300499",
        "sz301018","sh603912","sz002463","sh600183","sh603228",
        "sz300739","sh603986","sh688110","sz300223","sz000021",
        "sz300274","sz002335","sh600885","sh601231","sh603306",
        "sz002384","sz300620","sh600845","sh600728","sz300017",
        "sz002371","sh688082","sh688072",
        # ========== 低空经济（25只）==========
        "sz002085","sh600760","sh688568","sz300696","sh688297",
        "sz002389","sh600118","sz000768","sh600316","sz002013",
        "sh600038","sz300900","sz002151","sz300114","sz002025",
        "sh600372","sh600391","sz300159","sz002179","sh600967",
        "sz300424","sz002933","sz300411","sh603261","sh688070",
        # ========== 高股息（40只）==========
        "sh601939","sh601288","sh601088","sh600585","sh600028",
        "sh601857","sh600019","sh601988","sh601328","sh600016",
        "sh601998","sh601818","sh601186","sh601668","sh601390",
        "sh601728","sh600048","sh600104","sh600887","sh600690",
        "sh600741","sh600660","sh600276","sh600309","sh600406",
        "sh600089","sh600115","sh601111","sh600029","sh600377",
        "sh600350","sh600018","sh600017","sh600508","sh601699",
        "sh601225","sh601088","sh600900","sh601398","sh600036",
    ],
    "volume": [
        # ========== 其他热门 ==========
        "sz000725","sz300750","sz000858","sh601318","sz002594",
        "sh600519","sz300059","sh600036","sz300274","sh601012",
        "sz002475","sz300760","sh601166","sz000001","sh600900",
        "sh601398","sz002415","sh600276","sz000625","sz300014",
        # ========== AI算力产业链（50只）==========
        "sz002230","sz300033","sh688111","sh688256","sh688981",
        "sh688012","sh688041","sh688525","sz300502","sz300308",
        "sz300394","sz300548","sz002281","sz000938","sz000977",
        "sh603019","sh601138","sz002236","sz002837","sz300499",
        "sz301018","sh603912","sz002463","sh600183","sh603228",
        "sz300739","sh603986","sh688110","sz300223","sz000021",
        "sz300274","sz002335","sh600885","sh601231","sh603306",
        "sz002384","sz300620","sh600845","sh600728","sz300017",
        "sz002371","sh688082","sh688072",
        # ========== 低空经济（25只）==========
        "sz002085","sh600760","sh688568","sz300696","sh688297",
        "sz002389","sh600118","sz000768","sh600316","sz002013",
        "sh600038","sz300900","sz002151","sz300114","sz002025",
        "sh600372","sh600391","sz300159","sz002179","sh600967",
        "sz300424","sz002933","sz300411","sh603261","sh688070",
        # ========== 高股息（40只）==========
        "sh601939","sh601288","sh601088","sh600585","sh600028",
        "sh601857","sh600019","sh601988","sh601328","sh600016",
        "sh601998","sh601818","sh601186","sh601668","sh601390",
        "sh601728","sh600048","sh600104","sh600887","sh600690",
        "sh600741","sh600660","sh600276","sh600309","sh600406",
        "sh600089","sh600115","sh601111","sh600029","sh600377",
        "sh600350","sh600018","sh600017","sh600508","sh601699",
        "sh601225","sh601088","sh600900","sh601398","sh600036",
    ],
}

def _get_stock_list_sina(sort_by="change", size=20):
    """通过新浪财经API获取A股排行数据"""
    # 新浪财经API: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
    # 或使用: https://hq.sinajs.cn/list=sh600000,sz000001
    # 新浪有一个获取涨幅排行的接口
    
    sort_map = {
        "change": "changepercent",  # 涨跌幅
        "amount": "amount",         # 成交额
        "volume": "volume",         # 成交量
    }
    
    url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    params = {
        "page": 1,
        "num": size,
        "sort": sort_map.get(sort_by, "changepercent"),
        "asc": 0 if sort_by in ("change", "amount", "volume") else 1,
        "node": "hs_a",  # 沪深A股
        "symbol": "",
    }
    
    try:
        resp = requests.get(url, params=params, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "http://finance.sina.com.cn",
        }, timeout=10, proxies={"http": None, "https": None})
        
        if resp.status_code != 200:
            return []
        
        # 新浪返回的是JSONP格式，需要解析
        text = resp.text
        # 尝试解析JSON
        try:
            data = json.loads(text)
        except:
            # 可能是JSONP格式，去掉回调函数名
            if text.startswith("var"):
                text = text.split("=", 1)[1].strip().rstrip(";")
                data = json.loads(text)
            else:
                return []
        
        stocks = []
        for item in data if isinstance(data, list) else data.get("data", []):
            stocks.append({
                "code": item.get("symbol", item.get("code", "")),
                "name": item.get("name", ""),
                "price": str(item.get("trade", item.get("price", ""))),
                "change_pct": str(item.get("changepercent", item.get("change_pct", ""))),
                "change_amt": str(item.get("pricechange", "")),
                "volume": fmt_vol(item.get("volume", 0)),
                "amount": fmt_amt(item.get("amount", 0)),
                "turnover_rate": str(item.get("turnoverratio", "")),
                "pe": str(item.get("per", item.get("pe", ""))),
                "volume_ratio": "",
                "high": str(item.get("high", "")),
                "low": str(item.get("low", "")),
                "open": str(item.get("open", "")),
                "prev_close": str(item.get("settlement", "")),
                "market_cap": fmt_mcap(item.get("mktcap", 0)),
                "circ_market_cap": fmt_mcap(item.get("nmc", 0)),
                "pb": str(item.get("pb", "")),
                "change_60d": "",
                "change_1y": "",
                "industry": item.get("industry", ""),
                "update_time": "",
            })
        
        return stocks[:size]
    except Exception as e:
        print(f"sina API error: {e}")
        return []


def _get_stock_list_tencent(sort_by="change", size=20):
    """通过腾讯行情 API 获取热门股列表"""
    codes = _TENCENT_HOT_STOCKS.get(sort_by, _TENCENT_HOT_STOCKS["change"])
    fetch_codes = codes[:size]
    
    url = "https://qt.gtimg.cn/q=" + ",".join(fetch_codes)
    tencent_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://gu.qq.com/",
    }
    
    try:
        resp = requests.get(url, headers=tencent_headers, timeout=10, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            return []
        
        stocks = []
        for line in resp.text.strip().split(";"):
            line = line.strip()
            if not line.startswith("v_"):
                continue
            # 解析腾讯数据格式
            try:
                data_str = line.split("~")
                if len(data_str) < 45:
                    continue
                code = data_str[2]
                name = data_str[1]
                price = data_str[3]
                prev_close = data_str[4]
                open_price = data_str[5]
                volume = data_str[6]
                amount = data_str[37]  # 成交额(万)
                change_pct = data_str[32]  # 涨跌幅
                high = data_str[41]
                low = data_str[42]
                pe = data_str[52] if len(data_str) > 52 else ""
                mcap = data_str[50] if len(data_str) > 50 else ""
                
                if not price or price == "0.00":
                    continue
                
                stocks.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "change_amt": "",
                    "volume": fmt_vol(float(volume) * 100 if volume else 0),
                    "amount": fmt_amt(float(amount) * 10000 if amount else 0),
                    "turnover_rate": "",
                    "pe": fmt(pe) if pe else "-",
                    "volume_ratio": "",
                    "high": high,
                    "low": low,
                    "open": open_price,
                    "prev_close": prev_close,
                    "market_cap": fmt_mcap(float(mcap) * 10000 if mcap else 0),
                    "circ_market_cap": "",
                    "pb": "",
                    "change_60d": "",
                    "change_1y": "",
                    "industry": "",
                    "update_time": "",
                })
            except (ValueError, IndexError):
                continue
        
        # 按排序字段重新排序
        if sort_by == "change":
            stocks.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
        elif sort_by == "amount":
            # 腾讯API返回的amount字段需要解析（可能带单位）
            def parse_amount(s):
                amt = s.get("amount", "0")
                if isinstance(amt, str):
                    amt = amt.replace("万", "").replace("亿", "")
                try:
                    return float(amt) if amt else 0
                except:
                    return 0
            stocks.sort(key=parse_amount, reverse=True)
        elif sort_by == "volume":
            def parse_volume(s):
                vol = s.get("volume", "0")
                if isinstance(vol, str):
                    vol = vol.replace("万", "").replace("亿", "")
                try:
                    return float(vol) if vol else 0
                except:
                    return 0
            stocks.sort(key=parse_volume, reverse=True)
        
        return stocks[:size]
    except Exception as e:
        print(f"tencent API error: {e}")
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

# ========== 美股热门股列表 ==========
US_HOT_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "WMT", "MA", "PG", "UNH", "HD", "DIS", "NFLX",
    "PYPL", "AMD", "INTC", "CRM", "ORCL", "CSCO", "QCOM", "BA", "COIN",
    "SQ", "UBER", "ABNB", "SNOW", "PLTR", "SOFI", "RIVN", "LCID",
    "NIO", "PDD", "BABA", "JD", "TME", "NTES", "BIDU", "LI", "XP",
]

def get_us_stock_list(sort_by="change", size=20):
    """通过 Yahoo Finance 获取美股热门列表（优先读取缓存）"""
    # 1. 先尝试读取缓存文件
    cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "us_stocks.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # 检查缓存是否过期（30分钟）
            update_time = cached.get("update_time", "")
            if update_time:
                from datetime import datetime, timedelta
                try:
                    cached_time = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - cached_time < timedelta(minutes=30):
                        stocks = cached.get("stocks", [])
                        if stocks:
                            print(f"使用缓存的美股数据 (更新于 {update_time})")
                            # 排序
                            _sort_us_stocks(stocks, sort_by)
                            return stocks[:size]
                except Exception as e:
                    print(f"解析缓存时间失败: {e}")
        except Exception as e:
            print(f"读取缓存文件失败: {e}")

    # 2. 缓存不存在或过期，尝试 yfinance
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed, using mock data")
        return _get_us_mock_list(sort_by=sort_by, size=size)

    stocks = []
    fetch_symbols = US_HOT_STOCKS[:size + 10]  # 多取一些，排序后截取

    for symbol in fetch_symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            hist = ticker.history(period="2d")

            if hist.empty:
                continue

            price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else price
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close and prev_close != 0 else 0

            volume = hist["Volume"].iloc[-1] if "Volume" in hist.columns else 0

            # 获取更多信息
            try:
                full_info = ticker.info
                pe = full_info.get("trailingPE") or full_info.get("forwardPE")
                mcap = full_info.get("marketCap", 0)
                name = full_info.get("shortName") or full_info.get("longName", symbol)
                high = hist["High"].iloc[-1] if "High" in hist.columns else price
                low = hist["Low"].iloc[-1] if "Low" in hist.columns else price
                open_price = hist["Open"].iloc[-1] if "Open" in hist.columns else price
            except:
                pe = None
                mcap = 0
                name = symbol
                high = price
                low = price
                open_price = price

            stocks.append({
                "code": symbol,
                "name": name,
                "price": f"{price:.2f}",
                "change_pct": f"{change_pct:+.2f}",
                "change_amt": f"{price - prev_close:+.2f}",
                "volume": fmt_vol(volume),
                "amount": fmt_mcap(volume * price) if volume and price else "-",
                "turnover_rate": "",
                "pe": f"{pe:.2f}" if pe else "-",
                "volume_ratio": "",
                "high": f"{high:.2f}",
                "low": f"{low:.2f}",
                "open": f"{open_price:.2f}",
                "prev_close": f"{prev_close:.2f}",
                "market_cap": fmt_mcap(mcap) if mcap else "-",
                "circ_market_cap": "",
                "pb": "",
                "change_60d": "",
                "change_1y": "",
                "industry": "",
                "update_time": datetime.now().strftime("%H:%M:%S") if 'datetime' in dir() else "",
            })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            continue

    # 排序
    _sort_us_stocks(stocks, sort_by)

    return stocks[:size]


def _sort_us_stocks(stocks, sort_by="change"):
    """对美股列表进行排序（原地排序）"""
    if sort_by == "change":
        stocks.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
    elif sort_by == "amount":
        stocks.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
    elif sort_by == "volume":
        stocks.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)


def _get_us_mock_list(sort_by="change", size=20):
    """美股模拟数据兜底"""
    mock = [
        {"code": "AAPL", "name": "Apple Inc.", "price": "198.42", "change_pct": "+1.29", "pe": "30.50", "market_cap": "3.1万亿", "volume": "5200万", "amount": "103亿", "high": "199.50", "low": "196.80", "open": "197.00", "prev_close": "195.89"},
        {"code": "MSFT", "name": "Microsoft Corp.", "price": "420.15", "change_pct": "+0.39", "pe": "35.10", "market_cap": "3.1万亿", "volume": "2100万", "amount": "88亿", "high": "422.00", "low": "418.00", "open": "419.50", "prev_close": "418.50"},
        {"code": "NVDA", "name": "NVIDIA Corp.", "price": "875.28", "change_pct": "+1.76", "pe": "68.20", "market_cap": "2.2万亿", "volume": "4100万", "amount": "359亿", "high": "880.00", "low": "865.00", "open": "868.00", "prev_close": "860.11"},
        {"code": "GOOGL", "name": "Alphabet Inc.", "price": "142.65", "change_pct": "+1.03", "pe": "25.80", "market_cap": "1.8万亿", "volume": "2800万", "amount": "40亿", "high": "143.50", "low": "141.00", "open": "141.80", "prev_close": "141.20"},
        {"code": "AMZN", "name": "Amazon.com Inc.", "price": "185.60", "change_pct": "+0.85", "pe": "58.30", "market_cap": "1.9万亿", "volume": "3500万", "amount": "65亿", "high": "186.50", "low": "184.00", "open": "184.50", "prev_close": "184.03"},
        {"code": "META", "name": "Meta Platforms", "price": "505.75", "change_pct": "+2.10", "pe": "28.40", "market_cap": "1.3万亿", "volume": "1800万", "amount": "91亿", "high": "508.00", "low": "498.00", "open": "500.00", "prev_close": "495.30"},
        {"code": "TSLA", "name": "Tesla Inc.", "price": "248.50", "change_pct": "-1.51", "pe": "52.00", "market_cap": "7900亿", "volume": "9800万", "amount": "244亿", "high": "255.00", "low": "245.00", "open": "252.00", "prev_close": "252.30"},
        {"code": "BRK-B", "name": "Berkshire Hathaway", "price": "412.80", "change_pct": "+0.15", "pe": "9.80", "market_cap": "8900亿", "volume": "350万", "amount": "14亿", "high": "414.00", "low": "411.00", "open": "412.00", "prev_close": "412.18"},
        {"code": "JPM", "name": "JPMorgan Chase", "price": "205.30", "change_pct": "+0.68", "pe": "12.10", "market_cap": "5900亿", "volume": "800万", "amount": "16亿", "high": "206.50", "low": "203.50", "open": "204.00", "prev_close": "203.91"},
        {"code": "V", "name": "Visa Inc.", "price": "282.40", "change_pct": "+0.32", "pe": "31.50", "market_cap": "5800亿", "volume": "600万", "amount": "17亿", "high": "283.50", "low": "280.50", "open": "281.00", "prev_close": "281.50"},
        {"code": "NFLX", "name": "Netflix Inc.", "price": "628.90", "change_pct": "+1.85", "pe": "44.20", "market_cap": "2700亿", "volume": "500万", "amount": "31亿", "high": "632.00", "low": "620.00", "open": "622.00", "prev_close": "617.47"},
        {"code": "AMD", "name": "Advanced Micro Devices", "price": "168.50", "change_pct": "+2.30", "pe": "280.00", "market_cap": "2700亿", "volume": "4200万", "amount": "71亿", "high": "170.00", "low": "165.00", "open": "166.00", "prev_close": "164.71"},
        {"code": "BABA", "name": "Alibaba Group", "price": "78.65", "change_pct": "-0.95", "pe": "10.20", "market_cap": "2000亿", "volume": "1200万", "amount": "9亿", "high": "80.00", "low": "77.50", "open": "79.50", "prev_close": "79.41"},
        {"code": "PDD", "name": "PDD Holdings", "price": "132.80", "change_pct": "+1.60", "pe": "18.50", "market_cap": "1700亿", "volume": "900万", "amount": "12亿", "high": "134.00", "low": "131.00", "open": "131.50", "prev_close": "130.71"},
        {"code": "NIO", "name": "NIO Inc.", "price": "5.82", "change_pct": "+3.20", "pe": "-", "market_cap": "98亿", "volume": "4500万", "amount": "3亿", "high": "5.95", "low": "5.60", "open": "5.65", "prev_close": "5.64"},
        {"code": "JD", "name": "JD.com Inc.", "price": "35.20", "change_pct": "+0.86", "pe": "11.80", "market_cap": "550亿", "volume": "800万", "amount": "3亿", "high": "35.80", "low": "34.50", "open": "34.80", "prev_close": "34.90"},
        {"code": "DIS", "name": "Walt Disney Co.", "price": "112.40", "change_pct": "-0.45", "pe": "72.50", "market_cap": "2050亿", "volume": "700万", "amount": "8亿", "high": "113.50", "low": "111.50", "open": "113.00", "prev_close": "112.91"},
        {"code": "BA", "name": "Boeing Co.", "price": "178.90", "change_pct": "+1.25", "pe": "-", "market_cap": "1100亿", "volume": "500万", "amount": "9亿", "high": "180.50", "low": "176.00", "open": "177.00", "prev_close": "176.69"},
        {"code": "INTC", "name": "Intel Corp.", "price": "30.15", "change_pct": "-0.66", "pe": "-", "market_cap": "1300亿", "volume": "3200万", "amount": "10亿", "high": "30.80", "low": "29.80", "open": "30.50", "prev_close": "30.35"},
        {"code": "CRM", "name": "Salesforce Inc.", "price": "255.60", "change_pct": "+0.75", "pe": "48.30", "market_cap": "2500亿", "volume": "500万", "amount": "13亿", "high": "257.00", "low": "253.00", "open": "254.00", "prev_close": "253.70"},
    ]
    
    # 排序
    if sort_by == "change":
        mock.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
    elif sort_by == "amount":
        mock.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
    elif sort_by == "volume":
        mock.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
    
    result = mock[:size]
    # 补全缺失字段
    for s in result:
        s.setdefault("change_amt", "")
        s.setdefault("turnover_rate", "")
        s.setdefault("volume_ratio", "")
        s.setdefault("circ_market_cap", "")
        s.setdefault("pb", "")
        s.setdefault("change_60d", "")
        s.setdefault("change_1y", "")
        s.setdefault("industry", "")
        s.setdefault("update_time", "")
    return result

print("stock_service OK")