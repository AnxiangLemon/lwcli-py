"""账号在配置表中的逻辑槽位：device_id 可跨行重复，用「备注 + device_id」区分。"""


def account_slot_key(account: dict) -> str:
    did = str(account.get("device_id") or "").strip()
    remark = str(account.get("remark") or "").strip()
    if not remark:
        remark = (did[:8] if did else "account")
    # U+001F 避免 remark 中含常见分隔符时拼接歧义
    return f"{remark}\x1f{did}"
