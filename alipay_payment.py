# alipay_payment.py - 支付宝官方支付接入模块 (alipay-sdk-python)
import os
import uuid
import json
from datetime import datetime, timedelta

from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
from alipay.aop.api.request.AlipayTradeWapPayRequest import AlipayTradeWapPayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from alipay.aop.api.domain.AlipayTradeWapPayModel import AlipayTradeWapPayModel
from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel

# ============== 支付宝配置 ==============
APP_ID = '2021006160630900'
GATEWAY = 'https://openapi.alipay.com/gateway.do'
SIGN_TYPE = 'RSA2'

PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), 'alipay_private_key.pem')
PUBLIC_KEY_PATH = os.path.join(os.path.dirname(__file__), 'alipay_public_key.txt')

# 读取密钥
with open(PRIVATE_KEY_PATH, 'r') as f:
    APP_PRIVATE_KEY = f.read()

with open(PUBLIC_KEY_PATH, 'r') as f:
    ALIPAY_PUBLIC_KEY = f.read()

# 初始化支付宝客户端配置
alipay_config = AlipayClientConfig()
alipay_config.server_url = GATEWAY
alipay_config.app_id = APP_ID
alipay_config.app_private_key = APP_PRIVATE_KEY
alipay_config.alipay_public_key = ALIPAY_PUBLIC_KEY
alipay_config.sign_type = SIGN_TYPE

# 初始化客户端
alipay_client = DefaultAlipayClient(alipay_config)


def create_alipay_page_order(order_no, amount, subject, body, return_url, notify_url):
    """
    创建支付宝电脑网站支付订单
    返回跳转URL
    """
    # 创建业务模型
    model = AlipayTradePagePayModel()
    model.out_trade_no = order_no
    model.total_amount = str(amount)
    model.subject = subject
    model.body = body
    model.product_code = "FAST_INSTANT_TRADE_PAY"

    # 创建请求
    request = AlipayTradePagePayRequest()
    request.biz_model = model
    request.notify_url = notify_url
    request.return_url = return_url

    # 执行请求，获取支付URL
    response = alipay_client.page_execute(request)
    return response


def create_alipay_wap_order(order_no, amount, subject, body, return_url, notify_url):
    """
    创建支付宝手机网站支付订单（H5）
    """
    model = AlipayTradeWapPayModel()
    model.out_trade_no = order_no
    model.total_amount = str(amount)
    model.subject = subject
    model.body = body
    model.product_code = "QUICK_WAP_WAY"

    request = AlipayTradeWapPayRequest()
    request.biz_model = model
    request.notify_url = notify_url
    request.return_url = return_url

    response = alipay_client.page_execute(request)
    return response


def verify_alipay_notify(data):
    """
    验证支付宝异步通知的签名
    data: dict, 支付宝POST过来的通知数据
    """
    from alipay.aop.api.util.SignatureUtils import verify_with_rsa

    sign = data.pop('sign', None)
    sign_type = data.pop('sign_type', 'RSA2')

    if not sign:
        return False

    # 将参数按key排序后拼接成字符串
    params = sorted(data.items())
    content = '&'.join([f"{k}={v}" for k, v in params if v])

    return verify_with_rsa(ALIPAY_PUBLIC_KEY, content, sign)


def query_order(order_no):
    """
    查询订单状态
    """
    model = AlipayTradeQueryModel()
    model.out_trade_no = order_no

    request = AlipayTradeQueryRequest()
    request.biz_model = model

    response = alipay_client.execute(request)
    if response:
        return json.loads(response)
    return {}


def generate_order_no():
    """生成唯一订单号"""
    return f"GXZ{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
