# src/utils.py
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
_LOGGER_INITIALIZED = False


def setup_logger(name: str = "bot"):
    """
    每个账号单独一个按日期滚动的日志文件：logs/{name}_YYYY-MM-DD.log
    不再向 Web 实时合并推送，避免与分文件策略混在一起。
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
    """与 setup_logger(name) 生成的文件名规则一致（按自然日）。"""
    d = date_str or datetime.now().strftime("%Y-%m-%d")
    name = (remark or "").strip() or "bot"
    return LOG_DIR / f"{name}_{d}.log"


def read_account_today_log_tail(remark: str, lines: int = 50) -> Dict[str, Any]:
    """读取当日该备注对应的日志文件末尾若干行（用于运维台按需查看）。"""
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
    """防止多进程/多协程写坏配置文件"""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as f:
        f.write(text)
        temp_name = f.name
    Path(temp_name).replace(path)


def now_str() -> str:
    return datetime.now().strftime("%m-%d %H:%M:%S")
