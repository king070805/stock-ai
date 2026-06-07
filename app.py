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

# 支付配置
PAYMENT_CONFIG = {
    'app_name': '股小智会员',
    # 微信收款码URL（已配置）
    'wx_pay_url': 'wxp://f2f031hwP19cZF95xZkBJQ0RNbUJ_mbq6WGL9T6RcS5EurVBbL1gr2c8mAGZxKHkh8TD',
    # 支付宝收款码URL（已配置）
    'alipay_url': 'https://qr.alipay.com/fkx14375b9m8pvsj5hamvb1',
    # ⚠️ 请修改为您自己的密钥（生产环境必须修改！）
    'callback_key': 'guxiaozhi_secret_2024',
    'order_timeout': 300,  # 订单超时时间（秒）
}

# 会员套餐配置 - "一杯奶茶开启股票之旅"
# 成本核算：DeepSeek-Chat ~0.3分/次，毛利率64%-98%
MEMBER_PLANS = {
    'trial': {
        'name': '尝鲜卡',
        'amount': '1.9',
        'duration_days': 3,
        'tag': '一瓶水的价格',
        'daily_limit': 5,
        'features': ['AI分析5次/天', '异动预警推送', '基础选股策略'],
    },
    'weekly': {
        'name': '周卡',
        'amount': '5.9',
        'duration_days': 7,
        'tag': '半杯奶茶',
        'daily_limit': 10,
        'features': ['AI分析10次/天', '异动预警推送', '基础选股策略', '赛道热度追踪'],
    },
    'monthly': {
        'name': '月卡',
        'amount': '9.9',
        'duration_days': 30,
        'tag': '一杯奶茶',
        'daily_limit': 15,
        'features': ['AI分析15次/天', '异动预警推送', '高级选股策略', '赛道热度追踪'],
    },
    'quarterly': {
        'name': '季卡',
        'amount': '25.9',
        'duration_days': 90,
        'tag': '超值推荐',
        'daily_limit': 20,
        'features': ['AI分析20次/天', '异动预警推送', '高级选股策略', '赛道热度追踪', 'AI复盘日报', '优先客服支持'],
    },
    'yearly': {
        'name': '年卡VIP',
        'amount': '88',
        'duration_days': 365,
        'tag': '每天两毛四',
        'daily_limit': 30,
        'features': ['AI分析30次/天', '全部季卡权益', '专属AI模型', '深度研报解读', '一对一投资顾问', '年度投资报告'],
    },
}

# ==================== 用户次数限制系统 ====================
# 用户每日AI分析次数记录（生产环境请使用Redis/数据库）
user_daily_usage = {}

# 免费用户每日限制
FREE_DAILY_LIMIT = 1

# 用户会员状态记录（生产环境请使用数据库）
user_memberships = {}

def get_user_daily_limit(user_id='anonymous'):
    """获取用户每日AI分析次数限制"""
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
    try:
        stocks = get_stock_list(market=market, sort_by=sort_by, page=page, size=20)
        return jsonify({"stocks": stocks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "")
    if not keyword:
        return jsonify({"error": "请提供搜索关键词"}), 400
    try:
        results = search_stock(keyword)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    if not code:
        return jsonify({"error": "请提供股票代码"}), 400
    
    # ====== 次数限制检查 ======
    user_id = user_id or 'anonymous'
    limit_info = get_user_limit_info(user_id)
    
    if limit_info['remaining'] <= 0:
        return jsonify({
            "error": "今日AI分析次数已用完",
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

        return jsonify({
            "stock": result["stock"],
            "analysis": result["analysis"],
            "verdict": result.get("verdict", ""),
            "news": news,
            "policy": policy,
        })
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
        
        return jsonify({"stocks": all_stocks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    """获取用户AI分析次数限制信息"""
    user_id = request.args.get("user_id", "anonymous")
    limit_info = get_user_limit_info(user_id)
    return jsonify({
        "success": True,
        "limit_info": limit_info
    })


# ==================== 支付系统路由开始 ====================

@app.route('/subscribe')
def subscribe_page():
    """会员订阅页面"""
    return render_template('subscribe.html')


@app.route('/api/create_order', methods=['POST'])
def create_order():
    """创建支付订单"""
    data = request.get_json()
    
    plan_id = data.get('plan_id')
    pay_type = data.get('pay_type', 'wxpay')
    user_id = data.get('user_id', 'anonymous')
    
    if plan_id not in MEMBER_PLANS:
        return jsonify({'success': False, 'error': '无效的套餐'}), 400
    
    if pay_type not in ['wxpay', 'alipay']:
        return jsonify({'success': False, 'error': '无效的支付方式'}), 400
    
    plan = MEMBER_PLANS[plan_id]
    
    # 生成唯一订单号
    order_no = f"ORDER{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
    
    # 设置过期时间
    expire_time = datetime.now() + timedelta(seconds=PAYMENT_CONFIG['order_timeout'])
    
    # 创建订单
    orders[order_no] = {
        'order_no': order_no,
        'user_id': user_id,
        'plan_id': plan_id,
        'plan_name': plan['name'],
        'amount': plan['amount'],
        'pay_type': pay_type,
        'status': 'PENDING',
        'create_time': datetime.now(),
        'expire_time': expire_time
    }
    
    # 生成收款二维码
    qr_data = f"{PAYMENT_CONFIG['wx_pay_url']}?amount={plan['amount']}&remark={order_no}"
    
    # 生成二维码图片
    if qrcode:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
    else:
        img_str = ""
    
    return jsonify({
        'success': True,
        'order_no': order_no,
        'amount': plan['amount'],
        'qr_code': f'data:image/png;base64,{img_str}',
        'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
        'pay_type': pay_type,
    })


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


@app.route('/api/notify', methods=['POST'])
def payment_notify():
    """监控端回调接口"""
    data = request.get_json()
    
    # 验证签名
    sign = data.pop('sign', None)
    timestamp = data.get('timestamp', '')
    
    expected_sign = hashlib.md5(
        f"{data['order_no']}{data['amount']}{timestamp}{PAYMENT_CONFIG['callback_key']}".encode()
    ).hexdigest()
    
    if sign != expected_sign:
        return jsonify({'success': False, 'error': '签名验证失败'}), 403
    
    order_no = data.get('order_no')
    amount = data.get('amount')
    pay_type = data.get('pay_type')
    
    order = orders.get(order_no)
    
    if not order:
        return jsonify({'success': False, 'error': '订单不存在'}), 404
    
    if order['status'] != 'PENDING':
        return jsonify({'success': False, 'error': '订单状态异常'}), 400
    
    # 校验金额
    if amount != order['amount']:
        return jsonify({'success': False, 'error': '金额不匹配'}), 400
    
    # 更新订单状态
    order['status'] = 'PAID'
    order['pay_time'] = datetime.now()
    
    print(f"[支付成功] 订单: {order_no}, 金额: {amount}, 用户: {order['user_id']}")
    
    return jsonify({'success': True, 'message': '支付成功'})


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