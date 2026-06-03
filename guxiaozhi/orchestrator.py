# guxiaozhi/orchestrator.py - 股小智 Agent 调度引擎
# collector() + analyst() + keeper() — 全部硬编码，不依赖外部文档

import sys, os, json, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stock_service import get_stock_detail, get_stock_history, get_stock_list
from services.us_stock_service import get_quote
from services.ai_service import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCKS_DIR = os.path.join(BASE_DIR, "data", "stocks")
USERS_DIR = os.path.join(BASE_DIR, "memory", "users")

os.makedirs(STOCKS_DIR, exist_ok=True)
os.makedirs(USERS_DIR, exist_ok=True)


# ============================================================
# 情报员 Collector — 取数据，统一格式
# ============================================================

def collector(symbol):
    """判断 A 股/美股，拉取实时数据 → 写缓存并返回"""
    symbol = str(symbol).strip().upper()

    if symbol.isdigit() or (len(symbol) == 6 and symbol.isdigit()):
        # A 股：6 位纯数字
        return _collect_a_stock(symbol)
    else:
        # 美股：含字母
        return _collect_us_stock(symbol)


def _collect_a_stock(code):
    """从东方财富获取 A 股数据"""
    detail = get_stock_detail(code)
    
    # 如果 detail API 挂了，从列表里找
    if not detail:
        stocks = get_stock_list(size=300)
        for s in stocks:
            if s["code"] == code:
                detail = s
                break
    
    if not detail:
        return {"error": f"未找到 A 股代码 {code}", "symbol": code, "market": "a"}

    data = {
        "symbol": detail.get("code", code),
        "name": detail.get("name", ""),
        "market": "a",
        "price": detail.get("price", "N/A"),
        "change_pct": detail.get("change_pct", "N/A"),
        "pe_ratio": detail.get("pe", "N/A"),
        "market_cap": detail.get("market_cap", "N/A"),
        "amount": detail.get("amount", "N/A"),
        "turnover_rate": detail.get("turnover_rate", "N/A"),
        "fetched_at": datetime.now().isoformat(),
    }

    # 写缓存
    _write_stock_cache(code, data)
    return data


def _collect_us_stock(symbol):
    """从 Yahoo Finance 获取美股数据"""
    quote = get_quote(symbol)

    data = {
        "symbol": symbol,
        "name": quote.get("name", symbol),
        "market": "us",
        "price": quote.get("price", "N/A"),
        "prev_close": quote.get("prev_close", "N/A"),
        "change_pct": quote.get("change_pct", "N/A"),
        "change_5d": quote.get("change_5d", "N/A"),
        "pe_ratio": quote.get("pe_ratio", "N/A"),
        "market_cap": quote.get("market_cap", "N/A"),
        "volume_trend": quote.get("volume_trend", "N/A"),
        "news": quote.get("news", ""),
        "fetched_at": datetime.now().isoformat(),
    }

    _write_stock_cache(symbol, data)
    return data


# ============================================================
# 军师 Analyst — 调用 DeepSeek 生成人话建议
# ============================================================

ANALYST_SYSTEM_PROMPT = (
    "你是股小智，一位接地气的股票分析师。"
    "你的风格：说人话、不装逼、像朋友聊天一样给建议。"
    "不用 MACD、RSI、KDJ 这些术语——用'最近涨得有点猛'、'成交量在萎缩'这种表达。"
    "要能共情散户：提到'打工人定投'、'怕高不敢买'、'割肉心疼'这些真实感受。"
    "每段分析结尾给一个明确态度：【关注】【警惕】【观望】三选一。"
    "控制在 150 字以内。"
)


def analyst(raw_data):
    """读股票数据 → 调 DeepSeek → 返回建议"""
    symbol = raw_data.get("symbol", "?")
    cache_file = os.path.join(STOCKS_DIR, f"{symbol}.json")

    prompt = _build_analyst_prompt(raw_data)

    import requests
    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.8,
                "max_tokens": 400,
            },
            timeout=30,
        )

        if resp.status_code == 200:
            body = resp.json()
            advice = body["choices"][0]["message"]["content"]
        else:
            advice = f"[军师离线] 暂时无法分析 {raw_data.get('name', symbol)}，请稍后重试"
    except Exception as e:
        advice = f"[军师离线] 网络波动，稍后重试"

    # 提取态度
    verdict = "观望"
    if "关注" in advice:
        verdict = "关注"
    elif "警惕" in advice:
        verdict = "警惕"

    result = {
        "advice": advice,
        "verdict": verdict,
        "generated_at": datetime.now().isoformat(),
    }

    # 合并写回缓存
    raw_data.update(result)
    _write_stock_cache(symbol, raw_data)

    return result


def _build_analyst_prompt(data):
    """构造给 DeepSeek 的分析提示"""
    name = data.get("name", "?")
    symbol = data.get("symbol", "?")
    price = data.get("price", "N/A")
    change = data.get("change_pct", "N/A")
    pe = data.get("pe_ratio", "N/A")
    mcap = data.get("market_cap", "N/A")
    news = data.get("news", "")
    market = "A股" if data.get("market") == "a" else "美股"
    vol = data.get("volume_trend", data.get("turnover_rate", "N/A"))

    return f"""来看看这只{market}：

股票：{name}（{symbol}）
最新价：{price}
涨跌：{change}%
市盈率(PE)：{pe}
市值：{mcap}
成交量趋势：{vol}
相关新闻：{news}

请给出一段接地气的分析，最后用【关注】【警惕】【观望】中的一个收尾。"""


# ============================================================
# 书记官 Keeper — 用户记忆（JSON）
# ============================================================

def keeper(user_id, symbol, stock_name, verdict, summary):
    """追加用户查询记录，维护关注清单"""
    if not user_id:
        return

    user_file = os.path.join(USERS_DIR, f"{user_id}.json")
    now = datetime.now()

    # 读现有
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            memory = json.load(f)
    else:
        memory = {
            "user_id": user_id,
            "created": now.strftime("%Y-%m-%d"),
            "queries": [],
            "watchlist": [],
        }

    # 追加查询记录
    memory["queries"].append({
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "symbol": symbol,
        "name": stock_name,
        "verdict": verdict,
        "summary": summary,
    })

    # 只保留最近 100 条
    if len(memory["queries"]) > 100:
        memory["queries"] = memory["queries"][-100:]

    # 维护关注清单（去重，更新最后查看时间）
    watchlist = memory["watchlist"]
    existing = next((w for w in watchlist if w["symbol"] == symbol), None)
    if existing:
        existing["last_checked"] = now.strftime("%Y-%m-%d %H:%M")
    else:
        watchlist.append({
            "symbol": symbol,
            "name": stock_name,
            "last_checked": now.strftime("%Y-%m-%d %H:%M"),
        })

    # 按最近查看排序
    watchlist.sort(key=lambda w: w["last_checked"], reverse=True)

    # 写回
    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def get_user_memory(user_id):
    """读取用户记忆"""
    user_file = os.path.join(USERS_DIR, f"{user_id}.json")
    if not os.path.exists(user_file):
        return {"user_id": user_id, "queries": [], "watchlist": []}
    with open(user_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 主入口 — run_analysis()
# ============================================================

def run_analysis(symbol, user_id=None):
    """完整闭环：取数据 → 分析 → 记记忆"""
    symbol = str(symbol).strip().upper()

    # 1. 情报员取数据
    raw = collector(symbol)
    if "error" in raw:
        return {"error": raw["error"]}

    # 2. 军师分析
    result = analyst(raw)

    # 3. 书记官记记忆
    if user_id:
        keeper(
            user_id=user_id,
            symbol=symbol,
            stock_name=raw.get("name", symbol),
            verdict=result.get("verdict", "观望"),
            summary=result.get("advice", "")[:80],
        )

    return {
        "stock": raw,
        "analysis": result["advice"],
        "verdict": result["verdict"],
    }


# ============================================================
# 工具函数
# ============================================================

def _write_stock_cache(symbol, data):
    """写股票数据缓存"""
    path = os.path.join(STOCKS_DIR, f"{symbol}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_stock_cache(symbol):
    """读股票数据缓存"""
    path = os.path.join(STOCKS_DIR, f"{symbol}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    # 快速测试
    print("=== 测试 A 股 ===")
    print(run_analysis("000725", "test_user"))
    print("\n=== 测试 美股 ===")
    print(run_analysis("AAPL", "test_user"))