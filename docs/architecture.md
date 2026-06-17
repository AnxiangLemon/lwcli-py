# LwApi 核心架构说明

本文档描述 **lwapi-py** 项目中与 **登录**、**消息收发** 相关的核心架构，面向将 SDK 移植到 Rust（或其它语言）的开发者。不涉及插件系统、Web 运维台 UI 等上层功能。

---

## 1. 整体架构

本项目本质是 **LwApi 服务的异步 HTTP/WebSocket 客户端**，不直接连接微信协议，而是连接自部署的 LwApi 网关（默认 `http://localhost:8081`）。

```
┌─────────────────────────────────────────────────────────┐
│  业务编排层（src/）                                       │
│  BotService：多账号协程、登录编排、消息监听、在线 client 注册 │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  SDK 层（lwapi/）—— 移植时主要对标这一层                  │
│  LwApiClient                                            │
│    ├── transport   HTTP POST + X-Wxid 请求头              │
│    ├── login       远程扫码登录 + SecAutoAuth 保活         │
│    ├── relay       本机 MMTLS 中继登录（local 模式）       │
│    └── msg         消息同步（轮询 / WebSocket）+ 发送接口  │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────▼────────────────────────────────────┐
│  LwApi 服务端（外部部署）                                  │
│  维护微信会话、心跳、加解密；暴露 REST 与 WS 接口           │
└─────────────────────────────────────────────────────────┘
```

**Rust 移植最小集**：`Transport` + `LwApiClient` + `LoginClient` + `MsgClient`（若使用 local 登录模式，另加 `RelayClient`）。

---

## 2. HTTP 传输层

所有 REST 调用经 `AsyncHTTPTransport` 统一封装（见 `lwapi/transport.py`）。

### 2.1 URL 规则

```
{base_url}/api/{path}
```

示例：`/Login/GetQRCode` → `http://localhost:8081/api/Login/GetQRCode`

### 2.2 请求约定

| 项目 | 说明 |
|------|------|
| 方法 | `POST` |
| 请求头 | 登录后每条请求带 `X-Wxid: {wxid}` |
| 请求体 | JSON，字段名为 **camelCase**（如 `deviceId`、`toWxid`） |
| 默认超时 | 30 秒（消息 Sync 接口单独设为 180 秒） |

`wxid` 通过 `client.set_wxid(wxid)` 写入 `ClientConfig`，transport 自动附加到请求头。

### 2.3 响应信封

所有接口返回统一外层结构（`lwapi/models/base.py`）：

```json
{
  "code": 200,
  "message": "",
  "data": { }
}
```

| `code` | 处理 |
|--------|------|
| `200` | 成功，业务数据在 `data` |
| 其它 | 失败，抛出 `ApiError` |

特殊：`SecAutoAuth` 返回 `code == -1019` 表示本地缓存失效，属于正常分支，随后走扫码登录。

### 2.4 Relay 专用接口

`RelayClient` 使用 `post_envelope()`，返回 `(code, message, data)` 三元组，**不因 `code != 200` 抛异常**，以便处理 `-2020`、`needInit` 等中间状态。

---

## 3. 登录流程

登录成功后获得唯一会话标识 **`wxid`**，写入 client 配置，后续所有 API 自动携带 `X-Wxid` 头。

### 3.1 三种登录模式

| `login_mode` | 实现 | 说明 |
|--------------|------|------|
| `local`（默认） | `RelayLoginService` + `RelayClient` | 客户端本机 IP 直连微信 MMTLS；LwApi 负责组包、加解密、会话存储 |
| `remote` | `LoginService` + `LoginClient` | 登录逻辑完全在 LwApi 服务端执行 |
| `json` | `ImportUser` | 导入外部已有会话 JSON，跳过扫码 |

### 3.2 通用状态机

```
开始
  │
  ├─ 本地有 wxid？─是─► SecAutoAuth 二次登录
  │                        │
  │                        ├─ 成功 ──► set_wxid ──► 保活 + 消息监听
  │                        └─ 失败 ──► 获取二维码
  │
  └─ 无 wxid ─────────────► 获取二维码
                               │
                               ▼
                          轮询扫码状态
                               │
                               ├─ 成功 ──► set_wxid ──► 保活 + 消息监听
                               └─ 失败（取消/过期/超时）──► 重试或退出
```

### 3.3 Remote 模式（LoginClient）

对应文件：`lwapi/apis/login.py`、`src/login_service.py`

#### 步骤 1：二次登录（可选）

```
POST /api/Login/SecAutoAuth
Header: X-Wxid: {saved_wxid}
```

- 成功：`baseResponse.ret == 0`，无需扫码
- 失败：缓存失效（`code == -1019`），进入扫码流程

#### 步骤 2：获取二维码

```
POST /api/Login/GetQRCode
Body: {
  "deviceId": "...",
  "osType": 0,
  "proxy": { "host": null, "port": null, "type": null }
}
```

响应 `data` 字段：

| 字段（JSON 别名） | 说明 |
|-------------------|------|
| `Uuid` | 二维码 UUID，用于轮询 |
| `QrBase64` | 二维码图片 Base64 |
| `QrUrl` | 扫码 URL |
| `DeviceId` | 设备 ID（可能回写） |
| `ExpiredTime` | 过期时间（秒） |

#### 步骤 3：轮询扫码状态

```
POST /api/Login/CheckQRCode?uuid={uuid}
```

轮询间隔建议 3 秒，总超时 300 秒。

二维码状态（`QRStatus`）：

| `status` | 含义 |
|----------|------|
| `0` | 未扫码 |
| `1` | 已扫码 |
| `2` | 确认中 |
| `4` | 已取消 |
| `-2007` | 已过期 |

登录成功条件：`ret == 0` 且响应含 `acctSectResp.userName`（即 wxid）。

#### 步骤 4：登录后保活

调用 `login.start_keepalive(sec_interval=48*3600)` 启动后台协程，周期性调用 `SecAutoAuth`（默认每 48 小时）。

> 心跳与环境上报由 **LwApi 服务端**维护，客户端不再单独发送 `HeartBeat` / `Reportclientcheck`。

### 3.4 Local 模式（RelayClient）

对应文件：`lwapi/apis/relay.py`、`src/relay_login_service.py`

与 remote 的区别：LwApi 返回 `HttpSpec`（`url`、`headers`、hex `body`），**客户端用本机网络 POST 到微信 MMTLS 端点**，服务端负责加解密与会话存储。

流程概要：

1. `ensure_init` — 初始化 relay 会话
2. `sec_auto_auth` — 有 wxid 时尝试二次登录
3. 扫码流程：
   - `qr_get` → 返回 `qrImage`
   - 循环 `qr_check`，根据 `scanState` 推送状态（0 等待 / 1 已扫 / 2 确认 / 4 取消）
   - `sec_manual_auth` → `login_ok` 含 wxid

扫码事件类型：`qr_ready` | `status` | `success` | `error`

### 3.5 JSON 导入模式

对应文件：`src/login_service.py`（`build_import_user_payload`）

```
POST /api/Login/ImportUser
Body: {
  "wxid", "UIN", "ClientVer", "DeviceId", "DeviceType", "Host",
  "SessionKey", "Cookie", "SharedKey", "EarlyDataPart", "PSKAccessKey"
}
```

成功后 `set_wxid`，**不启动** `SecAutoAuth` 保活（会话由服务端维护）。

必填字段：`wxid`、`UIN`、`ClientVer`、`DeviceId`、`SessionKey`、`Cookie`、`SharedKey`、`EarlyDataPart`、`PSKAccessKey`。

---

## 4. 消息接收

登录成功并 `set_wxid` 后，调用 `msg.start(handler, mode, wxid)` 启动监听。

环境变量 `LWAPI_MSG_SYNC_MODE` 控制同步方式，默认 `websocket`。

### 4.1 HTTP 长轮询（poll）

```
循环:
  POST /api/Msg/Sync   (timeout = 180s)
  → 解析 SyncMessageResponse
  → 若 addMsgs 非空，调用 handler(client, resp)
  → sleep(interval)   # 默认 1s
```

别名：`poll`、`http`、`longpoll` 均归一化为 `poll`。

### 4.2 WebSocket 推送（websocket，推荐）

URL 构造规则（`lwapi/sync_utils.py`）：

```
http://127.0.0.1:8081  +  wxid_xxx
  →  ws://127.0.0.1:8081/ws/sync?wxid=wxid_xxx

https://...  →  wss://...
```

连接参数：

| 参数 | 值 |
|------|-----|
| 心跳间隔 | 30 秒 |
| 读超时 | 90 秒（超时后重连） |
| 重连退避 | 指数退避，上限 30 秒 |

收到 TEXT / BINARY 帧后，解析为 `SyncMessageResponse`，再分发给 handler。

### 4.3 消息数据结构

核心模型见 `lwapi/models/msg.py`。

**SyncMessageResponse**（同步响应）：

| 字段 | 说明 |
|------|------|
| `addMsgs` | 新增消息列表（主要关注） |
| `modContacts` | 联系人变更 |
| `modChatRoomMembers` | 群成员变更 |
| 其它 | 用户信息、SNS 等同步字段 |

**AddMsg**（单条消息）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `msgId` / `newMsgId` | int | 消息 ID |
| `fromUserName.string` | str | 发送者（群聊为 `xxx@chatroom`） |
| `toUserName.string` | str | 接收者 |
| `msgType` | int | 消息类型（1=文本，3=图片，34=语音…） |
| `content.string` | str | 正文（群聊常为 `发言者wxid:\n内容`） |
| `createTime` | int | Unix 时间戳 |
| `status` | int | 消息状态 |
| `msgSource` | str | 消息来源（可选） |

### 4.4 WebSocket 载荷兼容格式

解析时需兼容三种 JSON 形态：

1. 裸 data：`{ "addMsgs": [...] }`
2. 包装 data：`{ "code": 200, "data": { "addMsgs": [...] } }`
3. 完整 ApiResponse 信封

### 4.5 Handler 签名

```python
async def handler(client: LwApiClient, resp: SyncMessageResponse) -> None:
    for msg in resp.addMsgs or []:
        ...
```

---

## 5. 消息发送

发送是 **主动 HTTP POST**，与消息监听循环独立。

### 5.1 发送文本（最常用）

```
POST /api/Msg/SendTxt
Header: X-Wxid: {bot_wxid}
Body: {
  "toWxid": "对方wxid 或 群id@chatroom",
  "content": "消息正文",
  "at": "wxid1,wxid2"    // 群聊 @，可选；@全体用 notify@all
}
```

请求体模型：`SendNewMsgParam`（`lwapi/models/msg_requests.py`），Python 侧 snake_case 字段经 `.to_api()` 转为 camelCase JSON。

### 5.2 其它发送接口

| 路径 | 用途 |
|------|------|
| `/Msg/UploadImg` | 图片（Base64） |
| `/Msg/SendVoice` | 语音 |
| `/Msg/SendVideo` | 视频 |
| `/Msg/SendApp` | 小程序 |
| `/Msg/Revoke` | 撤回 |
| `/Msg/ShareCard` | 名片 |
| `/Msg/ShareLink` | 链接 |
| `/Msg/SendCDNImg` | 转发 CDN 图片 |
| `/Msg/SendCDNVideo` | 转发 CDN 视频 |
| `/Msg/SendEmoji` | 表情 |
| `/Msg/SendQuote` | 引用回复 |
| `/Msg/ShareLocation` | 地理位置 |

完整列表见 `lwapi/apis/msg.py`。

### 5.3 发送与接收的关系

- 发送后，本号发出的消息可能通过同步流 **回显** 到 `addMsgs`
- 处理消息时应比较 `fromUserName` 与 `client.wxid`，避免回复环路

---

## 6. 单账号生命周期（BotService）

`src/services/bot_service.py` 中每个账号一个 asyncio Task，主循环如下：

```
1. 创建 LwApiClient(base_url)
2. 按 login_mode 选择 LoginService / RelayLoginService
3. login(saved_wxid) → 获得 wxid、device_id
4. 持久化 wxid / device_id 到 accounts.json
5. client.login.start_keepalive()      # SecAutoAuth 保活
6. client.msg.start(handler, mode, wxid)  # 消息监听
7. register_online_client(wxid, client)   # 供主动发消息查找
8. await hold_future()                    # 阻塞直至任务取消
9. client.aclose()                        # 停止 WS/轮询 + 保活 + 关闭连接池
```

主动发消息路径：

```
send_text_message(bot_wxid, to_wxid, content)
  → client_registry.get_client(bot_wxid)
  → client.msg.send_text_message(to_wxid, content)
```

---

## 7. 关键环境变量

| 变量 | 默认值 | 含义 |
|------|--------|------|
| `LWAPI_BASE_URL` | `http://localhost:8081` | LwApi 根地址 |
| `LWAPI_MSG_SYNC_MODE` | `websocket` | 消息同步：`websocket` 或 `poll` |
| `LWAPI_SEC_AUTO_LOGIN_INTERVAL_SECONDS` | `172800`（48h） | SecAutoAuth 间隔，最小 3600 |

---

## 8. Rust 移植建议

### 8.3 最小可运行路径（不含 relay）

1. `POST /Login/GetQRCode` 获取二维码
2. 轮询 `POST /Login/CheckQRCode?uuid=...`
3. `set_wxid`，后续请求带 `X-Wxid`
4. 连接 `ws://host/ws/sync?wxid=...` 收消息
5. `POST /Msg/SendTxt` 发消息
6. 后台任务周期性 `POST /Login/SecAutoAuth` 保活

### 8.4 状态持久化

每账号建议持久化：

| 字段 | 说明 |
|------|------|
| `device_id` | 设备标识，获取二维码时使用 |
| `wxid` | 登录成功后写入，用于二次登录与请求头 |
| `proxy` | 可选代理配置 |

二次登录依赖 LwApi **服务端**侧会话缓存；客户端只需记住 `wxid` 并在请求头携带。

---

## 9. 相关源码索引

| 模块 | 路径 | 职责 |
|------|------|------|
| SDK 入口 | `lwapi/client.py` | `LwApiClient` 聚合 |
| HTTP 传输 | `lwapi/transport.py` | POST、信封解析、X-Wxid |
| 配置 | `lwapi/config.py` | base_url、wxid |
| 远程登录 | `lwapi/apis/login.py` | 二维码、SecAutoAuth、保活 |
| 中继登录 | `lwapi/apis/relay.py` | local MMTLS 流程 |
| 消息 | `lwapi/apis/msg.py` | 同步、发送 |
| WS URL | `lwapi/sync_utils.py` | 同步模式归一化、WS 地址 |
| 消息模型 | `lwapi/models/msg.py` | AddMsg、SyncMessageResponse |
| 发送请求体 | `lwapi/models/msg_requests.py` | SendNewMsgParam 等 |
| 登录模型 | `lwapi/models/login.py` | QR 请求/响应 |
| 登录编排 | `src/login_service.py` | remote / json 登录流程 |
| 中继编排 | `src/relay_login_service.py` | local 登录流程 |
| 多账号运行时 | `src/services/bot_service.py` | 登录 → 监听 → 发消息 |
| 在线 client | `src/runtime/client_registry.py` | 按 wxid 查找 client |

---

## 10. 与 Web 运维台的关系

`src/web/` 为 aiohttp 运维台，提供账号管理、扫码事件 WebSocket 推送、消息入库等功能，**与 LwApi SDK 核心逻辑无关**。

移植纯 Rust bot 时可直接实现 `LoginService` 逻辑 + 消息 handler，无需复现 Web 层。

运维台 Token 鉴权（`LWAPI_WEB_TOKEN`）是 Web 层独立机制，与微信登录无关。
