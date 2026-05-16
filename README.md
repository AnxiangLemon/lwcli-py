# lwapi-py

面向 **LwApi** 的 Python 项目：提供异步 **`lwapi/` SDK**，以及 **`src/`** 下的 aiohttp **Web 运维台**（多账号、扫码登录、插件链、消息入库与日志）。

**许可**：MIT，见 [LICENSE](LICENSE)。

**本文档以插件开发者为主**：如何发现/启用插件、处理消息、在不上线消息时主动发信、以及生命周期钩子。运维与打包见文末附录。

---

## 插件系统概览

```text
LwApi 消息同步
    │
    ▼
composite_message_handler（src/plugins/chain.py）
    │
    ├─► message_inbox：写入 config/messages.sqlite（供运维台「消息」页，失败不影响插件）
    │
    └─► 按 config/plugins.json 的 enabled 顺序，依次调用各插件 handle(client, resp)

BotService 账号上线/下线
    │
    ├─► client_registry：注册/注销在线 LwApiClient
    └─► lifecycle：对已启用插件调用 on_bot_online / on_bot_offline

Web 进程启动（aiohttp cleanup_ctx）
    │
    ├─► on_app_ready（每个已启用插件，一次）
    └─► start_background（每个已启用插件，进程级长驻协程）
```

两件事不要混用：

| 机制 | 作用 |
|------|------|
| **代码发现** | 启动时扫描 `plugins/lwplugin_*.py`，注册 `PLUGIN_ID` 与钩子；控制台会打印 id / 标题。 |
| **运行启用** | `config/plugins.json` 的 `enabled` 数组决定**哪些插件参与**消息链与生命周期；**顺序即 `handle` 执行顺序**。 |

仅改 `plugins.json` 可热更新启用列表（见下文）；**新增/修改插件 `.py` 必须重启进程**。

---

## 快速开始（插件作者）

```bash
pip install -r requirements.txt
python run.py
```

浏览器打开终端提示的地址（默认 `http://127.0.0.1:26121`）。在 **插件管理** 勾选你的 `PLUGIN_ID` 并保存，或编辑 `config/plugins.json`。

自定义插件目录（可选）：

```bash
export LWAPI_PLUGINS_DIR=/path/to/my-plugins   # 绝对路径，多项目共用一套插件
```

---

## 插件文件约定

| 规则 | 说明 |
|------|------|
| 路径 | `plugins/lwplugin_<名称>.py`，**仅扫描首层** |
| 前缀 | 文件名必须以 `lwplugin_` 开头 |
| 子目录 | `plugins/mybiz/*.py` **不会**被当作插件加载，可放私有业务代码 |
| 下划线文件 | 不以 `lwplugin_` 开头的文件（如 `_patterns.py`）**不会**加载 |

每个插件模块需提供：

| 符号 | 必填 | 说明 |
|------|------|------|
| `PLUGIN_ID` | 是 | 稳定唯一 id，写入 `plugins.json` 的 `enabled` |
| `PLUGIN_TITLE` | 否 | 运维台展示标题，默认用 id |
| `PLUGIN_DESCRIPTION` | 否 | 运维台说明 |
| `PLUGIN_VERSION` / `PLUGIN_AUTHOR` | 否 | 元数据，默认 `1.0.0` / 空 |
| `async def handle(client, resp)` | 是 | 消息回调入口 |
| `on_app_ready` / `on_bot_online` / `on_bot_offline` / `start_background` | 否 | 见下文「生命周期钩子」 |

`handle` 签名与 LwApi 一致：`(LwApiClient, SyncMessageResponse) -> None`，类型见 `lwapi.models.msg`。

---

## 第一步：最小消息插件

在 `plugins/` 下新建 `lwplugin_my_bot.py`：

```python
from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "my_bot"
PLUGIN_TITLE = "我的机器人"
PLUGIN_DESCRIPTION = "私聊「测试」时回复一句。"

async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    wxid = (client.wxid or "").strip()
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:  # 1 = 文本
            continue
        sender = (msg.fromUserName.string or "").strip()
        if sender == wxid:  # 忽略自己发出的回显，避免环路
            continue
        content = (msg.content.string or "").strip()
        if content == "测试":
            logger.info(f"[{PLUGIN_ID}] reply to {sender}")
            await client.msg.send_text_message(
                to_wxid=sender, content="插件已收到：测试"
            )
```

1. **重启** `python run.py`（新文件必须重启才会被扫描）。
2. 在运维台启用 `my_bot`，或把 `"my_bot"` 加入 `config/plugins.json` 的 `enabled`。
3. 启动对应账号机器人，私聊发送「测试」验证。

---

## 生命周期钩子（可选）

在 `lwplugin_*.py` 中按需定义以下 **async** 函数；**仅对已启用（`enabled`）的插件**调用。单个钩子抛错会被框架捕获并打日志，**不会**拖垮其它插件或账号。

| 钩子 | 调用时机 | 典型用途 |
|------|----------|----------|
| `on_app_ready()` | Web 进程启动后，每个已启用插件**一次** | 延迟 N 秒做初始化、发启动通知 |
| `on_bot_online(client)` | 某账号登录成功且消息监听已启动 | 欢迎语、拉取状态 |
| `on_bot_offline(wxid)` | 该账号下线或机器人任务结束 | 清理缓存；账号级后台协程会被框架 cancel |
| `start_background()` | 应用存活期间**一个**长驻协程 | 定时巡检所有在线账号 |

实现位置：`src/plugins/lifecycle.py`（由 `BotService` 与 `AdminWebApp` 挂载）。

### 主动拿在线客户端（不必等消息）

账号上线后，`LwApiClient` 会登记在 `src/runtime/client_registry.py`。插件内可：

```python
from src.runtime.client_registry import get_client, require_client, iter_online_clients

# 指定 wxid，未在线则抛错
client = await require_client("wxid_xxx")
await client.msg.send_text_message(to_wxid="filehelper", content="hello")

# 可能为 None
client = await get_client("wxid_xxx")

# 当前所有在线机器人 {wxid: client}
online = await iter_online_clients()
for wxid, client in online.items():
    ...
```

### 账号级后台协程（上线后延迟发信等）

在 `on_bot_online` 里用 `spawn_bot_task`，**该账号下线时自动 cancel**，无需自建任务表：

```python
from src.plugins.bot_tasks import spawn_bot_task

async def _welcome(client: LwApiClient) -> None:
    await asyncio.sleep(2)
    await client.msg.send_text_message(to_wxid="filehelper", content="已上线")

async def on_bot_online(client: LwApiClient) -> None:
    wxid = (client.wxid or "").strip()
    spawn_bot_task(wxid, _welcome(client), name=f"{PLUGIN_ID}:welcome")
```

### 进程启动后延迟执行

`on_app_ready` 内请自行 `asyncio.create_task`，避免阻塞启动：

```python
async def on_app_ready() -> None:
    async def _later() -> None:
        await asyncio.sleep(30)
        online = await iter_online_clients()
        if online:
            wxid, client = next(iter(online.items()))
            await client.msg.send_text_message(to_wxid="filehelper", content="启动提醒")
    asyncio.create_task(_later(), name=f"{PLUGIN_ID}:app-ready")
```

### 全事件示例

仓库内 **`plugins/lwplugin_my_hello.py`** 演示了 `handle`、`on_app_ready`、`on_bot_online`、`on_bot_offline`、`start_background` 与 `require_client`；顶部配置区填写 `BOT_WXID` / `TO_WXID`，留空则跳过对应逻辑。

群聊命令、@ 解析、防自回复可参考 **`plugins/lwplugin_demo_helper.py`**（`PLUGIN_ID = demo_helper`）。

---

## 配置：`config/plugins.json`

```json
{
  "enabled": ["demo_helper", "my_hello"]
}
```

| 操作 | 是否需要重启 |
|------|----------------|
| 修改 `enabled` 或顺序 | **否**（按文件 mtime 缓存失效，下一条消息或下一次生命周期即生效） |
| 新增/删除/重命名 `lwplugin_*.py` 或改插件代码 | **是** |

保存方式：运维台 **插件管理**（`PUT /api/plugins`），或手动编辑 JSON。`PUT` 会校验 id 必须已在注册表中存在。

首次无配置文件时，框架会生成默认 `enabled`（见 `src/plugins/settings.py` 中的 `DEFAULT_ENABLED`）。

---

## 处理消息时要注意什么

### 异常

`chain.py` 对每个 `handle` 包了一层 `try/except`：异常**不会**中断后续插件，但会 `logger.exception`。仍建议在插件内处理可预期错误。

### `addMsgs` 与类型

- 使用 `for msg in resp.addMsgs or []:`。
- `msgType == 1` 一般为文本；图片、语音等见 `src/message_inbox.py` 中的类型标签，或对照 LwApi 文档。
- `msg.content.string`、`msg.fromUserName.string` 可能为 `None`，请 `or ""`。

### 私聊与群聊

- **私聊**：`fromUserName` 多为对方 wxid；回复时 `to_wxid=sender`。
- **群聊**：`fromUserName` 常为 `xxx@chatroom`；正文常为 `发言者wxid:\n内容`，需自行解析（见 `demo_helper`）。建议用 `#命令`、@ 机器人或白名单，避免误回复。

### 避免回复环路

同步流里可能包含**本号刚发出的消息**。比较 `fromUserName` 与 `client.wxid`，或只响应明确触发条件。

### 多插件顺序

`enabled` 中靠前的插件先执行；**每个都会跑完**，前一个已回复不会阻止后一个——注意避免重复回复或逻辑冲突。

### 异步

`handle` 与钩子均须 `async def`；发送消息用 SDK 的 `await`，避免长时间同步阻塞。

---

## 发送消息（SDK）

文本优先：

```python
await client.msg.send_text_message(to_wxid=target, content="正文", at=None)
```

群聊 @ 成员：`at="wxid_a,wxid_b"` 或 `at="notify@all"`（见 `demo_helper`）。

更多类型与请求体模型见 **`lwapi/models/msg_requests.py`**，封装方法见 **`lwapi/apis/msg.py`**。

---

## 与框架其它模块的关系

| 模块 | 插件作者是否需要改 |
|------|-------------------|
| `src/plugins/registry.py` | 否，自动扫描 |
| `src/plugins/chain.py` | 否 |
| `src/message_handler.py` | 否，仅为兼容入口 |
| `src/message_inbox.py` | 否；入库在插件链之前，插件可读库做统计（一般不必） |
| `src/services/bot_service.py` | 否；负责登录、注册在线 client、触发 lifecycle |

升级上游时，**保留** `plugins/` 与 `config/plugins.json` 即可；业务请放在自有 `lwplugin_*.py` 或 `plugins/` 子目录。

---

## 附录 A：环境与启动

- **Python ≥ 3.9**
- 可访问的 **LwApi** 服务（默认 `http://localhost:8081`）

| 变量 | 默认值 | 含义 |
|------|--------|------|
| `LWAPI_BASE_URL` | `http://localhost:8081` | LwApi 根地址 |
| `LWAPI_WEB_HOST` | `127.0.0.1` | 运维台监听地址（仅本机；需局域网访问见下文「安全」） |
| `LWAPI_WEB_PORT` | `26121` | 运维台端口 |
| `LWAPI_PLUGINS_DIR` | `plugins`（项目根） | 插件目录 |
| `LWAPI_MSG_SYNC_MODE` | `websocket` | 消息同步：`websocket` 或 `http` |
| `LWAPI_OPEN_BROWSER` | 未设置 | 设为 `1`/`true` 时启动后打开浏览器 |

项目根 `.env` 会在 `bot_service` 导入时由 `load_dotenv()` 加载。

**扫码登录**：启动机器人前请先打开该账号页面并保持 **WebSocket**（`/ws/account/{idx}`），否则界面收不到二维码。

**安装依赖**：`pip install -r requirements.txt`（与 `pyproject.toml` 中依赖一致；也可 `pip install .` 安装本包）。

---

## 附录 A2：安全说明（部署前必读）

运维台 **未内置登录或 Token 鉴权**。任何能访问监听地址的客户端均可：查看/修改账号、启停机器人、发送消息、修改插件、清空消息库。

| 风险 | 说明 |
|------|------|
| 默认仅本机 | `LWAPI_WEB_HOST` 默认为 `127.0.0.1`，仅本机浏览器可访问。 |
| 暴露到局域网/公网 | 若改为 `0.0.0.0` 或公网 IP，务必配合防火墙、VPN 或反向代理 + 鉴权。 |
| 敏感数据 | `config/accounts.json`（含 device_id、wxid、代理）、`config/messages.sqlite`、`logs/` 含业务与聊天相关内容，请限制文件权限并定期备份。 |
| 插件代码 | `plugins/lwplugin_*.py` 在进程内以完整 Python 权限执行，仅放置可信代码。 |

生产环境建议：保持 `127.0.0.1`；远程管理用 SSH 隧道或带认证的反向代理，不要直接把运维台端口暴露到公网。

---

## 附录 B：运维台 API（插件相关）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/plugins` | 已发现插件元数据 + 当前 `enabled` |
| `PUT` | `/api/plugins` | body: `{"enabled": ["id1", "id2"]}` |

完整路由见 `src/web/app.py`。

---

## 附录 C：打包分发（简述）

使用 **PyInstaller** 在**目标系统**上分别打包；对方需自行部署 LwApi。解压后 `plugins/`、`config/` 与可执行文件同级（macOS 为 `.app` **所在文件夹**）。

| 系统 | 脚本 |
|------|------|
| Windows | `build/build-windows.bat` |
| Linux | `build/build-linux.sh` |
| macOS | `build/build-macos.sh` |

产物与 `.env.example` 说明见解压包内 **`使用说明.txt`**。开发运行：`python run.py`；打包运行：无需本机 Python。

---

## 仓库结构（与插件相关）

```text
lwapi-py/
├── lwapi/                    # LwApi Python SDK
├── plugins/                  # lwplugin_*.py（你的业务插件）
├── config/
│   ├── plugins.json          # enabled 列表
│   ├── accounts.json
│   └── messages.sqlite       # 消息入库（框架维护）
├── src/
│   ├── plugins/              # registry、chain、settings、lifecycle、bot_tasks
│   ├── runtime/              # client_registry、account_events
│   ├── message_handler.py    # → composite_message_handler
│   ├── message_inbox.py
│   └── services/bot_service.py
├── run.py
└── README.md
```
