"""
收消息入库（SQLite）与聚合查询，供运维台「消息」视图使用。

与插件链解耦：在 composite_message_handler 中先于插件写入，失败不影响插件。
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, List, Optional

from lwapi import LwApiClient
from lwapi.models.msg import AddMsg, SyncMessageResponse

DB_PATH = Path("config/messages.sqlite")
_lock = threading.Lock()

_MSG_TYPE_LABELS: dict[int, str] = {
    1: "文本",
    3: "图片",
    34: "语音",
    37: "好友确认",
    43: "视频",
    47: "表情",
    48: "位置",
    49: "链接/应用/小程序",
    50: "语音通话",
    10000: "系统",
    10002: "系统通知",
}


def msg_type_label(msg_type: int) -> str:
    return _MSG_TYPE_LABELS.get(msg_type, f"类型 {msg_type}")


def _sk_string(obj: Any) -> str:
    if obj is None:
        return ""
    s = getattr(obj, "string", None)
    if isinstance(s, str):
        return s.strip()
    return ""


def _peer_wxid(bot: str, from_u: str, to_u: str) -> str:
    if to_u.endswith("@chatroom"):
        return to_u
    if from_u == bot:
        return to_u
    return from_u


def _init_conn(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS inbox (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          bot_wxid TEXT NOT NULL,
          peer_wxid TEXT NOT NULL,
          from_wxid TEXT NOT NULL,
          to_wxid TEXT NOT NULL,
          msg_type INTEGER NOT NULL,
          category TEXT NOT NULL,
          content TEXT NOT NULL,
          msg_id INTEGER,
          new_msg_id INTEGER,
          create_time INTEGER,
          received_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_inbox_bot ON inbox(bot_wxid);
        CREATE INDEX IF NOT EXISTS idx_inbox_bot_type ON inbox(bot_wxid, msg_type);
        CREATE INDEX IF NOT EXISTS idx_inbox_bot_peer ON inbox(bot_wxid, peer_wxid);
        CREATE INDEX IF NOT EXISTS idx_inbox_received ON inbox(received_at DESC);
        """
    )


def _rows_from_add_msgs(bot_wxid: str, add_msgs: List[AddMsg]) -> List[tuple]:
    now = time.time()
    rows: List[tuple] = []
    for m in add_msgs:
        from_u = _sk_string(m.fromUserName)
        to_u = _sk_string(m.toUserName)
        content = _sk_string(m.content)
        if len(content) > 800:
            content = content[:797] + "..."
        mt = int(m.msgType)
        label = msg_type_label(mt)
        peer = _peer_wxid(bot_wxid, from_u, to_u)
        rows.append(
            (
                bot_wxid,
                peer,
                from_u,
                to_u,
                mt,
                label,
                content,
                int(m.msgId) if m.msgId is not None else None,
                int(m.newMsgId) if m.newMsgId is not None else None,
                int(m.createTime) if m.createTime is not None else None,
                now,
            )
        )
    return rows


def _insert_rows_sync(rows: List[tuple]) -> None:
    if not rows:
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        try:
            _init_conn(conn)
            conn.executemany(
                """
                INSERT INTO inbox (
                  bot_wxid, peer_wxid, from_wxid, to_wxid,
                  msg_type, category, content,
                  msg_id, new_msg_id, create_time, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        finally:
            conn.close()


async def append_sync_messages(client: LwApiClient, resp: SyncMessageResponse) -> None:
    bot = (client.wxid or "").strip()
    if not bot or not resp.addMsgs:
        return
    rows = _rows_from_add_msgs(bot, list(resp.addMsgs))
    await asyncio.to_thread(_insert_rows_sync, rows)


def _query_summary_sync(
    bot_wxid: Optional[str],
) -> dict[str, Any]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        try:
            _init_conn(conn)
            cur = conn.cursor()
            if bot_wxid and bot_wxid.strip():
                w = bot_wxid.strip()
                cur.execute("SELECT COUNT(*) FROM inbox WHERE bot_wxid = ?", (w,))
                total = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT msg_type, category, COUNT(*) AS c
                    FROM inbox WHERE bot_wxid = ?
                    GROUP BY msg_type, category
                    ORDER BY c DESC
                    """,
                    (w,),
                )
                by_type = [
                    {"msg_type": r[0], "label": r[1], "count": int(r[2])}
                    for r in cur.fetchall()
                ]
                cur.execute(
                    """
                    SELECT g.bot_wxid, g.peer_wxid, g.cnt, i.content, i.received_at
                    FROM (
                      SELECT bot_wxid, peer_wxid, COUNT(*) AS cnt, MAX(id) AS max_id
                      FROM inbox
                      WHERE bot_wxid = ?
                      GROUP BY bot_wxid, peer_wxid
                      ORDER BY cnt DESC
                      LIMIT 40
                    ) g
                    JOIN inbox i ON i.id = g.max_id
                    ORDER BY g.cnt DESC
                    """,
                    (w,),
                )
            else:
                cur.execute("SELECT COUNT(*) FROM inbox")
                total = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT msg_type, category, COUNT(*) AS c
                    FROM inbox
                    GROUP BY msg_type, category
                    ORDER BY c DESC
                    """
                )
                by_type = [
                    {"msg_type": r[0], "label": r[1], "count": int(r[2])}
                    for r in cur.fetchall()
                ]
                cur.execute(
                    """
                    SELECT g.bot_wxid, g.peer_wxid, g.cnt, i.content, i.received_at
                    FROM (
                      SELECT bot_wxid, peer_wxid, COUNT(*) AS cnt, MAX(id) AS max_id
                      FROM inbox
                      GROUP BY bot_wxid, peer_wxid
                      ORDER BY cnt DESC
                      LIMIT 40
                    ) g
                    JOIN inbox i ON i.id = g.max_id
                    ORDER BY g.cnt DESC
                    """
                )
            by_peer = [
                {
                    "bot_wxid": r[0],
                    "peer_wxid": r[1],
                    "count": int(r[2]),
                    "last_content": (r[3] or "")[:120],
                    "last_time": r[4],
                }
                for r in cur.fetchall()
            ]
            return {"total": total, "by_type": by_type, "by_peer": by_peer}
        finally:
            conn.close()


def _query_list_sync(
    *,
    bot_wxid: Optional[str],
    msg_type: Optional[int],
    peer_wxid: Optional[str],
    search: Optional[str],
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        try:
            _init_conn(conn)
            cur = conn.cursor()
            conds: List[str] = []
            params: List[Any] = []
            if bot_wxid and bot_wxid.strip():
                conds.append("bot_wxid = ?")
                params.append(bot_wxid.strip())
            if msg_type is not None:
                conds.append("msg_type = ?")
                params.append(int(msg_type))
            if peer_wxid and peer_wxid.strip():
                conds.append("peer_wxid = ?")
                params.append(peer_wxid.strip())
            if search and search.strip():
                conds.append("INSTR(LOWER(content), LOWER(?)) > 0")
                params.append(search.strip())
            where = (" WHERE " + " AND ".join(conds)) if conds else ""
            cur.execute(f"SELECT COUNT(*) FROM inbox{where}", params)
            total = int(cur.fetchone()[0])
            cur.execute(
                f"""
                SELECT id, bot_wxid, peer_wxid, from_wxid, to_wxid,
                       msg_type, category, content, create_time, received_at
                FROM inbox{where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            items = [
                {
                    "id": r[0],
                    "bot_wxid": r[1],
                    "peer_wxid": r[2],
                    "from_wxid": r[3],
                    "to_wxid": r[4],
                    "msg_type": r[5],
                    "category": r[6],
                    "content": r[7],
                    "create_time": r[8],
                    "received_at": r[9],
                }
                for r in cur.fetchall()
            ]
            return items, total
        finally:
            conn.close()


async def query_summary(bot_wxid: Optional[str] = None) -> dict[str, Any]:
    return await asyncio.to_thread(_query_summary_sync, bot_wxid)


async def query_list(
    *,
    bot_wxid: Optional[str] = None,
    msg_type: Optional[int] = None,
    peer_wxid: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    return await asyncio.to_thread(
        _query_list_sync,
        bot_wxid=bot_wxid,
        msg_type=msg_type,
        peer_wxid=peer_wxid,
        search=search,
        limit=limit,
        offset=offset,
    )


def _clear_inbox_sync() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        try:
            _init_conn(conn)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM inbox")
            n = int(cur.fetchone()[0])
            cur.execute("DELETE FROM inbox")
            conn.commit()
            return n
        finally:
            conn.close()


async def clear_inbox() -> int:
    return await asyncio.to_thread(_clear_inbox_sync)
