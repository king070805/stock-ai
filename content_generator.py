# content_generator.py - 小红书每日内容自动生成
import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.stock_service import get_stock_list
from services.ai_service import analyze_stock

CONTENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "content_log.json")

# 选题库 - 每周7天不同角度
TOPICS = [
    {
        "title": "今日最值得关注的3只股票（AI分析版）",
        "angle": "TOP3",
        "body_template": "今天AI帮我扫了一遍A股，挑出3只值得关注的：\n\n{stocks}\n\n你们持有哪些？评论区交流\n\n#股票 #AI选股 #今日看盘"
    },
    {
        "title": "AI眼中的今日异动：这只股票发生了什么？",
        "angle": "SINGLE",
        "body_template": "刚刚用AI分析了{name}（{code}），它的判断是：\n\n{analysis}\n\n大家怎么看？这个分析靠谱吗？\n\n#股票分析 #AI #投资"
    },
    {
        "title": "散户必看：AI教你避开今天的坑",
        "angle": "RISK",
        "body_template": "今天AI重点警告了这只股票：\n\n{name}（{code}）\n{analysis}\n\nAI不一定对，但多一个维度总没错\n\n#韭菜自救 #风险提示 #炒股"
    },
    {
        "title": "冷门发现：AI挖出一只被忽视的股票",
        "angle": "DISCOVERY",
        "body_template": "今天AI在扫描成交额中段时，发现了{name}（{code}）：\n\n{analysis}\n\n不是热门股，但数据有点意思\n\n#价值投资 #发现好股 #AI"
    },
    {
        "title": "你的持仓，AI觉得怎么样？（评论区发代码我来测）",
        "angle": "INTERACTIVE",
        "body_template": "今天不分析，咱们玩个互动的：\n\n把你持仓的股票代码发在评论区\n\n我挑10只用AI深度分析，明天发结果\n\n敢不敢晒出你的持仓？\n\n#晒持仓 #AI分析 #互动"
    },
    {
        "title": "本周AI胜率统计：AI的判断到底准不准？",
        "angle": "REVIEW",
        "body_template": "这周AI总共分析了{count}只股票，做个简单的准度复盘：\n\n{review}\n\nAI是工具，不是神。但它确实能帮你看到自己忽略的东西\n\n#AI复盘 #投资反思"
    },
    {
        "title": "同花顺没告诉你的事：AI看到的三个信号",
        "angle": "INSIGHT",
        "body_template": "今天市场{market_mood}。AI从数据中挖出了三个信号：\n\n{insights}\n\n这些在同花顺的消息流里早就被淹没了\n\n#信息差 #AI洞察 #看盘"
    },
]

def load_log():
    try:
        os.makedirs(os.path.dirname(CONTENT_FILE), exist_ok=True)
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"posts": [], "last_generated": None}

def save_log(log):
    os.makedirs(os.path.dirname(CONTENT_FILE), exist_ok=True)
    with open(CONTENT_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def generate_daily_content():
    """生成今日小红书内容"""
    weekday = datetime.now().weekday()  # 0=周一, 6=周日
    today = datetime.now().strftime("%Y-%m-%d")
    
    log = load_log()
    
    print(f"\n{'='*50}")
    print(f"📝 个股智投 · 小红书内容生成")
    print(f"📅 {today} 周{'一二三四五六日'[weekday]}")
    print(f"{'='*50}\n")
    
    # 获取市场数据
    print("⏳ 正在获取市场数据...")
    try:
        top_change = get_stock_list(market="a", sort_by="change", size=5)
        top_amount = get_stock_list(market="a", sort_by="amount", size=5)
        print(f"✅ 获取 {len(top_change)} 只涨跌榜 + {len(top_amount)} 只成交榜")
    except Exception as e:
        print(f"⚠️ 数据获取失败: {e}")
        print("请检查网络后重试")
        return
    
    if not top_change:
        print("⚠️ 当前无数据（可能是非交易时段）")
        print("建议发互动型内容")
    
    # 根据星期几选择角度
    topic = TOPICS[weekday]
    print(f"\n📌 今日选题: {topic['title']}")
    print(f"🎯 角度: {topic['angle']}")
    
    body = ""
    
    if topic["angle"] == "TOP3":
        # 选3只热门股生成摘要
        stocks_text = ""
        for i, s in enumerate(top_amount[:3]):
            chg = float(s.get("change_pct", 0) or 0)
            arrow = "📈" if chg > 0 else "📉" if chg < 0 else "➡️"
            stocks_text += f"\n{arrow} {s['name']}({s['code']}) "
            stocks_text += f"涨跌{'+' if chg>0 else ''}{s['change_pct']}% "
            stocks_text += f"成交{s.get('amount','N/A')}"
        body = topic["body_template"].replace("{stocks}", stocks_text)
    
    elif topic["angle"] == "SINGLE":
        # 挑一只成交额最大的做深度分析
        s = top_amount[0]
        print(f"\n⏳ AI正在分析 {s['name']}({s['code']})...")
        try:
            analysis = analyze_stock(s)
            short = analysis[:250] + "..." if len(analysis) > 250 else analysis
            body = topic["body_template"].replace("{name}", s["name"]).replace("{code}", s["code"]).replace("{analysis}", short)
            print("✅ AI分析完成")
        except:
            body = topic["body_template"].replace("{name}", s["name"]).replace("{code}", s["code"]).replace("{analysis}", "AI分析暂不可用，请稍后重试")
    
    elif topic["angle"] == "RISK":
        # 挑跌幅最大的
        s = top_change[-1] if len(top_change) > 0 else top_amount[0]
        print(f"\n⏳ AI正在分析 {s['name']}({s['code']})...")
        try:
            analysis = analyze_stock(s)
            short = analysis[:250] + "..." if len(analysis) > 250 else analysis
            body = topic["body_template"].replace("{name}", s["name"]).replace("{code}", s["code"]).replace("{analysis}", short)
        except:
            body = f"{s['name']}({s['code']})：今日跌幅{s['change_pct']}%，需关注风险"
    
    elif topic["angle"] == "DISCOVERY":
        # 挑成交额中段的
        mid = top_amount[len(top_amount)//2] if len(top_amount) > 2 else top_amount[0]
        print(f"\n⏳ AI正在分析 {mid['name']}({mid['code']})...")
        try:
            analysis = analyze_stock(mid)
            short = analysis[:250] + "..." if len(analysis) > 250 else analysis
            body = topic["body_template"].replace("{name}", mid["name"]).replace("{code}", mid["code"]).replace("{analysis}", short)
        except:
            body = f"{mid['name']}({mid['code']})：值得关注的冷门标的"
    
    elif topic["angle"] == "INTERACTIVE":
        body = topic["body_template"]
    
    elif topic["angle"] == "REVIEW":
        recent = [p for p in log.get("posts", []) if p.get("type") == "analysis"][-5:]
        count = len(recent)
        review = "本周数据量还不够，下周开始统计AI分析的准确率" if count < 3 else "回顾中..."
        body = topic["body_template"].replace("{count}", str(count)).replace("{review}", review)
    
    elif topic["angle"] == "INSIGHT":
        up_count = sum(1 for s in top_change if float(s.get("change_pct", 0) or 0) > 0)
        market_mood = "涨多跌少，情绪偏暖" if up_count > 3 else "跌多涨少，情绪偏冷" if up_count < 2 else "涨跌互现，方向不明"
        insights = f"1️⃣ 成交额前3集中在{top_amount[0].get('industry','科技')}板块\n2️⃣ 涨幅榜多为小盘股，资金偏向题材炒作\n3️⃣ 北向资金流向值得明天开盘关注"
        body = topic["body_template"].replace("{market_mood}", market_mood).replace("{insights}", insights)
    
    # 输出
    print(f"\n{'─'*50}")
    print("📱 小红书正文（可直接复制）:")
    print(f"{'─'*50}")
    print(body)
    print(f"{'─'*50}")
    
    # 配图建议
    print("\n🖼️ 配图建议:")
    print("  图1: 产品首页截图（搜索框+股票列表）")
    print("  图2: AI分析结果截图")
    print("  图3: K线图特写")
    print("\n💬 评论区置顶:")
    print("  免费测你的股票 → [链接]")
    
    # 记录
    log["posts"].append({
        "date": today,
        "topic": topic["title"],
        "angle": topic["angle"],
        "body_preview": body[:100],
    })
    log["last_generated"] = today
    save_log(log)
    
    print(f"\n✅ 内容已保存到 {CONTENT_FILE}")
    return body


if __name__ == "__main__":
    generate_daily_content()