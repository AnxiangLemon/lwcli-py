# models/msg.py
from pydantic import BaseModel
from typing import List, Optional

class SKBuiltinString_t(BaseModel):
    """内置字符串类型"""
    string: Optional[str] = None  # 字符串内容

class SKBuiltinBuffer_t(BaseModel):
    """内置缓冲区类型"""
    iLen: Optional[int] = None    # 缓冲区长度
    buffer: Optional[bytes] = None  # 缓冲区内容

class AddMsg(BaseModel):
    """新增消息结构"""
    msgId: int                    # 消息ID
    fromUserName: SKBuiltinString_t  # 发送者用户名
    toUserName: SKBuiltinString_t    # 接收者用户名
    msgType: int                    # 消息类型
    content: SKBuiltinString_t      # 消息内容
    status: int                     # 消息状态
    imgStatus: int                  # 图片状态
    imgBuf: SKBuiltinBuffer_t       # 图片缓冲区
    createTime: int                 # 创建时间戳
    msgSource: Optional[str] = None  # 消息来源
    pushContent: Optional[str] = None  # 推送内容
    newMsgId: Optional[int] = None    # 新消息ID
    msgSeq: Optional[int] = None     # 消息序列号

class SyncMessageResponse(BaseModel):
    """同步消息响应结构"""
    modUserInfos: Optional[List] = []    # 修改的用户信息
    modContacts: Optional[List] = []      # 修改的联系人
    delContacts: Optional[List] = []      # 删除的联系人
    functionSwitchs: Optional[List] = []  # 功能开关
    addMsgs: Optional[List[AddMsg]] = []  # 新增消息
    modUserImgs: Optional[List] = []      # 修改的用户头像
    userInfoExts: Optional[List] = []     # 用户扩展信息
    snsObjects: Optional[List] = []       # SNS对象
    snsActionGroups: Optional[List] = []  # SNS操作组
    delChatContacts: Optional[List] = []  # 删除的聊天联系人
    modChatRoomMembers: Optional[List] = [] # 修改的聊天室成员
    quitChatRooms: Optional[List] = []    # 退出的聊天室
    modChatRoomNotifys: Optional[List] = []  # 修改的聊天室通知
    modChatRoomTopics: Optional[List] = []   # 修改的聊天室主题
    keyBuf: Optional[SKBuiltinBuffer_t] = None  # 同步密钥