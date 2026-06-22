import hmac
from hashlib import sha256

from app.core.config import settings
from app.core.exceptions import BizError


def build_callback_signature(trade_no: str, transaction_id: str | None, status: str, secret: str) -> str:
    payload = f"{trade_no}|{transaction_id or ''}|{status}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()


def verify_callback_signature(trade_no: str, transaction_id: str | None, status: str, signature: str | None) -> None:
    # 未配置密钥时允许本地和测试环境跳过验签；生产环境必须配置 WX_PAY_CALLBACK_SECRET。
    if not settings.wx_pay_callback_secret:
        return
    expected = build_callback_signature(trade_no, transaction_id, status, settings.wx_pay_callback_secret)
    if not signature or not hmac.compare_digest(expected, signature):
        raise BizError("微信支付回调签名无效", 401)
