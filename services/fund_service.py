# services/fund_service.py - ?????? (??? v2)
import requests
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/"
}

SORT_MAP = {
    "1m": "1nzf", "3m": "3nzf", "6m": "6nzf",
    "1y": "1ynzf", "3y": "3ynzf", "jn": "jnzf"
}

def get_fund_rankings(page=1, size=20, fund_type="all", sort_by="6m"):
    """??????"""
    sc = SORT_MAP.get(sort_by, "6nzf")

    url = "https://fund.eastmoney.com/data/rankhandler.aspx"
    params = {
        "op": "ph", "dt": "kf", "ft": fund_type,
        "rs": "", "gs": 0, "sc": sc, "st": "desc",
        "sd": "", "ed": "", "qdii": "",
        "tabSubtype": ",,,,,",
        "pi": page, "pn": size,
        "dx": 1, "v": "0.1"
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        text = resp.text

        # ?? datas ??: datas:[...]
        m = re.search(r"datas:\[", text)
        if not m:
            return []

        arr_start = m.end() - 1  # [
        depth = 1
        arr_end = arr_start + 1
        for i in range(arr_start + 1, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    arr_end = i + 1
                    break

        arr_str = text[arr_start:arr_end]
        items = json.loads(arr_str)

        def pct(v):
            try:
                return f"{float(v):.2f}"
            except (ValueError, TypeError):
                return "N/A"

        funds = []
        for item_str in items:
            parts = item_str.split(",")
            if len(parts) < 16:
                continue

            funds.append({
                "code": parts[0],
                "name": parts[1],
                "nav_date": parts[3] if len(parts) > 3 else "",
                "nav": parts[4] if len(parts) > 4 else "",
                "cum_nav": parts[5] if len(parts) > 5 else "",
                "daily_change": pct(parts[6]) if len(parts) > 6 else "N/A",
                "one_week": pct(parts[7]) if len(parts) > 7 else "N/A",
                "one_month": pct(parts[8]) if len(parts) > 8 else "N/A",
                "three_month": pct(parts[9]) if len(parts) > 9 else "N/A",
                "six_month": pct(parts[10]) if len(parts) > 10 else "N/A",
                "one_year": pct(parts[11]) if len(parts) > 11 else "N/A",
                "two_year": pct(parts[12]) if len(parts) > 12 else "N/A",
                "three_year": pct(parts[13]) if len(parts) > 13 else "N/A",
                "ytd": pct(parts[14]) if len(parts) > 14 else "N/A",
                "since_inception": pct(parts[15]) if len(parts) > 14 else "N/A",
                "setup_date": parts[16] if len(parts) > 16 else "",
                "type": parts[17] if len(parts) > 17 else "",
                "manager": "",
                "scale": "",
            })
        return funds
    except Exception as e:
        print(f"fund_service get_fund_rankings error: {e}")
        return []


def search_fund(keyword):
    """????"""
    url = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
    params = {"callback": "jQuery", "m": "1", "key": keyword, "_": ""}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        text = resp.text
        json_str = text[text.index("(") + 1 : text.rindex(")")]
        data = json.loads(json_str)

        funds = []
        if data.get("Datas"):
            for item in data["Datas"]:
                funds.append({
                    "code": item.get("CODE", ""),
                    "name": item.get("NAME", ""),
                    "type": item.get("FundType", ""),
                    "pinyin": item.get("PY", ""),
                })
        return funds[:10]
    except:
        return []


def get_fund_detail(code):
    """??????????"""
    url = f"https://fundgz.1234567.com.cn/js/{code}.js"
    params = {"rt": "1463558676006"}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        text = resp.text
        if "jsonpgz" not in text:
            return None

        json_str = text[text.index("(") + 1 : text.rindex(")")]
        data = json.loads(json_str)
        return {
            "code": data.get("fundcode", ""),
            "name": data.get("name", ""),
            "nav": data.get("dwjz", ""),
            "estimated_nav": data.get("gsz", ""),
            "estimated_change": data.get("gszzl", ""),
            "nav_date": data.get("jzrq", ""),
            "estimated_time": data.get("gztime", ""),
        }
    except:
        return None
