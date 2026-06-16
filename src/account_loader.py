"""
账号配置读写与「逻辑槽位」键。

本模块负责 config/accounts.json。account_slot_key 可用于日志等场景区分同行配置；
机器人任务以 accounts.json 行下标跟踪，因扫码登录后 device_id 可能被服务端回写。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .utils import atomic_write_json, logger

CONFIG_FILE = Path("config/accounts.json")


def account_slot_key(account: dict) -> str:
    """生成该行账号在运行期使用的唯一键（备注 + 设备 ID）。"""
    did = str(account.get("device_id") or "").strip()
    remark = str(account.get("remark") or "").strip()
    if not remark:
        remark = did[:8] if did else "account"
    # U+001F 单元分隔符，降低 remark 内含常见符号时拼接歧义
    return f"{remark}\x1f{did}"


def find_duplicate_wxid_index(
    accounts: List[Dict],
    wxid: str,
    *,
    exclude_idx: Optional[int] = None,
) -> Optional[int]:
    """若列表中已有相同 wxid（非空），返回其下标；否则返回 None。"""
    needle = str(wxid or "").strip()
    if not needle:
        return None
    for i, acc in enumerate(accounts):
        if exclude_idx is not None and i == exclude_idx:
            continue
        if str(acc.get("wxid") or "").strip() == needle:
            return i
    return None


def wxid_conflict_message(wxid: str, other_remark: str = "") -> str:
    """生成 wxid 重复时的中文错误说明。"""
    label = str(other_remark or "").strip() or str(wxid or "")[:12] or "未备注"
    return f"wxid 已存在（{wxid}，备注「{label}」），同一微信号只能添加一条"


def load_accounts() -> List[Dict]:
    """
    供独立脚本/工具使用：若配置文件不存在则写入示例并退出进程。
    Web 运维台请使用 load_accounts_safe()，避免因无文件而整站起不来。
    """
    if not CONFIG_FILE.exists():
        example = [
            {
                "device_id": "deviceid132456",
                "wxid": "",
                "remark": "主号",
                "proxy": None,
                "login_mode": "local",
            }
        ]
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(CONFIG_FILE, example)
        logger.warning(f"已创建 {CONFIG_FILE}，请编辑后重新运行")
        raise SystemExit(1)

    accounts = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return accounts


def save_accounts(accounts: List[Dict]) -> None:
    """原子写入账号列表（登录成功后可能回写 wxid / 真实 device_id）。"""
    atomic_write_json(CONFIG_FILE, accounts)


def load_accounts_safe() -> List[Dict]:
    """Web 与长期运行服务使用：无文件或 JSON 损坏时返回空列表，不退出进程。"""
    if not CONFIG_FILE.exists():
        return []
    try:
        text = CONFIG_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"读取 {CONFIG_FILE} 失败，返回空列表: {e}")
        return []
