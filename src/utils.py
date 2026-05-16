"""
通用工具：控制台+文件日志、按账号日志路径、原子写 JSON、简单时间字符串。

被 account_loader、各服务与 web 层复用；与业务无关的纯函数尽量放此处，
避免在业务模块里散落重复实现。
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from loguru import logger

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
_LOGGER_INITIALIZED = False
# 已为该「日志账号键」注册过文件 sink，避免同一备注重复启动时重复写入同一文件。
_ACCOUNT_FILE_SINKS: set[str] = set()
# Bot 协程内设置；文件 sink 的 filter 会读此变量，使 lwapi / 插件里未 bind 的 logger 也能进对应账号文件。
log_account_ctx: ContextVar[Optional[str]] = ContextVar("log_account", default=None)

ACCOUNT_LOG_EXTRA_KEY = "account"


def effective_account_remark(acc: dict) -> str:
    """与运维台读日志、日志文件名一致：优先备注，否则取 device_id 前 8 位。"""
    r = (acc.get("remark") or "").strip()
    if r:
        return r
    did = (acc.get("device_id") or "").strip()
    return did[:8] if did else "bot"


def setup_logger(name: str = "bot"):
    """
    为「逻辑名」（通常账号备注）注册按日期滚动的文件日志：logs/{name}_YYYY-MM-DD.log。
    首次调用时还会配置带颜色的控制台输出。

    多账号时：文件 sink 带 filter，只写入 ``extra["account"] == name`` 或当前
    ``log_account_ctx`` 与本账号一致的记录（lwapi 等未 bind 的日志依赖后者），避免互相混写。
    """
    global _LOGGER_INITIALIZED
    account_key = (name or "").strip() or "bot"

    if not _LOGGER_INITIALIZED:
        logger.remove()
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level="DEBUG",
            colorize=True,
        )
        _LOGGER_INITIALIZED = True

    def _only_this_account(record: dict) -> bool:
        extra = record["extra"]
        if extra.get(ACCOUNT_LOG_EXTRA_KEY) == account_key:
            return True
        # 各模块普遍 ``from loguru import logger`` 未 bind；Bot 协程里已 set log_account_ctx
        return log_account_ctx.get() == account_key

    if account_key not in _ACCOUNT_FILE_SINKS:
        _ACCOUNT_FILE_SINKS.add(account_key)
        logger.add(
            LOG_DIR / f"{account_key}_{{time:YYYY-MM-DD}}.log",
            rotation="10 MB",
            retention="7 days",
            level="DEBUG",
            encoding="utf-8",
            filter=_only_this_account,
        )
    return logger.bind(**{ACCOUNT_LOG_EXTRA_KEY: account_key})


def account_log_file_path(remark: str, date_str: Optional[str] = None) -> Path:
    """与 setup_logger(name) 生成的按日文件名规则一致。"""
    d = date_str or datetime.now().strftime("%Y-%m-%d")
    name = (remark or "").strip() or "bot"
    return LOG_DIR / f"{name}_{d}.log"


def read_account_today_log_tail(remark: str, lines: int = 50) -> Dict[str, Any]:
    """读取当日该备注对应日志文件末尾若干行，供运维台「日志」页展示。"""
    lines = max(1, min(200, int(lines)))
    path = account_log_file_path(remark)
    if not path.exists():
        return {
            "path": str(path.resolve()),
            "exists": False,
            "lines": [],
            "message": "今日尚无此日志文件（可能尚未启动过或备注与日志名不一致）",
        }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"path": str(path.resolve()), "exists": False, "lines": [], "error": str(e)}
    all_lines = text.splitlines()
    tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
    return {
        "path": str(path.resolve()),
        "exists": True,
        "lines": tail,
        "total_lines": len(all_lines),
    }


def clear_account_today_log(remark: str) -> Dict[str, Any]:
    """清空当日该备注对应日志文件内容。"""
    path = account_log_file_path(remark)
    if not path.exists():
        return {
            "path": str(path.resolve()),
            "cleared": False,
            "message": "今日尚无此日志文件",
        }
    try:
        path.write_text("", encoding="utf-8")
    except OSError as e:
        return {"path": str(path.resolve()), "cleared": False, "error": str(e)}
    return {"path": str(path.resolve()), "cleared": True}


def atomic_write_json(path: Path, data) -> None:
    """先写临时文件再 replace，降低并发写 JSON 时文件半写入的概率。"""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as f:
        f.write(text)
        temp_name = f.name
    Path(temp_name).replace(path)


def now_str() -> str:
    """简短人类可读时间串，供业务日志拼接（可选）。"""
    return datetime.now().strftime("%m-%d %H:%M:%S")
