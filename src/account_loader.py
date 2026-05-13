"""
账号配置读写与「逻辑槽位」键。

本模块负责 config/accounts.json，并提供 account_slot_key：同一表中 device_id 可重复，
启动/停止/运行状态必须以「备注 + device_id」区分不同行，避免任务互相覆盖。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

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
