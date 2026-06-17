# lwapi-py

面向 **LwApi** 的 Python 项目：提供异步 **`lwapi/` SDK**，以及 **`src/`** 下的 aiohttp **Web 运维台**（多账号、扫码登录、插件链、消息入库与日志）。

**许可**：MIT，见 [LICENSE](LICENSE)。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| `lwapi/` | LwApi 异步 SDK：登录、消息同步与发送、Events WebSocket 等 |
| Web 运维台 | 多账号管理、扫码登录、插件开关、消息与日志查看 |
| 插件系统 | `plugins/lwplugin_*.py` 扩展消息处理与生命周期钩子 |
| 消息入库 | 自动写入 `config/messages.sqlite`，供运维台「消息」页查询 |

更底层的登录与消息架构见 [docs/architecture.md](docs/architecture.md)。

---

## 环境要求

- **Python ≥ 3.9**
- 可访问的 **LwApi** 服务（默认 `http://localhost:8081`）

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
# 或安装本包
pip install .
```

### 2. 配置环境变量

复制模板并按需修改（开发环境可直接编辑项目根目录 `.env`）：

```bash
cp build/dist-template/.env.example .env
```

详见下文 **[环境变量（.env）](#环境变量env)**。

### 3. 启动

```bash
python run.py
```

浏览器打开终端提示的地址（默认 `http://127.0.0.1:26121`）。首次访问需输入运维台 Token（默认 `123123`）。

### 4. 添加账号并登录

在运维台添加账号后启动机器人。扫码登录时，请保持该账号详情页的 **WebSocket**（`/ws/account/{idx}`）连接，否则界面收不到二维码。

账号数据保存在 `config/accounts.json`；支持 `remote`（远程扫码）、`local`（本机 MMTLS 中继）、`json`（导入已有会话）等登录模式，见 [docs/architecture.md](docs/architecture.md)。

---

## 环境变量（.env）

项目根目录的 `.env` 在 `BotService` 导入时由 `python-dotenv` 自动加载（路径经 `src/app_paths.py` 解析，打包版与可执行文件同级）。**修改后需重启进程**。

完整模板见 [`build/dist-template/.env.example`](build/dist-template/.env.example)。

### 示例

```dotenv
# LwApi HTTP 服务地址
LWAPI_BASE_URL=http://localhost:8081

# 运维台监听
LWAPI_WEB_HOST=127.0.0.1
LWAPI_WEB_PORT=26121

# 消息同步：websocket 或 http
LWAPI_MSG_SYNC_MODE=websocket

# 运维台登录 Token（留空则关闭鉴权）
LWAPI_WEB_TOKEN=123123

# 日志
LWAPI_LOG_LEVEL=INFO

# Events WebSocket（JSON 账号收消息，可选）
EVENT_WS_ENABLED=1
EVENT_WS=ws://127.0.0.1:9725/api/ws/events
EVENT_KEY=your_manage_key
```

### LwApi 与运维台

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LWAPI_BASE_URL` | `http://localhost:8081` | LwApi HTTP 根地址；所有 SDK 请求发往 `{BASE_URL}/api/...` |
| `LWAPI_WEB_HOST` | `127.0.0.1` | 运维台监听地址。仅本机访问保持默认；局域网访问可改为 `0.0.0.0`（见[安全说明](#安全说明)） |
| `LWAPI_WEB_PORT` | `26121` | 运维台端口 |
| `LWAPI_OPEN_BROWSER` | 未设置（开发）/ `1`（打包版） | 设为 `1` / `true` / `yes` / `on` 时，启动后自动打开浏览器 |
| `LWAPI_WEB_TOKEN` | `123123` | 运维台登录 Token；**留空则关闭鉴权**（仅建议在可信内网使用） |

### 消息同步与插件

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LWAPI_MSG_SYNC_MODE` | `websocket` | 扫码 / remote 账号的消息同步方式：`websocket` 或 `http` |
| `LWAPI_PLUGINS_DIR` | 项目根 `plugins/` | 插件扫描目录的绝对路径；多项目可共用一套插件 |

### 日志

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LWAPI_LOG_LEVEL` | `INFO` | 全局日志级别（同时作用于控制台与文件，可被下面两项覆盖） |
| `LWAPI_LOG_CONSOLE_LEVEL` | 同 `LWAPI_LOG_LEVEL` | 仅控制台输出级别 |
| `LWAPI_LOG_FILE_LEVEL` | 同 `LWAPI_LOG_LEVEL` | 仅文件 `logs/{备注}_日期.log` |
| `LWAPI_LOG_ROTATION` | `10 MB` | 单日志文件轮转大小 |
| `LWAPI_LOG_RETENTION` | `7 days` | 日志保留时间 |

可选级别：`TRACE` `DEBUG` `INFO` `SUCCESS` `WARNING` `ERROR` `CRITICAL`（loguru 语义）。

**建议**：日常运行 `LWAPI_LOG_LEVEL=INFO`；排障时临时改为 `DEBUG`，复现后在运维台「日志」页查看 `logs/` 下对应文件。

### 在线保活

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LWAPI_SEC_AUTO_LOGIN_INTERVAL_SECONDS` | `172800`（48 小时） | 登录成功后周期性 `SecAutoAuth` 间隔（秒），最小 `3600` |

### Events WebSocket（JSON 账号收消息）

当账号 `login_mode` 为 `json`（通过 `ImportUser` 导入会话）时，消息可走 LwApi 管理端的 **Events WS hook**，而不依赖 per-account 的 `/ws/sync`。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EVENT_WS_ENABLED` | 未设置（关闭） | 设为 `1` / `true` / `yes` / `on` 时启用 Events WS |
| `EVENT_WS` | — | 管理端 WebSocket 地址，如 `ws://127.0.0.1:9725/api/ws/events` |
| `EVENT_KEY` | — | 管理端鉴权 key；客户端会自动附加为 URL 查询参数 `?key=...` |
| `EVENT_WS_RECONNECT_MIN_SEC` | `5` | 断线重连初始等待（秒），最小 `1` |
| `EVENT_WS_RECONNECT_MAX_SEC` | `120` | 断线重连最大等待（秒） |

启用逻辑（见 `lwapi/events_utils.py`）：

1. `EVENT_WS_ENABLED` 为真；
2. `EVENT_WS` 与 `EVENT_KEY` 均非空。

满足后，首个 JSON 账号上线时建立 WebSocket，消息经 `src/events_message_bridge.py` 分发给对应在线机器人与插件链；全部 JSON 账号下线后断开。连续重连失败达上限会停止相关账号，需手动重启。

`remote` / `local` 账号仍使用 `LWAPI_MSG_SYNC_MODE` 指定的同步通道，与 Events WS 独立。

---

## 安全说明

运维台默认启用 **Token 登录**（`LWAPI_WEB_TOKEN`）。首次访问跳转 `/login.html`；登录成功后通过 HttpOnly Cookie 维持会话。API 也可使用 `Authorization: Bearer <token>`。

| 风险 | 说明 |
|------|------|
| 默认仅本机 | `LWAPI_WEB_HOST=127.0.0.1`，仅本机浏览器可访问 |
| 暴露到局域网/公网 | 若改为 `0.0.0.0`，务必配合防火墙、VPN 或反向代理 + 强 Token |
| 敏感数据 | `config/accounts.json`、`config/messages.sqlite`、`logs/` 含会话与聊天内容，请限制文件权限 |
| 插件代码 | `plugins/lwplugin_*.py` 以完整 Python 权限执行，仅放置可信代码 |

生产环境建议：保持 `127.0.0.1`；远程管理用 SSH 隧道或带认证的反向代理，不要直接把运维台端口暴露到公网。

---

## 插件开发

插件是扩展业务的主要方式。框架在启动时扫描 `plugins/lwplugin_*.py`，运行时在 `config/plugins.json` 的 `enabled` 数组中决定**哪些插件参与**消息链与生命周期。

```text
LwApi 消息同步 / EVENT_WS
    │
    ▼
composite_message_handler（src/plugins/chain.py）
    │
    ├─► message_inbox → config/messages.sqlite
    └─► 按 plugins.json enabled 顺序调用各插件 handle(client, resp)

BotService 账号上线/下线
    ├─► client_registry：注册在线 LwApiClient
    └─► lifecycle：on_bot_online / on_bot_offline

Web 进程启动
    ├─► on_app_ready（每个已启用插件，一次）
    └─► start_background（进程级长驻协程）
```

### 文件约定

| 规则 | 说明 |
|------|------|
| 路径 | `plugins/lwplugin_<名称>.py`，**仅扫描首层** |
| 前缀 | 文件名必须以 `lwplugin_` 开头 |
| 子目录 | `plugins/mybiz/*.py` 不会被当作插件，可放私有业务代码 |

每个插件模块需提供：

| 符号 | 必填 | 说明 |
|------|------|------|
| `PLUGIN_ID` | 是 | 稳定唯一 id，写入 `plugins.json` 的 `enabled` |
| `PLUGIN_TITLE` / `PLUGIN_DESCRIPTION` | 否 | 运维台展示 |
| `PLUGIN_VERSION` / `PLUGIN_AUTHOR` / `PLUGIN_ICON` | 否 | 元数据 |
| `async def handle(client, resp)` | 是 | 消息回调；返回 `False` 时停止后续插件 |
| `on_app_ready` / `on_bot_online` / `on_bot_offline` / `start_background` | 否 | 生命周期钩子 |

### 最小示例

```python
from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "my_bot"
PLUGIN_TITLE = "我的机器人"

async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = (client.wxid or "").strip()
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:
            continue
        sender = (msg.fromUserName.string or "").strip()
        if sender == wxid:
            continue
        if (msg.content.string or "").strip() == "测试":
            await client.msg.send_text_message(to_wxid=sender, content="插件已收到：测试")
```

1. **重启** `python run.py`（新插件文件必须重启才会被扫描）。
2. 在运维台启用 `my_bot`，或编辑 `config/plugins.json`。
3. 启动对应账号机器人并私聊发送「测试」验证。

### 配置 `config/plugins.json`

```json
{
  "enabled": ["demo_helper", "my_bot"]
}
```

| 操作 | 是否需要重启 |
|------|----------------|
| 修改 `enabled` 或顺序 | **否**（下一条消息或下一次生命周期即生效） |
| 新增/修改/删除 `lwplugin_*.py` | **是** |

### 主动获取在线客户端

```python
from src.runtime.client_registry import get_client, require_client, iter_online_clients

client = await require_client("wxid_xxx")  # 未在线则抛错
await client.msg.send_text_message(to_wxid="filehelper", content="hello")
```

更多示例见 `plugins/lwplugin_demo_helper.py`、`plugins/lwplugin_my_demo.py`。

### 运维台 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/plugins` | 已发现插件元数据 + 当前 `enabled` |
| `PUT` | `/api/plugins` | body: `{"enabled": ["id1", "id2"]}` |

---

## 仓库结构

```text
lwapi-py/
├── lwapi/                    # LwApi Python SDK
├── plugins/                  # lwplugin_*.py（业务插件）
├── config/
│   ├── plugins.json          # 已启用插件列表
│   ├── accounts.json         # 账号配置
│   └── messages.sqlite       # 消息入库（框架维护）
├── src/
│   ├── plugins/              # registry、chain、lifecycle
│   ├── runtime/              # client_registry、events_ws_holder
│   ├── services/bot_service.py
│   └── web/                  # 运维台前端与 API
├── docs/architecture.md      # 登录与消息架构说明
├── build/dist-template/.env.example
├── run.py
└── README.md
```

