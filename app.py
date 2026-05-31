# app.py - 个股智投 - AI驱动的股票分析工具
import sys, os, json, time
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from services.stock_service import get_stock_list, search_stock, get_stock_detail, get_stock_history
from services.ai_service import analyze_stock, analyze_portfolio, daily_briefing

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

@app.route("/api/analyze")
def api_analyze():
    code = request.args.get("code", "")
    if not code:
        return jsonify({"error": "请提供股票代码"}), 400
    try:
        track_analysis(code)
        all_stocks = get_stock_list(size=300)
        detail = None
        for s in all_stocks:
            if s["code"] == code:
                detail = s
                break
        if not detail:
            detail = get_stock_detail(code)
        if not detail:
            return jsonify({"error": "未找到股票代码 " + code}), 404
        try:
            history = get_stock_history(code, days=30)
        except:
            history = None
        analysis = analyze_stock(detail, history)
        resp_data = {"stock": detail, "analysis": analysis}
        if history:
            resp_data["history"] = history[-30:]
        return jsonify(resp_data)
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)