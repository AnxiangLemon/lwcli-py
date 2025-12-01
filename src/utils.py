# src/utils.py
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from loguru import logger
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logger(name: str = "bot"):
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="DEBUG",
        colorize=True,
    )
    logger.add(
        LOG_DIR / f"{name}_{{time:YYYY-MM-DD}}.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8"
    )
    return logger

def atomic_write_json(path: Path, data) -> None:
    """防止多进程/多协程写坏配置文件"""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as f:
        f.write(text)
        temp_name = f.name
    Path(temp_name).replace(path)

def now_str() -> str:
    return datetime.now().strftime("%m-%d %H:%M:%S")