"""
通用工具：控制台+文件日志、按账号日志路径、原子写 JSON、简单时间字符串。

被 account_loader、各服务与 web 层复用；与业务无关的纯函数尽量放此处，
避免在业务模块里散落重复实现。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from loguru import logger

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
_LOGGER_INITIALIZED = False


def setup_logger(name: str = "bot"):
    """
    为「逻辑名」（通常账号备注）注册按日期滚动的文件日志：logs/{name}_YYYY-MM-DD.log。
    首次调用时还会配置带颜色的控制台输出。
    """
    global _LOGGER_INITIALIZED
    if not _LOGGER_INITIALIZED:
        logger.remove()
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level="DEBUG",
            colorize=True,
        )
        _LOGGER_INITIALIZED = True

    logger.add(
        LOG_DIR / f"{name}_{{time:YYYY-MM-DD}}.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8",
    )
    return logger


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
