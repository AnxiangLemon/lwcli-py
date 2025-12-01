# src/account_loader.py
import json
from pathlib import Path
from typing import List, Dict
from .utils import atomic_write_json, logger

CONFIG_FILE = Path("config/accounts.json")

def load_accounts() -> List[Dict]:
    if not CONFIG_FILE.exists():
        example = [{
            "device_id": "deviceid132456",
            "wxid": "",
            "remark": "主号",
            "proxy": None
        }]
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(CONFIG_FILE, example)
        logger.warning(f"已创建 {CONFIG_FILE}，请编辑后重新运行")
        exit(1)

    accounts = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return accounts

def save_accounts(accounts: List[Dict]) -> None:
    atomic_write_json(CONFIG_FILE, accounts)