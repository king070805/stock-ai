# app.py - 个股智投 - AI驱动的股票分析工具
import sys, os, json, time
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from services.stock_service import get_stock_list, search_stock, get_stock_detail, get_stock_history
from services.ai_service import analyze_stock, analyze_portfolio, daily_briefing
from guxiaozhi.orchestrator import run_analysis, get_user_memory

# ==================== 支付系统集成开始 ====================
import uuid
import hashlib
try:
    import qrcode
except ImportError:
    qrcode = None
import io
import base64

# 支付宝官方支付模块
try:
    from alipay_payment import (
        create_alipay_page_order, create_alipay_wap_order,
        verify_alipay_notify, query_order, generate_order_no
    )
    ALIPAY_ENABLED = True
except ImportError:
    ALIPAY_ENABLED = False

# 支付配置
PAYMENT_CONFIG = {
    'app_name': '股小智会员',
    # 网站域名（用于支付回调）
    'site_url': 'https://guxiaozhi-ai.up.railway.app',
    'order_timeout': 900,  # 订单超时时间（秒）15分钟
}

# 判断是否为手机访问
def is_mobile_request():
    """判断当前请求是否来自手机"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'windows phone']
    return any(kw in user_agent for kw in mobile_keywords)

# 会员套餐配置 - "一杯奶茶开启股票之旅"
# 成本核算：DeepSeek-Chat ~0.3分/次，毛利率64%-98%
MEMBER_PLANS = {
    'trial': {
        'name': '尝鲜卡',
        'amount': '1.9',
        'duration_days': 3,
        'tag': '一瓶水的价格',
        'daily_limit': 5,
        'features': ['信息摘要5次/天', '公开信息提醒', '基础资料整理'],
    },
    'weekly': {
        'name': '周卡',
        'amount': '5.9',
        'duration_days': 7,
        'tag': '半杯奶茶',
        'daily_limit': 10,
        'features': ['信息摘要10次/天', '公开信息提醒', '基础资料整理', '赛道公开信息整理'],
    },
    'monthly': {
        'name': '月卡',
        'amount': '9.9',
        'duration_days': 30,
        'tag': '一杯奶茶',
        'daily_limit': 15,
        'features': ['信息摘要15次/天', '公开信息提醒', '完整资料整理', '赛道公开信息整理'],
    },
    'quarterly': {
        'name': '季卡',
        'amount': '25.9',
        'duration_days': 90,
        'tag': '高频整理',
        'daily_limit': 20,
        'features': ['信息摘要20次/天', '公开信息提醒', '完整资料整理', '赛道公开信息整理', 'AI 信息整理日报', '优先客服支持'],
    },
    'yearly': {
        'name': '年卡VIP',
        'amount': '88',
        'duration_days': 365,
        'tag': '每天两毛四',
        'daily_limit': 30,
        'features': ['信息摘要30次/天', '全部季卡权益', '专属AI模型', '公开资料深度整理', '一对一信息整理支持', '年度信息整理摘要'],
    },
}

# ==================== 用户次数限制系统 ====================
# 用户每日信息摘要次数记录（生产环境请使用Redis/数据库）
user_daily_usage = {}

# 免费用户每日限制
FREE_DAILY_LIMIT = 1

# 用户会员状态记录（生产环境请使用数据库）
user_memberships = {}

def get_user_daily_limit(user_id='anonymous'):
    """获取用户每日信息摘要次数限制"""
    membership = user_memberships.get(user_id)
    if membership:
        plan = MEMBER_PLANS.get(membership['plan_id'])
        if plan:
            return plan['daily_limit']
    return FREE_DAILY_LIMIT

def get_user_usage(user_id='anonymous'):
    """获取用户今日已使用次数"""
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{user_id}:{today}"
    return user_daily_usage.get(key, 0)

def increment_user_usage(user_id='anonymous'):
    """增加用户今日使用次数"""
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{user_id}:{today}"
    user_daily_usage[key] = user_daily_usage.get(key, 0) + 1
    return user_daily_usage[key]

def get_user_limit_info(user_id='anonymous'):
    """获取用户限制信息（用于前端展示）"""
    limit = get_user_daily_limit(user_id)
    used = get_user_usage(user_id)
    remaining = max(0, limit - used)
    return {
        'limit': limit,
        'used': used,
        'remaining': remaining,
        'is_member': user_id in user_memberships,
    }

# ==================== 信息摘要缓存系统 ====================
# 缓存用户最近分析的股票结果（30分钟内免费复看）
# 结构: {user_id: {stock_code: {'data': {...}, 'time': datetime}}}
ai_analysis_cache = {}
CACHE_DURATION_MINUTES = 30  # 缓存有效期30分钟

def get_cached_analysis(user_id, stock_code):
    """获取缓存的分析结果"""
    user_cache = ai_analysis_cache.get(user_id, {})
    cached = user_cache.get(stock_code)
    if cached:
        elapsed = (datetime.now() - cached['time']).total_seconds() / 60
        if elapsed < CACHE_DURATION_MINUTES:
            return cached['data'], elapsed
    return None, 0

def cache_analysis(user_id, stock_code, data):
    """缓存分析结果"""
    if user_id not in ai_analysis_cache:
        ai_analysis_cache[user_id] = {}
    ai_analysis_cache[user_id][stock_code] = {
        'data': data,
        'time': datetime.now()
    }

def build_report_meta(user_id, stock_code):
    """构造报告状态元信息，用于前端区分登录/付费/已解锁状态。"""
    safe_user = user_id or "anonymous"
    safe_code = str(stock_code or "").upper()
    today = datetime.now().strftime("%Y%m%d")
    report_id = hashlib.md5(f"{safe_user}:{safe_code}:{today}".encode()).hexdigest()[:12]
    is_member = safe_user in user_memberships
    if is_member:
        state = "paid"
        valid_until = user_memberships[safe_user].get("expire_time")
    elif safe_user == "anonymous" or safe_user.startswith("user_"):
        state = "login_required"
        valid_until = None
    else:
        state = "payment_required"
        valid_until = None
    return {
        "report_id": report_id,
        "unlock_state": state,
        "valid_until": valid_until.strftime("%Y-%m-%d %H:%M:%S") if isinstance(valid_until, datetime) else valid_until,
    }

REPORT_EMPTY_TEXT = "暂无可整理的信息"
REPORT_DISCLAIMER = "本报告仅基于公开信息整理，不构成投资建议。投资有风险，请独立判断。"

def _report_value(value):
    if value is None:
        return REPORT_EMPTY_TEXT
    text = str(value).strip()
    if not text or text in {"-", "None", "null", "N/A"}:
        return REPORT_EMPTY_TEXT
    return text

def _join_report_parts(parts):
    cleaned = [_report_value(part) for part in parts if _report_value(part) != REPORT_EMPTY_TEXT]
    return "；".join(cleaned) if cleaned else REPORT_EMPTY_TEXT

def build_structured_report(stock_info, analysis, news, policy):
    """返回固定 10 模块报告，前端按结构稳定渲染。"""
    stock_info = stock_info or {}
    news = news or []
    name = _report_value(stock_info.get("name"))
    code = _report_value(stock_info.get("code") or stock_info.get("symbol"))
    price = _report_value(stock_info.get("price"))
    change_pct = _report_value(stock_info.get("change_pct"))
    amount = _report_value(stock_info.get("amount"))
    pe = _report_value(stock_info.get("pe") or stock_info.get("pe_ratio"))
    industry = _report_value(stock_info.get("industry"))
    market = _report_value(stock_info.get("market"))
    news_lines = []
    for item in news[:5]:
        title = _report_value(item.get("title") if isinstance(item, dict) else item)
        if title != REPORT_EMPTY_TEXT:
            news_lines.append(title)
    news_text = "；".join(news_lines) if news_lines else REPORT_EMPTY_TEXT
    policy_text = _report_value(policy.get("text") if isinstance(policy, dict) else None)
    basis_text = _join_report_parts([
        f"最新价 {price}" if price != REPORT_EMPTY_TEXT else "",
        f"公开行情变动比例 {change_pct}%" if change_pct != REPORT_EMPTY_TEXT else "",
        f"成交额 {amount}" if amount != REPORT_EMPTY_TEXT else "",
        f"市盈率 {pe}" if pe != REPORT_EMPTY_TEXT else "",
    ])
    attention_text = _join_report_parts([
        "近期公开信息主要围绕新闻动态、公司公告、公开市场数据变化展开",
        f"所属市场：{market}" if market != REPORT_EMPTY_TEXT else "",
        f"行业信息：{industry}" if industry != REPORT_EMPTY_TEXT else "",
    ])
    risk_text = "需关注公开数据延迟、公告更新、行业变化、公司经营信息变化等不确定因素。"
    summary_text = _report_value(analysis)
    return [
        {"key": "basic_info", "title": "股票基础信息", "content": f"{name}（{code}）｜所属市场 {market}｜行业 {industry}"},
        {"key": "recent_summary", "title": "近期重点摘要", "content": summary_text},
        {"key": "news", "title": "新闻动态整理", "content": news_text},
        {"key": "announcements", "title": "公司公告整理", "content": policy_text},
        {"key": "capital_flow", "title": "资金动向整理", "content": amount if amount != REPORT_EMPTY_TEXT else REPORT_EMPTY_TEXT},
        {"key": "price_overview", "title": "股价表现概览", "content": basis_text},
        {"key": "market_attention", "title": "市场关注点", "content": attention_text},
        {"key": "risk_notice", "title": "潜在风险提示", "content": risk_text},
        {"key": "ai_summary", "title": "AI 总结：这只股票最近主要发生了什么", "content": summary_text},
        {"key": "disclaimer", "title": "免责声明", "content": REPORT_DISCLAIMER},
    ]

# 内存存储订单（生产环境建议使用数据库）
orders = {}
user_agreements = {}
# ==================== 支付系统集成结束 ====================

app = Flask(__name__)

# 简易访问统计（内存存储，重启清零）
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stats.json")

def load_stats():
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "total_visits": 0,
            "total_analyses": 0,
            "daily": {},
            "searches": [],
        }

def save_stats(stats):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def track_visit():
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    stats["total_visits"] += 1
    if today not in stats["daily"]:
        stats["daily"][today] = {"visits": 0, "analyses": 0}
    stats["daily"][today]["visits"] += 1
    save_stats(stats)

def track_analysis(code):
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    stats["total_analyses"] += 1
    if today not in stats["daily"]:
        stats["daily"][today] = {"visits": 0, "analyses": 0}
    stats["daily"][today]["analyses"] += 1
    stats["searches"].append({"code": code, "time": datetime.now().isoformat()})
    if len(stats["searches"]) > 100:
        stats["searches"] = stats["searches"][-100:]
    save_stats(stats)


@app.route("/")
def index():
    track_visit()
    return render_template("index.html")

@app.route("/report")
def report():
    track_visit()
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    today_data = stats["daily"].get(today, {"visits": 0, "analyses": 0})
    yesterday_data = stats["daily"].get(yesterday, {"visits": 0, "analyses": 0})
    
    # Recent 7 days
    recent = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        recent.append({
            "date": d,
            "visits": stats["daily"].get(d, {}).get("visits", 0),
            "analyses": stats["daily"].get(d, {}).get("analyses", 0),
        })
    
    return render_template("dashboard.html",
        total_visits=stats["total_visits"],
        total_analyses=stats["total_analyses"],
        today_visits=today_data["visits"],
        today_analyses=today_data["analyses"],
        yesterday_visits=yesterday_data["visits"],
        recent=recent,
        recent_searches=stats.get("searches", [])[-20:],
    )

@app.route("/api/stats")
def api_stats():
    stats = load_stats()
    return jsonify(stats)

@app.route("/api/stocks")
def api_stocks():
    market = request.args.get("market", "a")
    sort_by = request.args.get("sort", "amount")
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 60))
    try:
        stocks = get_stock_list(market=market, sort_by=sort_by, page=page, size=size)
        return jsonify({"stocks": stocks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "")
    examples = ["600519", "贵州茅台", "NVDA", "英伟达", "NVIDIA"]
    if not keyword:
        return jsonify({"error": "请提供搜索关键词", "examples": examples}), 400
    try:
        results = search_stock(keyword)
        return jsonify({"results": results, "examples": examples})
    except Exception as e:
        return jsonify({"error": str(e), "examples": examples}), 500

def _get_a_stock_news(code):
    """获取A股相关新闻"""
    import requests as req
    url = "https://searchapi.eastmoney.com/bussiness/web/QuotationLabelSearch"
    params = {
        "keyword": code,
        "type": 0,
        "pi": 1,
        "ps": 5,
        "name": code,
    }
    try:
        resp = req.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            data = resp.json()
            items = []
            if data.get("Data"):
                for item in data["Data"][:5]:
                    items.append({
                        "title": item.get("Title", item.get("title", "")),
                        "time": item.get("Date", item.get("date", "")),
                    })
            return items
    except:
        pass

    # 备用：从东方财富个股新闻API获取
    try:
        news_url = f"https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        news_params = {
            "client": "web",
            "column": "600",
            "order": "1",
            "pageSize": "5",
            "search": code,
        }
        resp = req.get(news_url, params=news_params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            data = resp.json()
            items = []
            if data.get("data") and data["data"].get("list"):
                for item in data["data"]["list"][:5]:
                    items.append({
                        "title": item.get("title", ""),
                        "time": item.get("showtime", ""),
                    })
            return items
    except:
        pass

    return []


def _get_policy_info(code, stock_info):
    """根据股票代码和行业推断政策关联"""
    name = stock_info.get("name", "")
    industry = stock_info.get("industry", "")

    # AI/算力相关
    ai_keywords = ["AI", "人工智能", "算力", "芯片", "半导体", "智能", "科大讯飞", "中科曙光", "浪潮", "寒武纪", "GPU", "CPU"]
    # 低空经济相关
    ev_keywords = ["低空", "飞行", "无人机", "航空", "万丰", "中信海直", "商络"]
    # 新能源相关
    energy_keywords = ["新能源", "光伏", "锂电", "储能", "隆基", "宁德", "比亚迪"]
    # 高股息/金融相关
    finance_keywords = ["银行", "保险", "证券", "神华", "电力", "长江电力", "工商银行"]

    policy_text = ""
    stance = "neutral"

    for kw in ai_keywords:
        if kw in name or kw in industry:
            policy_text = "受益于国家AI发展战略，算力基础设施建设持续推进，相关企业有望获得政策支持和订单增长"
            stance = "bullish"
            break

    if not policy_text:
        for kw in ev_keywords:
            if kw in name or kw in industry:
                policy_text = "低空经济被列为国家战略性新兴产业，多地试点政策落地，eVTOL适航认证加速推进"
                stance = "bullish"
                break

    if not policy_text:
        for kw in energy_keywords:
            if kw in name or kw in industry:
                policy_text = "新能源行业处于政策调整期，产能过剩问题待化解，关注供给侧改革政策动向"
                stance = "neutral"
                break

    if not policy_text:
        for kw in finance_keywords:
            if kw in name or kw in industry:
                policy_text = "金融板块受益于利率环境稳定和高股息政策导向，防御属性突出"
                stance = "bullish"
                break

    if not policy_text:
        return None

    return {
        "stance": stance,
        "text": policy_text,
    }


@app.route("/api/analyze")
def api_analyze():
    code = request.args.get("code", "")
    user_id = request.args.get("user_id", None)
    force_refresh = request.args.get("refresh", "false").lower() == "true"
    
    if not code:
        return jsonify({"error": "请提供股票代码"}), 400
    
    user_id = user_id or 'anonymous'
    
    # ====== 缓存检查（30分钟内免费复看） ======
    if not force_refresh:
        cached_data, elapsed_minutes = get_cached_analysis(user_id, code)
        if cached_data:
            remaining_minutes = int(CACHE_DURATION_MINUTES - elapsed_minutes)
            return jsonify({
                **cached_data,
                **build_report_meta(user_id, code),
                "cached": True,
                "cached_time": f"{int(elapsed_minutes)}分钟前",
                "cache_expires_in": remaining_minutes,
                "message": f"📋 这是您{int(elapsed_minutes)}分钟前的分析结果（{remaining_minutes}分钟内免费复看）",
                "limit_info": get_user_limit_info(user_id)
            })
    
    # ====== 次数限制检查 ======
    limit_info = get_user_limit_info(user_id)
    
    if limit_info['remaining'] <= 0:
        return jsonify({
            "error": "今日信息摘要次数已用完",
            "limit_info": limit_info,
            "upgrade_url": "/subscribe",
            "message": f"免费用户每日{limit_info['limit']}次，开通会员享更多次数"
        }), 403
    
    # 增加使用次数
    increment_user_usage(user_id)
    
    try:
        track_analysis(code)
        result = run_analysis(code, user_id=user_id)
        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        # 获取新闻数据
        news = []
        stock_info = result.get("stock", {})
        if stock_info.get("market") == "us":
            # 美股新闻
            try:
                from services.us_stock_service import get_quote
                quote = get_quote(code)
                if quote and quote.get("news"):
                    news_text = quote["news"]
                    if news_text and news_text != "暂无新闻":
                        # 将分号分隔的新闻文本转为列表
                        news_items = [n.strip() for n in news_text.split(";") if n.strip()]
                        news = [{"title": item, "time": ""} for item in news_items[:5]]
            except:
                pass
        else:
            # A股新闻 - 从东方财富获取
            try:
                news = _get_a_stock_news(code)
            except:
                pass

        # 获取政策关联信息
        policy = _get_policy_info(code, stock_info)
        report_modules = build_structured_report(stock_info, result["analysis"], news, policy)

        response_data = {
            "stock": result["stock"],
            "analysis": result["analysis"],
            "verdict": result.get("verdict", ""),
            "news": news,
            "policy": policy,
            "report_modules": report_modules,
            "limit_info": get_user_limit_info(user_id),
            **build_report_meta(user_id, code),
        }
        
        # 缓存分析结果（30分钟内免费复看）
        cache_analysis(user_id, code, response_data)
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/briefing")
def api_briefing():
    try:
        gainers = get_stock_list(market="a", sort_by="change", size=10)
        active = get_stock_list(market="a", sort_by="amount", size=10)
        seen = set()
        top = []
        for s in gainers + active:
            if s["code"] not in seen:
                seen.add(s["code"])
                top.append(s)
            if len(top) >= 10:
                break
        briefing = daily_briefing(top)
        return jsonify({"briefing": briefing, "top_stocks": top[:5]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sector-stocks")
def api_sector_stocks():
    """获取特定赛道的股票数据（通过腾讯API）"""
    sector = request.args.get("sector", "")
    sort_by = request.args.get("sort", "change")
    if not sector:
        return jsonify({"error": "请提供赛道参数"}), 400
    
    sector_codes_map = {
        "ai": [
            "002230","300033","688111","688256","688981","688012","688041","688525",
            "300502","300308","300394","300548","002281","000938",
            "000977","603019","601138","002236",
            "002837","300499","301018","603912",
            "002463","600183","603228","300739",
            "603986","688110","300223","000021",
            "300274","002335","600885",
            "601231","603306","002384","300620",
            "600845","600728","300017",
            "002371","688082","688072",
        ],
        "ev": [
            "002085","600760","688568","300696","688297","002389","600118",
            "000768","600316","002013","600038","300900","002151",
            "300114","002025","600372","600391","300159","002179",
            "600967","300424","002933","300411","603261","688070",
        ],
        "dividend": [
            "601398","601939","601288","600036","600900","601088","600585",
            "601318","600028","601857","600019","601988","601328","600016",
            "601998","601818","601186","601668","601390","601728","600048",
            "600104","600887","600690","600741","600660","600276","600309",
            "600406","600089","600115","601111","600029","600377","600350",
            "600018","600017","600508","601699","601225",
        ],
    }
    
    codes = sector_codes_map.get(sector, [])
    if not codes:
        return jsonify({"error": "无效的赛道"}), 400
    
    try:
        import requests as req
        
        # Convert to tencent format
        tencent_codes = []
        for c in codes:
            if c.startswith("6") or c.startswith("688") or c.startswith("689"):
                tencent_codes.append("sh" + c)
            else:
                tencent_codes.append("sz" + c)
        
        # Batch fetch (max 45 per request)
        all_stocks = []
        batch_size = 45
        for i in range(0, len(tencent_codes), batch_size):
            batch = tencent_codes[i:i + batch_size]
            url = "https://qt.gtimg.cn/q=" + ",".join(batch)
            resp = req.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://gu.qq.com/",
            }, timeout=15, proxies={"http": None, "https": None})
            
            if resp.status_code == 200:
                lines = [l for l in resp.text.strip().split(";") if l.strip().startswith("v_")]
                for line in lines:
                    parts = line.split("~")
                    if len(parts) < 45:
                        continue
                    code = parts[2]
                    price = parts[3]
                    if not price or price == "0.00":
                        continue
                    all_stocks.append({
                        "code": code,
                        "name": parts[1],
                        "price": price,
                        "change_pct": parts[32],
                        "change_amt": parts[31],
                        "volume": parts[36],
                        "amount": parts[37],
                        "turnover_rate": parts[38],
                        "pe": parts[52] or "",
                        "volume_ratio": "",
                        "high": parts[33] or "",
                        "low": parts[34] or "",
                        "open": parts[5] or "",
                        "prev_close": parts[4] or "",
                        "market_cap": parts[44] or "",
                        "circ_market_cap": parts[45] or "",
                        "pb": parts[46] or "",
                        "change_60d": "",
                        "change_1y": "",
                        "industry": "",
                        "update_time": datetime.now().strftime("%H:%M:%S"),
                    })
        
        # Sort
        if sort_by == "change":
            all_stocks.sort(key=lambda s: float(s.get("change_pct") or 0), reverse=True)
        elif sort_by == "amount":
            all_stocks.sort(key=lambda s: float(s.get("amount") or 0), reverse=True)
        elif sort_by == "volume":
            all_stocks.sort(key=lambda s: float(s.get("volume") or 0), reverse=True)
        
        if not all_stocks:
            fallback = []
            for c in codes[:20]:
                detail = get_stock_detail(c)
                if detail:
                    fallback.append(detail)
            return jsonify({"stocks": fallback})
        return jsonify({"stocks": all_stocks})
    except Exception as e:
        fallback = []
        for c in codes[:20]:
            detail = get_stock_detail(c)
            if detail:
                fallback.append(detail)
        return jsonify({"stocks": fallback, "message": "实时赛道数据暂不可用，已展示示例公开信息"})


@app.route("/api/sector-heat")
def api_sector_heat():
    """获取赛道热度数据"""
    try:
        sectors = [
            {"name": "AI算力", "heat": "🔥🔥🔥", "cls": "ai"},
            {"name": "低空经济", "heat": "🔥🔥", "cls": "ev"},
            {"name": "高股息", "heat": "🔥", "cls": "dividend"},
        ]
        # 动态计算热度：获取各赛道股票的平均涨跌幅
        sector_codes = {
            "ai": ["002230", "300033", "688111", "300502", "300308", "002049", "603019", "000977"],
            "ev": ["002085", "600760", "688568", "300696", "688297", "002389", "600118"],
            "dividend": ["601398", "601939", "601288", "600036", "600900", "601088", "600585"],
        }

        for sector in sectors:
            codes = sector_codes.get(sector["cls"], [])
            total_change = 0
            count = 0
            for code in codes:
                try:
                    detail = get_stock_detail(code)
                    if detail and detail.get("change_pct"):
                        total_change += float(detail.get("change_pct", 0))
                        count += 1
                except:
                    pass
            avg_change = total_change / count if count > 0 else 0
            # 根据平均涨跌幅动态设置热度
            if avg_change > 2:
                sector["heat"] = "🔥🔥🔥🔥"
            elif avg_change > 1:
                sector["heat"] = "🔥🔥🔥"
            elif avg_change > 0:
                sector["heat"] = "🔥🔥"
            elif avg_change > -1:
                sector["heat"] = "🔥"
            else:
                sector["heat"] = "❄️"
            sector["avg_change"] = f"{avg_change:+.2f}%"

        return jsonify({"sectors": sectors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/user/memory")
def api_user_memory():
    """获取用户记忆"""
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"error": "请提供 user_id"}), 400
    try:
        memory = get_user_memory(user_id)
        return jsonify(memory)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/portfolio")
def api_portfolio():
    codes_str = request.args.get("codes", "")
    if not codes_str:
        return jsonify({"error": "请提供股票代码"}), 400
    codes = [c.strip() for c in codes_str.split(",") if c.strip()]
    if not codes:
        return jsonify({"error": "无效的股票代码"}), 400
    try:
        matched = []
        for code in codes:
            detail = get_stock_detail(code)
            if detail:
                matched.append(detail)
        if not matched:
            return jsonify({"error": "未找到任何匹配的股票"}), 404
        analysis = analyze_portfolio(matched)
        return jsonify({"stocks": matched, "analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<code>")
def api_stock_detail(code):
    try:
        detail = get_stock_detail(code)
        history = get_stock_history(code, days=10)
        if detail:
            return jsonify({"stock": detail, "history": history})
        return jsonify({"error": "未找到"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/user/limit")
def api_user_limit():
    """获取用户信息摘要次数限制信息"""
    user_id = request.args.get("user_id", "anonymous")
    limit_info = get_user_limit_info(user_id)
    return jsonify({
        "success": True,
        "limit_info": limit_info
    })


# ==================== 法律合规页面 ====================

@app.route('/terms')
def terms_page():
    """用户协议页面"""
    return render_template('terms.html')

@app.route('/refund')
def refund_page():
    """退费规则页面"""
    return render_template('refund.html')

@app.route('/disclaimer')
def disclaimer_page():
    """免责声明页面"""
    return render_template('disclaimer.html')


# ==================== 支付系统路由开始 ====================

@app.route('/subscribe')
def subscribe_page():
    """会员订阅页面"""
    return render_template('subscribe.html')


@app.route('/api/create_order', methods=['POST'])
def create_order():
    """创建支付订单 - 支付宝官方接入"""
    data = request.get_json()

    plan_id = data.get('plan_id')
    user_id = data.get('user_id', 'anonymous')

    if plan_id not in MEMBER_PLANS:
        return jsonify({'success': False, 'error': '无效的套餐'}), 400

    plan = MEMBER_PLANS[plan_id]

    # 生成唯一订单号
    order_no = generate_order_no()

    # 设置过期时间
    expire_time = datetime.now() + timedelta(seconds=PAYMENT_CONFIG['order_timeout'])

    # 创建订单
    orders[order_no] = {
        'order_no': order_no,
        'user_id': user_id,
        'plan_id': plan_id,
        'plan_name': plan['name'],
        'amount': plan['amount'],
        'pay_type': 'alipay',
        'status': 'PENDING',
        'create_time': datetime.now(),
        'expire_time': expire_time
    }

    # 构建回调URL
    site_url = PAYMENT_CONFIG['site_url']
    return_url = f"{site_url}/api/alipay/return"
    notify_url = f"{site_url}/api/alipay/notify"

    # 判断设备类型，选择电脑网站支付或手机网站支付
    subject = f"股小智AI - {plan['name']}"
    body = f"{plan['name']}会员服务，有效期{plan['duration_days']}天"

    try:
        if is_mobile_request():
            # 手机端使用H5支付
            pay_url = create_alipay_wap_order(
                order_no=order_no,
                amount=plan['amount'],
                subject=subject,
                body=body,
                return_url=return_url,
                notify_url=notify_url
            )
        else:
            # 电脑端使用网页支付
            pay_url = create_alipay_page_order(
                order_no=order_no,
                amount=plan['amount'],
                subject=subject,
                body=body,
                return_url=return_url,
                notify_url=notify_url
            )

        return jsonify({
            'success': True,
            'order_no': order_no,
            'amount': plan['amount'],
            'pay_url': pay_url,
            'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
            'pay_type': 'alipay',
        })
    except Exception as e:
        print(f"[创建订单失败] {e}")
        return jsonify({'success': False, 'error': '支付系统暂时不可用，请稍后重试'}), 500


@app.route('/api/check_order/<order_no>')
def check_order(order_no):
    """查询订单状态"""
    order = orders.get(order_no)
    
    if not order:
        return jsonify({'success': False, 'error': '订单不存在'}), 404
    
    # 检查是否超时
    if order['status'] == 'PENDING' and datetime.now() > order['expire_time']:
        order['status'] = 'EXPIRED'
    
    return jsonify({
        'success': True,
        'order': {
            'order_no': order['order_no'],
            'plan_name': order['plan_name'],
            'amount': order['amount'],
            'pay_type': order['pay_type'],
            'status': order['status'],
            'create_time': order['create_time'].strftime('%Y-%m-%d %H:%M:%S'),
            'pay_time': order.get('pay_time', '').strftime('%Y-%m-%d %H:%M:%S') if order.get('pay_time') else None,
            'expire_time': order['expire_time'].strftime('%Y-%m-%d %H:%M:%S'),
        }
    })


@app.route('/api/alipay/return')
def alipay_return():
    """支付宝同步回调 - 支付成功后跳转回来"""
    data = request.args.to_dict()
    order_no = data.get('out_trade_no')

    order = orders.get(order_no)
    if not order:
        return render_template('pay_result.html', success=False, message='订单不存在')

    # 查询订单真实状态
    try:
        result = query_order(order_no)
        if result.get('trade_status') in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
            if order['status'] == 'PENDING':
                order['status'] = 'PAID'
                order['pay_time'] = datetime.now()
                plan = MEMBER_PLANS.get(order['plan_id'], {})
                user_memberships[order['user_id']] = {
                    'plan_id': order['plan_id'],
                    'order_no': order_no,
                    'start_time': order['pay_time'],
                    'expire_time': order['pay_time'] + timedelta(days=plan.get('duration_days', 30)),
                }
            return render_template('pay_result.html', success=True,
                                   plan_name=order['plan_name'],
                                   amount=order['amount'])
    except Exception as e:
        print(f"[同步回调查询失败] {e}")

    # 如果查询失败，但用户已经支付，显示处理中
    return render_template('pay_result.html', success=True,
                           plan_name=order['plan_name'],
                           amount=order['amount'],
                           message='支付处理中，请稍后刷新页面查看')


@app.route('/api/alipay/notify', methods=['POST'])
def alipay_notify():
    """支付宝异步通知 - 支付结果后台通知"""
    data = request.form.to_dict()

    # 验证签名
    if not verify_alipay_notify(data.copy()):
        print("[支付宝通知] 签名验证失败")
        return 'fail'

    order_no = data.get('out_trade_no')
    trade_status = data.get('trade_status')
    total_amount = data.get('total_amount')

    order = orders.get(order_no)
    if not order:
        return 'success'  # 订单不存在也返回success，避免支付宝重复通知

    # 校验金额
    if float(total_amount) != float(order['amount']):
        print(f"[支付宝通知] 金额不匹配: 通知{total_amount} vs 订单{order['amount']}")
        return 'fail'

    # 处理支付成功
    if trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
        if order['status'] == 'PENDING':
            order['status'] = 'PAID'
            order['pay_time'] = datetime.now()
            order['trade_no'] = data.get('trade_no')  # 支付宝交易号
            plan = MEMBER_PLANS.get(order['plan_id'], {})
            user_memberships[order['user_id']] = {
                'plan_id': order['plan_id'],
                'order_no': order_no,
                'start_time': order['pay_time'],
                'expire_time': order['pay_time'] + timedelta(days=plan.get('duration_days', 30)),
            }
            print(f"[支付成功] 订单: {order_no}, 金额: {total_amount}, 用户: {order['user_id']}, 支付宝交易号: {data.get('trade_no')}")

    return 'success'


@app.route('/admin/payments')
def admin_payments():
    """支付管理后台"""
    order_list = sorted(orders.values(), key=lambda x: x['create_time'], reverse=True)
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>支付订单管理 - 股小智</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #667eea; color: white; }
            .status-PENDING { color: #ff9800; }
            .status-PAID { color: #4caf50; }
            .status-EXPIRED { color: #f44336; }
            .back-link { display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-link">← 返回股小智</a>
            <h1>支付订单管理</h1>
            <table>
                <tr>
                    <th>订单号</th>
                    <th>用户</th>
                    <th>套餐</th>
                    <th>金额</th>
                    <th>支付方式</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th>支付时间</th>
                </tr>
    '''
    
    for order in order_list:
        html += f'''
                <tr>
                    <td>{order['order_no']}</td>
                    <td>{order['user_id']}</td>
                    <td>{order['plan_name']}</td>
                    <td>¥{order['amount']}</td>
                    <td>{order['pay_type']}</td>
                    <td class="status-{order['status']}">{order['status']}</td>
                    <td>{order['create_time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{order.get('pay_time', '').strftime('%Y-%m-%d %H:%M:%S') if order.get('pay_time') else '-'}</td>
                </tr>
        '''
    
    html += '''
            </table>
        </div>
    </body>
    </html>
    '''
    
    return html

# ==================== 支付系统路由结束 ====================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
