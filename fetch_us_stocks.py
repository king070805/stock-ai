#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_us_stocks.py - 使用 agent-browser 从 Yahoo Finance 抓取美股热门数据

用法:
    python fetch_us_stocks.py                      # 默认按涨跌幅排序，取20条
    python fetch_us_stocks.py --sort volume        # 按成交量排序
    python fetch_us_stocks.py --sort amount        # 按成交额排序
    python fetch_us_stocks.py --size 50             # 取50条数据

数据源优先级:
    1. agent-browser (浏览器自动化抓取 Yahoo Finance)
    2. yfinance (Python 库)
    3. mock 数据 (兜底)
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime

# ============ 配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "us_stocks.json")

YAHOO_URL = "https://finance.yahoo.com/markets/active-us/"
BROWSER_TIMEOUT = 60  # agent-browser 超时秒数
YFINANCE_TIMEOUT = 30  # yfinance 超时秒数

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("fetch_us_stocks")

# ============ Mock 数据 ============
MOCK_STOCKS = [
    {"code": "AAPL", "name": "Apple Inc.", "price": "198.42", "change_pct": "+1.29",
     "change_amt": "+2.53", "volume": "52.0M", "amount": "10.3B",
     "market_cap": "3.05T", "pe": "30.50", "high": "199.50", "low": "196.80",
     "open": "197.00", "prev_close": "195.89"},
    {"code": "MSFT", "name": "Microsoft Corp.", "price": "420.15", "change_pct": "+0.39",
     "change_amt": "+1.65", "volume": "21.0M", "amount": "8.8B",
     "market_cap": "3.12T", "pe": "35.10", "high": "422.00", "low": "418.00",
     "open": "419.50", "prev_close": "418.50"},
    {"code": "NVDA", "name": "NVIDIA Corp.", "price": "875.28", "change_pct": "+1.76",
     "change_amt": "+15.17", "volume": "41.0M", "amount": "35.9B",
     "market_cap": "2.15T", "pe": "68.20", "high": "880.00", "low": "865.00",
     "open": "868.00", "prev_close": "860.11"},
    {"code": "GOOGL", "name": "Alphabet Inc.", "price": "142.65", "change_pct": "+1.03",
     "change_amt": "+1.45", "volume": "28.0M", "amount": "4.0B",
     "market_cap": "1.76T", "pe": "25.80", "high": "143.50", "low": "141.00",
     "open": "141.80", "prev_close": "141.20"},
    {"code": "AMZN", "name": "Amazon.com Inc.", "price": "185.60", "change_pct": "+0.85",
     "change_amt": "+1.57", "volume": "35.0M", "amount": "6.5B",
     "market_cap": "1.93T", "pe": "58.30", "high": "186.50", "low": "184.00",
     "open": "184.50", "prev_close": "184.03"},
    {"code": "META", "name": "Meta Platforms", "price": "505.75", "change_pct": "+2.10",
     "change_amt": "+10.45", "volume": "18.0M", "amount": "9.1B",
     "market_cap": "1.29T", "pe": "28.40", "high": "508.00", "low": "498.00",
     "open": "500.00", "prev_close": "495.30"},
    {"code": "TSLA", "name": "Tesla Inc.", "price": "248.50", "change_pct": "-1.51",
     "change_amt": "-3.80", "volume": "98.0M", "amount": "24.4B",
     "market_cap": "790.0B", "pe": "52.00", "high": "255.00", "low": "245.00",
     "open": "252.00", "prev_close": "252.30"},
    {"code": "BRK-B", "name": "Berkshire Hathaway", "price": "412.80", "change_pct": "+0.15",
     "change_amt": "+0.62", "volume": "3.5M", "amount": "1.4B",
     "market_cap": "890.0B", "pe": "9.80", "high": "414.00", "low": "411.00",
     "open": "412.00", "prev_close": "412.18"},
    {"code": "JPM", "name": "JPMorgan Chase", "price": "205.30", "change_pct": "+0.68",
     "change_amt": "+1.39", "volume": "8.0M", "amount": "1.6B",
     "market_cap": "590.0B", "pe": "12.10", "high": "206.50", "low": "203.50",
     "open": "204.00", "prev_close": "203.91"},
    {"code": "V", "name": "Visa Inc.", "price": "282.40", "change_pct": "+0.32",
     "change_amt": "+0.90", "volume": "6.0M", "amount": "1.7B",
     "market_cap": "580.0B", "pe": "31.50", "high": "283.50", "low": "280.50",
     "open": "281.00", "prev_close": "281.50"},
    {"code": "NFLX", "name": "Netflix Inc.", "price": "628.90", "change_pct": "+1.85",
     "change_amt": "+11.43", "volume": "5.0M", "amount": "3.1B",
     "market_cap": "270.0B", "pe": "44.20", "high": "632.00", "low": "620.00",
     "open": "622.00", "prev_close": "617.47"},
    {"code": "AMD", "name": "Advanced Micro Devices", "price": "168.50", "change_pct": "+2.30",
     "change_amt": "+3.79", "volume": "42.0M", "amount": "7.1B",
     "market_cap": "270.0B", "pe": "280.00", "high": "170.00", "low": "165.00",
     "open": "166.00", "prev_close": "164.71"},
    {"code": "BABA", "name": "Alibaba Group", "price": "78.65", "change_pct": "-0.95",
     "change_amt": "-0.76", "volume": "12.0M", "amount": "0.9B",
     "market_cap": "200.0B", "pe": "10.20", "high": "80.00", "low": "77.50",
     "open": "79.50", "prev_close": "79.41"},
    {"code": "PDD", "name": "PDD Holdings", "price": "132.80", "change_pct": "+1.60",
     "change_amt": "+2.09", "volume": "9.0M", "amount": "1.2B",
     "market_cap": "170.0B", "pe": "18.50", "high": "134.00", "low": "131.00",
     "open": "131.50", "prev_close": "130.71"},
    {"code": "NIO", "name": "NIO Inc.", "price": "5.82", "change_pct": "+3.20",
     "change_amt": "+0.18", "volume": "45.0M", "amount": "0.3B",
     "market_cap": "9.8B", "pe": "-", "high": "5.95", "low": "5.60",
     "open": "5.65", "prev_close": "5.64"},
    {"code": "JD", "name": "JD.com Inc.", "price": "35.20", "change_pct": "+0.86",
     "change_amt": "+0.30", "volume": "8.0M", "amount": "0.3B",
     "market_cap": "55.0B", "pe": "11.80", "high": "35.80", "low": "34.50",
     "open": "34.80", "prev_close": "34.90"},
    {"code": "DIS", "name": "Walt Disney Co.", "price": "112.40", "change_pct": "-0.45",
     "change_amt": "-0.51", "volume": "7.0M", "amount": "0.8B",
     "market_cap": "205.0B", "pe": "72.50", "high": "113.50", "low": "111.50",
     "open": "113.00", "prev_close": "112.91"},
    {"code": "BA", "name": "Boeing Co.", "price": "178.90", "change_pct": "+1.25",
     "change_amt": "+2.21", "volume": "5.0M", "amount": "0.9B",
     "market_cap": "110.0B", "pe": "-", "high": "180.50", "low": "176.00",
     "open": "177.00", "prev_close": "176.69"},
    {"code": "INTC", "name": "Intel Corp.", "price": "30.15", "change_pct": "-0.66",
     "change_amt": "-0.20", "volume": "32.0M", "amount": "1.0B",
     "market_cap": "130.0B", "pe": "-", "high": "30.80", "low": "29.80",
     "open": "30.50", "prev_close": "30.35"},
    {"code": "CRM", "name": "Salesforce Inc.", "price": "255.60", "change_pct": "+0.75",
     "change_amt": "+1.90", "volume": "5.0M", "amount": "1.3B",
     "market_cap": "250.0B", "pe": "48.30", "high": "257.00", "low": "253.00",
     "open": "254.00", "prev_close": "253.70"},
]


# ============ 工具函数 ============

def _parse_number(text):
    """将带后缀的数字文本转换为 float（用于排序）"""
    if not text:
        return 0.0
    text = str(text).strip().replace(",", "").replace("+", "")
    # 处理后缀: K, M, B, T
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    for suffix, mult in multipliers.items():
        if text.upper().endswith(suffix):
            try:
                return float(text[:-1].strip()) * mult
            except ValueError:
                return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _sort_stocks(stocks, sort_by):
    """按指定字段排序股票列表"""
    if sort_by == "change":
        stocks.sort(key=lambda s: abs(_parse_number(s.get("change_pct", "0"))), reverse=True)
    elif sort_by == "amount":
        stocks.sort(key=lambda s: _parse_number(s.get("amount", "0")), reverse=True)
    elif sort_by == "volume":
        stocks.sort(key=lambda s: _parse_number(s.get("volume", "0")), reverse=True)
    return stocks


def save_to_json(data, filepath):
    """保存数据到 JSON 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"数据已保存到: {filepath}")


# ============ 数据抓取方法 ============

def fetch_via_agent_browser(size=20):
    """
    方法1: 使用 agent-browser CLI 从 Yahoo Finance 抓取数据
    """
    logger.info("尝试使用 agent-browser 抓取 Yahoo Finance 数据...")

    # 检查 agent-browser 是否可用
    try:
        result = subprocess.run(
            ["agent-browser", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            logger.warning("agent-browser 不可用 (返回码非0)")
            return None
        logger.info(f"agent-browser 版本: {result.stdout.strip()}")
    except FileNotFoundError:
        logger.warning("agent-browser 未安装，将尝试 yfinance")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("agent-browser 版本检查超时")
        return None
    except Exception as e:
        logger.warning(f"agent-browser 检查异常: {e}")
        return None

    # 构建 eval 脚本 - 从 Yahoo Finance 页面提取表格数据
    eval_script = r"""
JSON.stringify(
  Array.from(document.querySelectorAll('tr[data-test="quote-row"], table[data-test="active-tickers-table"] tbody tr'))
    .slice(0, %d)
    .map(row => {
      const cells = row.querySelectorAll('td');
      return {
        symbol: cells[0]?.textContent?.trim() || '',
        name: cells[1]?.textContent?.trim() || '',
        price: cells[2]?.textContent?.trim() || '',
        change: cells[3]?.textContent?.trim() || '',
        change_pct: cells[4]?.textContent?.trim() || '',
        volume: cells[5]?.textContent?.trim() || '',
        avg_volume: cells[6]?.textContent?.trim() || '',
        market_cap: cells[7]?.textContent?.trim() || '',
        pe_ratio: cells[8]?.textContent?.trim() || '',
      };
    })
    .filter(s => s.symbol && s.symbol.length > 0)
)
""" % (size + 10)  # 多取几条以防过滤

    # 依次执行 agent-browser 命令链
    commands = [
        ["agent-browser", "open", YAHOO_URL],
        ["agent-browser", "wait", "--load", "networkidle"],
        ["agent-browser", "eval", "--stdin"],
        ["agent-browser", "close"],
    ]

    try:
        # 1. 打开页面
        logger.info(f"打开页面: {YAHOO_URL}")
        result = subprocess.run(
            commands[0], capture_output=True, text=True, timeout=BROWSER_TIMEOUT
        )
        if result.returncode != 0:
            logger.error(f"打开页面失败: {result.stderr.strip()}")
            return None

        # 2. 等待加载
        logger.info("等待页面加载完成 (networkidle)...")
        result = subprocess.run(
            commands[1], capture_output=True, text=True, timeout=BROWSER_TIMEOUT
        )
        if result.returncode != 0:
            logger.warning(f"等待加载警告: {result.stderr.strip()}")

        # 3. 执行 JS 提取数据
        logger.info("执行 JavaScript 提取表格数据...")
        result = subprocess.run(
            commands[2],
            input=eval_script,
            capture_output=True, text=True, timeout=BROWSER_TIMEOUT
        )
        if result.returncode != 0:
            logger.error(f"JS 执行失败: {result.stderr.strip()}")
            return None

        # 解析 JSON 输出
        raw_output = result.stdout.strip()
        logger.debug(f"agent-browser eval 原始输出: {raw_output[:500]}")

        # 尝试从输出中提取 JSON（可能包含在引号或多余文本中）
        json_str = raw_output
        # 如果输出被引号包裹，去掉引号
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1]
            # 处理转义字符
            json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')

        stocks_raw = json.loads(json_str)

        if not stocks_raw or not isinstance(stocks_raw, list):
            logger.warning("agent-browser 返回空数据")
            return None

        # 4. 关闭浏览器
        try:
            subprocess.run(
                commands[3], capture_output=True, text=True, timeout=10
            )
        except Exception:
            pass

        # 转换为统一格式
        stocks = []
        for item in stocks_raw:
            symbol = item.get("symbol", "").strip()
            if not symbol:
                continue

            # 解析 change 和 change_pct
            change_text = item.get("change", "")
            change_pct_text = item.get("change_pct", "")

            # change_pct 可能是 "+1.29%" 或 "+1.29" 格式
            if change_pct_text and change_pct_text.endswith("%"):
                change_pct_text = change_pct_text[:-1]

            stocks.append({
                "code": symbol,
                "name": item.get("name", ""),
                "price": item.get("price", ""),
                "change_pct": change_pct_text,
                "change_amt": change_text,
                "volume": item.get("volume", ""),
                "amount": "",  # Yahoo 页面通常不直接提供成交额
                "market_cap": item.get("market_cap", ""),
                "pe": item.get("pe_ratio", ""),
                "high": "",
                "low": "",
                "open": "",
                "prev_close": "",
            })

        logger.info(f"agent-browser 成功抓取 {len(stocks)} 条数据")
        return stocks

    except subprocess.TimeoutExpired:
        logger.error("agent-browser 执行超时")
        # 尝试关闭浏览器
        try:
            subprocess.run(["agent-browser", "close"], capture_output=True, text=True, timeout=10)
        except Exception:
            pass
        return None
    except json.JSONDecodeError as e:
        logger.error(f"解析 agent-browser 输出失败: {e}")
        return None
    except Exception as e:
        logger.error(f"agent-browser 抓取异常: {e}")
        # 尝试关闭浏览器
        try:
            subprocess.run(["agent-browser", "close"], capture_output=True, text=True, timeout=10)
        except Exception:
            pass
        return None


def fetch_via_yfinance(size=20):
    """
    方法2: 使用 yfinance 库获取美股数据
    """
    logger.info("尝试使用 yfinance 获取美股数据...")

    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance 未安装")
        return None

    # 热门美股代码池
    hot_symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
        "JPM", "V", "JNJ", "WMT", "MA", "PG", "UNH", "HD", "DIS", "NFLX",
        "PYPL", "AMD", "INTC", "CRM", "ORCL", "CSCO", "QCOM", "BA", "COIN",
        "SQ", "UBER", "ABNB", "SNOW", "PLTR", "SOFI", "RIVN", "LCID",
        "NIO", "PDD", "BABA", "JD", "TME", "NTES", "BIDU", "LI", "XP",
    ]

    fetch_symbols = hot_symbols[:size + 10]
    stocks = []

    for symbol in fetch_symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d", timeout=YFINANCE_TIMEOUT)

            if hist.empty:
                continue

            price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else price
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close and prev_close != 0 else 0
            change_amt = price - prev_close

            volume = hist["Volume"].iloc[-1] if "Volume" in hist.columns else 0
            high = hist["High"].iloc[-1] if "High" in hist.columns else price
            low = hist["Low"].iloc[-1] if "Low" in hist.columns else price
            open_price = hist["Open"].iloc[-1] if "Open" in hist.columns else price

            # 获取额外信息
            try:
                full_info = ticker.info
                pe = full_info.get("trailingPE") or full_info.get("forwardPE")
                mcap = full_info.get("marketCap", 0)
                name = full_info.get("shortName") or full_info.get("longName", symbol)
            except Exception:
                pe = None
                mcap = 0
                name = symbol

            # 格式化成交量
            vol_str = ""
            if volume >= 1e6:
                vol_str = f"{volume / 1e6:.1f}M"
            elif volume >= 1e3:
                vol_str = f"{volume / 1e3:.1f}K"
            else:
                vol_str = str(int(volume))

            # 格式化市值
            mcap_str = ""
            if mcap >= 1e12:
                mcap_str = f"{mcap / 1e12:.2f}T"
            elif mcap >= 1e9:
                mcap_str = f"{mcap / 1e9:.1f}B"
            elif mcap >= 1e6:
                mcap_str = f"{mcap / 1e6:.1f}M"
            else:
                mcap_str = str(int(mcap))

            # 格式化成交额（估算: volume * price）
            amount_val = volume * price
            amt_str = ""
            if amount_val >= 1e9:
                amt_str = f"{amount_val / 1e9:.1f}B"
            elif amount_val >= 1e6:
                amt_str = f"{amount_val / 1e6:.1f}M"
            else:
                amt_str = f"{amount_val / 1e3:.1f}K"

            stocks.append({
                "code": symbol,
                "name": name,
                "price": f"{price:.2f}",
                "change_pct": f"{change_pct:+.2f}",
                "change_amt": f"{change_amt:+.2f}",
                "volume": vol_str,
                "amount": amt_str,
                "market_cap": mcap_str,
                "pe": f"{pe:.2f}" if pe else "-",
                "high": f"{high:.2f}",
                "low": f"{low:.2f}",
                "open": f"{open_price:.2f}",
                "prev_close": f"{prev_close:.2f}",
            })
        except Exception as e:
            logger.debug(f"yfinance 获取 {symbol} 失败: {e}")
            continue

    if stocks:
        logger.info(f"yfinance 成功获取 {len(stocks)} 条数据")
        return stocks
    else:
        logger.warning("yfinance 未能获取任何数据")
        return None


def fetch_mock_data(size=20):
    """
    方法3: 返回 mock 兜底数据
    """
    logger.info("使用 mock 兜底数据")
    return [dict(s) for s in MOCK_STOCKS[:size]]


# ============ 主流程 ============

def fetch_us_stocks(sort_by="change", size=20, output_path=None):
    """
    抓取美股热门数据的主函数

    优先级: agent-browser > yfinance > mock
    """
    if output_path is None:
        output_path = OUTPUT_FILE

    logger.info(f"开始抓取美股数据: sort_by={sort_by}, size={size}")

    stocks = None

    # 方法1: agent-browser
    stocks = fetch_via_agent_browser(size)

    # 方法2: yfinance
    if not stocks:
        stocks = fetch_via_yfinance(size)

    # 方法3: mock
    if not stocks:
        stocks = fetch_mock_data(size)

    # 排序
    stocks = _sort_stocks(stocks, sort_by)
    stocks = stocks[:size]

    # 构建输出数据
    output = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sort": sort_by,
        "stocks": stocks,
    }

    # 保存到文件
    save_to_json(output, output_path)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="从 Yahoo Finance 抓取美股热门数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fetch_us_stocks.py                      # 默认按涨跌幅排序，取20条
  python fetch_us_stocks.py --sort volume        # 按成交量排序
  python fetch_us_stocks.py --sort amount        # 按成交额排序
  python fetch_us_stocks.py --size 50            # 取50条数据
  python fetch_us_stocks.py --sort change --size 10
        """,
    )
    parser.add_argument(
        "--sort",
        choices=["change", "amount", "volume"],
        default="change",
        help="排序方式: change=涨跌幅, amount=成交额, volume=成交量 (默认: change)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=20,
        help="获取数据条数 (默认: 20)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=OUTPUT_FILE,
        help=f"输出 JSON 文件路径 (默认: {OUTPUT_FILE})",
    )

    args = parser.parse_args()

    # 如果指定了自定义输出路径，覆盖全局变量
    output_path = args.output if args.output else OUTPUT_FILE

    result = fetch_us_stocks(sort_by=args.sort, size=args.size, output_path=output_path)

    # 打印摘要
    print(f"\n{'='*60}")
    print(f"美股热门数据抓取完成")
    print(f"  数据源: agent-browser / yfinance / mock (自动选择)")
    print(f"  排序: {args.sort}")
    print(f"  数量: {len(result['stocks'])}")
    print(f"  更新时间: {result['update_time']}")
    print(f"  保存路径: {output_path}")
    print(f"{'='*60}\n")

    # 打印前5条数据预览
    for i, stock in enumerate(result["stocks"][:5]):
        print(f"  {i+1}. {stock['code']:8s} {stock['name']:30s} "
              f"价格: {stock['price']:>10s}  涨跌幅: {stock['change_pct']:>8s}")
    if len(result["stocks"]) > 5:
        print(f"  ... 共 {len(result['stocks'])} 条")


if __name__ == "__main__":
    main()
