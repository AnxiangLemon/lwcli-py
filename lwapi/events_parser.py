"""Events WebSocket 消息解析：hex protobuf → Pydantic AddMsg。"""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from lwapi.models.msg import (
    AddMsg,
    SKBuiltinBuffer_t,
    SKBuiltinString_t,
    SyncMessageResponse,
)
from lwapi.proto import addmsg_pb2


def _pb_string(pb: addmsg_pb2.SKBuiltinString_t) -> SKBuiltinString_t:
    return SKBuiltinString_t(
        string=pb.string if pb.HasField("string") else None,
    )


def _pb_buffer(pb: addmsg_pb2.SKBuiltinBuffer_t) -> SKBuiltinBuffer_t:
    return SKBuiltinBuffer_t(
        iLen=pb.iLen,
        buffer=pb.buffer if pb.HasField("buffer") else None,
    )


def pb_to_addmsg(pb: addmsg_pb2.AddMsg) -> AddMsg:
    """将 protobuf AddMsg 转为 Pydantic 模型。"""
    return AddMsg(
        msgId=pb.msgId,
        fromUserName=_pb_string(pb.fromUserName),
        toUserName=_pb_string(pb.toUserName),
        msgType=pb.msgType,
        content=_pb_string(pb.content),
        status=pb.status,
        imgStatus=pb.imgStatus,
        imgBuf=_pb_buffer(pb.imgBuf),
        createTime=pb.createTime,
        msgSource=pb.msgSource if pb.HasField("msgSource") else None,
        pushContent=pb.pushContent if pb.HasField("pushContent") else None,
        newMsgId=pb.newMsgId if pb.HasField("newMsgId") else None,
        msgSeq=pb.msgSeq if pb.HasField("msgSeq") else None,
    )


def parse_addmsg_from_hex(hex_str: str) -> AddMsg:
    """将十六进制字符串解码并反序列化为 AddMsg。"""
    cleaned = "".join((hex_str or "").split())
    if not cleaned:
        raise ValueError("hex 字符串为空")
    try:
        data = bytes.fromhex(cleaned)
    except ValueError as e:
        raise ValueError(f"hex 解码失败: {e}") from e

    pb = addmsg_pb2.AddMsg()
    try:
        pb.ParseFromString(data)
    except Exception as e:
        raise ValueError(f"protobuf 反序列化失败: {e}") from e
    return pb_to_addmsg(pb)


def parse_ws_envelope(
    raw: str | bytes | dict[str, Any],
) -> tuple[str, AddMsg] | None:
    """
    解析 Events WS 推送的 JSON 信封。

    返回 (type, AddMsg)；无法识别或解析失败时返回 None。
    """
    if isinstance(raw, (str, bytes)):
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Events WS 消息非 JSON: {e}")
            return None
    elif isinstance(raw, dict):
        payload = raw
    else:
        return None

    if not isinstance(payload, dict):
        return None

    msg_type = str(payload.get("type") or "").strip()
    if not msg_type:
        logger.debug("Events WS 消息缺少 type 字段，已忽略")
        return None
    if msg_type != "wx_message":
        logger.debug(f"Events WS 暂未处理的消息类型: {msg_type}")
        return None

    hex_str = str(payload.get("hex") or "").strip()
    if not hex_str:
        logger.warning("Events WS wx_message 缺少 hex 字段")
        return None

    try:
        add_msg = parse_addmsg_from_hex(hex_str)
    except ValueError as e:
        logger.warning(f"Events WS wx_message 解析失败: {e}")
        return None

    return msg_type, add_msg


def addmsg_to_sync_response(msg: AddMsg) -> SyncMessageResponse:
    """将单条 AddMsg 包装为 SyncMessageResponse，供后续插件链并行接入。"""
    return SyncMessageResponse(addMsgs=[msg])
