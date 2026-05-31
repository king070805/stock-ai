# services/ai_service.py - DeepSeek AI 股票分析服务
import requests
import json

DEEPSEEK_API_KEY = "sk-02582c0bb09b4099be5dfa14c652ce07"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = """你是一位专业的股票分析师，风格犀利、直接、说人话。
你的分析必须包含：
1. 一句话总结当前状态（强势/弱势/震荡，为什么）
2. 关键风险点（一个就够了，不要列一堆）
3. 值得关注的一个信号（技术面或基本面，说清楚逻辑）
规则：总字数不超过200字，不要"仅供参考"之类的免责声明，不要说"建议买入/卖出"，用"关注""警惕""留意"这类词。"""


def analyze_stock(stock_info, history=None):
    """AI 分析单只股票"""
    
    # 准备近5日K线摘要
    kline_text = ""
    if history and len(history) >= 3:
        recent = history[-5:]
        kline_text = "\n近5日K线：\n"
        for k in recent:
            kline_text += f"  {k.get('date','')}: 开{k.get('open','')} 收{k.get('close','')} 高{k.get('high','')} 低{k.get('low','')} 涨跌{k.get('change_pct','')}%\n"
    
    prompt = f"""请分析以下股票：

名称：{stock_info.get('name', '未知')}
代码：{stock_info.get('code', '未知')}
最新价：{stock_info.get('price', 'N/A')}
涨跌幅：{stock_info.get('change_pct', 'N/A')}%
今开：{stock_info.get('open', 'N/A')}
最高：{stock_info.get('high', 'N/A')}
最低：{stock_info.get('low', 'N/A')}
昨收：{stock_info.get('prev_close', 'N/A')}
市盈率(PE)：{stock_info.get('pe', 'N/A')}
市净率(PB)：{stock_info.get('pb', 'N/A')}
总市值：{stock_info.get('market_cap', 'N/A')}
换手率：{stock_info.get('turnover_rate', 'N/A')}%
量比：{stock_info.get('volume_ratio', 'N/A')}
振幅：{stock_info.get('amplitude', 'N/A')}%
60日涨跌：{stock_info.get('change_60d', 'N/A')}%
近1年涨跌：{stock_info.get('change_1y', 'N/A')}%
行业：{stock_info.get('industry', '未知')}
成交额：{stock_info.get('amount', 'N/A')}
{kline_text}
请直接给出分析："""

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"AI分析暂不可用 (错误: {resp.status_code})"
            
    except Exception as e:
        return f"AI分析暂不可用: {str(e)[:50]}"


def analyze_portfolio(stocks_data):
    """AI 分析股票组合"""
    stocks_text = "\n".join([
        f"- {s.get('name','?')}({s.get('code','?')}): 现价{s.get('price','N/A')}, 涨跌{s.get('change_pct','N/A')}%"
        for s in stocks_data[:5]
    ])
    
    prompt = f"""用户持有以下股票组合：
{stocks_text}

请给出：
1. 组合整体评价（一句话，说整体是进攻型还是防御型，集中还是分散）
2. 最大风险点（一句话）
3. 一个值得关注的信号（一句话）

总共不超过150字。"""

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是专业的股票投顾，简洁直接地给出分析和建议。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"AI分析暂不可用"
    except Exception as e:
        return f"AI分析暂不可用"


def daily_briefing(top_stocks):
    """生成每日市场简报"""
    stocks_text = "\n".join([
        f"{i+1}. {s['name']}({s['code']}) 涨跌{s['change_pct']}%，成交{s.get('amount','N/A')}"
        for i, s in enumerate(top_stocks[:5])
    ])
    
    prompt = f"""今日市场异动TOP5：
{stocks_text}

请生成一份今日市场简报（80字左右），包含：
1. 市场整体情绪（一句话）
2. 值得关注的方向（一句话）

风格：像在投资群里发消息一样自然，不要模板化。"""

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是财经编辑，产出简洁有力的市场简报。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            return "简报生成中..."
    except Exception as e:
        return "简报生成中..."