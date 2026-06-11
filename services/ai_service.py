# services/ai_service.py - DeepSeek AI 股票分析服务
import os
import requests
import json

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

LEGAL_DISCLAIMER = "本内容仅为基于公开行情数据的信息整理，不构成任何投资建议或交易指令，也不承诺收益。投资有风险，请独立判断并自行承担风险。"

COMPLIANCE_SYSTEM_PROMPT = """你是股小智的公开行情信息解读助手，不是证券投资顾问、投顾、荐股老师或交易顾问。
合规边界：
1. 只能做公开行情、财务指标、新闻和风险因素的客观解读。
2. 不得推荐买入、卖出、加仓、减仓、满仓、清仓、抄底、追高、止盈、止损等具体交易动作。
3. 不得给目标价、收益率预测、保证盈利、必涨必跌、内幕消息、确定性结论。
4. 不得根据单个用户资产、持仓、风险偏好生成个性化投资建议。
5. 如用户要求交易指令，只能提示无法提供具体投资建议，并改为说明可关注的信息维度。
6. 输出必须包含风险提示，不得删除免责声明。
"""

SYSTEM_PROMPT = COMPLIANCE_SYSTEM_PROMPT + """
你是一位公开行情信息解读助手，风格清晰、直接、说人话。
你的分析必须包含：
1. 一句话总结公开数据变化（只描述事实，不使用强势/弱势等方向判断）
2. 政策/行业动态（如果有相关政策利好或利空，一句话说明影响）
3. 关键风险点（一个就够了，不要列一堆）
4. 值得关注的一个信息信号（技术面或基本面，说清楚逻辑）
规则：总字数不超过250字；不得出现具体交易动作建议；结尾必须带一句“仅供信息参考，不构成投资建议”。"""


def enforce_ai_compliance(text):
    """对模型输出做服务端合规二次过滤，降低荐股/投顾表达风险。"""
    if not text:
        return LEGAL_DISCLAIMER

    replacements = {
        "证券投顾": "公开行情信息解读助手",
        "投顾": "信息解读助手",
        "荐股": "信息解读",
        "建议买入": "不提供买入建议，可关注",
        "建议卖出": "不提供卖出建议，可关注",
        "推荐买入": "不提供买入建议，可关注",
        "推荐卖出": "不提供卖出建议，可关注",
        "强烈买入": "不提供买入建议",
        "立即买入": "不提供买入建议",
        "马上买入": "不提供买入建议",
        "立即卖出": "不提供卖出建议",
        "马上卖出": "不提供卖出建议",
        "满仓": "高仓位风险",
        "梭哈": "高风险操作",
        "抄底": "低位波动",
        "追高": "高位波动",
        "止盈": "风险管理",
        "止损": "风险管理",
        "目标价": "估值区间信息",
        "必涨": "存在上涨不确定性",
        "必跌": "存在下跌不确定性",
        "稳赚": "不存在确定收益",
        "保本": "不承诺本金安全",
        "保证收益": "不承诺收益",
        "涨跌幅": "公开行情变动比例",
        "涨跌": "公开行情变动",
        "强势": "较前一参考值上升",
        "弱势": "较前一参考值下降",
        "偏强": "较前一参考值上升",
        "偏弱": "较前一参考值下降",
        "乐观": "变化向上",
        "恐慌": "波动较大",
    }

    safe_text = text
    for bad, good in replacements.items():
        safe_text = safe_text.replace(bad, good)

    if "不构成投资建议" not in safe_text:
        safe_text = safe_text.rstrip() + "\n\n" + LEGAL_DISCLAIMER
    return safe_text


def analyze_stock(stock_info, history=None):
    """AI 分析单只股票"""
    
    # 准备近5日K线摘要
    kline_text = ""
    if history and len(history) >= 3:
        recent = history[-5:]
        kline_text = "\n近5日K线：\n"
        for k in recent:
            kline_text += f"  {k.get('date','')}: 开{k.get('open','')} 收{k.get('close','')} 高{k.get('high','')} 低{k.get('low','')} 公开行情变动{k.get('change_pct','')}%\n"
    
    prompt = f"""请分析以下股票：

名称：{stock_info.get('name', '未知')}
代码：{stock_info.get('code', '未知')}
最新价：{stock_info.get('price', 'N/A')}
公开行情变动比例：{stock_info.get('change_pct', 'N/A')}%
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
60日公开行情变动：{stock_info.get('change_60d', 'N/A')}%
近1年公开行情变动：{stock_info.get('change_1y', 'N/A')}%
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
            return enforce_ai_compliance(result["choices"][0]["message"]["content"])
        else:
            return f"信息整理暂不可用 (错误: {resp.status_code})"
            
    except Exception as e:
        return f"信息整理暂不可用: {str(e)[:50]}"


def analyze_portfolio(stocks_data):
    """AI 分析股票组合"""
    stocks_text = "\n".join([
        f"- {s.get('name','?')}({s.get('code','?')}): 现价{s.get('price','N/A')}, 公开行情变动{s.get('change_pct','N/A')}%"
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
                    {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT + "你是公开行情信息解读助手，简洁直接地说明组合集中度、波动风险和可观察信号，不提供个性化投资建议。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            return enforce_ai_compliance(result["choices"][0]["message"]["content"])
        else:
            return f"信息整理暂不可用"
    except Exception as e:
        return f"信息整理暂不可用"


def daily_briefing(top_stocks):
    """生成每日市场简报"""
    stocks_text = "\n".join([
        f"{i+1}. {s['name']}({s['code']}) 公开行情变动{s['change_pct']}%，成交{s.get('amount','N/A')}"
        for i, s in enumerate(top_stocks[:5])
    ])
    
    prompt = f"""今日市场异动TOP5：
{stocks_text}

请生成一份今日市场简报（80字左右），包含：
1. 公开行情整体变化（一句话）
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
                    {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT + "你是财经信息编辑，只输出市场信息简报和风险提示，不给任何交易指令。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            return enforce_ai_compliance(result["choices"][0]["message"]["content"])
        else:
            return "简报生成中..."
    except Exception as e:
        return "简报生成中..."
