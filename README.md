# lwapi-py

面向 **LwApi** 的 Python 仓库：提供异步 **`lwapi/` SDK**，以及 **`src/`** 下的 aiohttp **Web 运维台**——管理多账号、扫码登录、按插件链处理同步消息、查看日志与账号级 WebSocket 事件。

---

## 环境要求与启动

- **Python ≥ 3.9**
- 已部署且可访问的 **LwApi** 服务（默认 `http://localhost:8081`）

```bash
pip install -r requirements.txt
python run.py
```

默认运维台监听 **`0.0.0.0:8090`**，浏览器打开终端打印的地址（本机一般为 `http://127.0.0.1:8090`）。启动机器人做扫码登录前，**请先打开对应账号页面并保持 WebSocket 连接**，否则界面收不到二维码（见下文「扫码与 WebSocket」）。

### 环境变量

| 变量 | 默认值 | 含义 |
|------|--------|------|
| `LWAPI_BASE_URL` | `http://localhost:8081` | LwApi 根地址；`BotService` 创建 `LwApiClient` 时使用。 |
| `LWAPI_WEB_HOST` | `0.0.0.0` | 运维台监听地址。 |
| `LWAPI_WEB_PORT` | `8090` | 运维台端口。 |

可在项目根目录放置 **`.env`**：`src/services/bot_service.py` 在导入时会执行 `load_dotenv()`。

### 配置文件（简要）

| 路径 | 作用 |
|------|------|
| `config/accounts.json` | 多账号列表（`device_id`、`wxid`、`remark`、`proxy` 等）。 |
| `config/plugins.json` | `enabled` 数组：已注册插件的 **id** 及 **执行顺序**。 |

---

## 仓库结构

```text
lwapi-py/
├── lwapi/                 # LwApi Python SDK（HTTP、登录、消息等）
├── src/
│   ├── main.py            # Web 进程入口
│   ├── account_loader.py  # accounts.json 读写 + account_slot_key
│   ├── login_service.py   # 二次登录 + 二维码流式登录（依赖 Web emit）
│   ├── message_handler.py # 消息回调入口 → 插件链
│   ├── utils.py           # 日志、原子写 JSON、读日志尾等工具
│   ├── plugins/           # 消息插件注册表、配置、builtin_* 实现
│   ├── runtime/           # 账号级 WebSocket 事件总线
│   ├── services/          # bot_service、二维码渲染等
│   └── web/               # aiohttp 路由与静态前端
├── config/                # accounts.json、plugins.json（运行时生成或自备）
├── logs/                  # 按备注分文件的滚动日志
├── run.py                 # 启动运维台
├── requirements.txt
└── README.md
```

---

## 编写第一个插件（详细步骤与注意事项）

### 插件是什么、何时被调用

LwApi 消息同步会在一批数据到达时回调 **`composite_message_handler`**（见 `src/plugins/chain.py`）。它会读取 `config/plugins.json` 中的 **`enabled`**，用 `registry.resolve_handlers` 转成有序的 `PluginSpec` 列表，再**依次**调用每个插件的 **`handle(client, resp)`**。

因此你要弄清两件事：

1. **代码注册**：你的插件必须出现在 `registry.py` 的 `_ALL` 里，进程启动时 Python 已 import，运维台 `GET /api/plugins` 才能列出它。
2. **运行启用**：`plugins.json` 的 `enabled` 里要包含你的 **`PLUGIN_ID`**，且顺序即执行顺序。

### 第一步：新建插件模块

在 `src/plugins/` 下新建文件，例如 **`my_hello.py`**。每个插件模块通常包含四样**约定俗成**的元数据常量 + 一个异步入口函数 **`handle`**：

| 约定项 | 说明 |
|--------|------|
| `PLUGIN_ID` | **稳定唯一**字符串，写入 `plugins.json` 的 `enabled`；勿随意改名，否则已保存配置会失效。 |
| `PLUGIN_TITLE` | 运维台展示用短标题。 |
| `PLUGIN_DESCRIPTION` | 运维台展示用说明。 |
| `async def handle(client, resp)` | 与 `MsgClient` 回调一致：第一个参数为 **`LwApiClient`**，第二个为 **`SyncMessageResponse`**（见 `lwapi.models.msg`）。 |

**最小可用示例**（仅私聊文本里回复固定句，便于验证链路）：

```python
# src/plugins/my_hello.py
from __future__ import annotations

from loguru import logger

from lwapi import LwApiClient
from lwapi.models.msg import SyncMessageResponse

PLUGIN_ID = "my_hello"
PLUGIN_TITLE = "示例：你好世界"
PLUGIN_DESCRIPTION = "收到私聊文本「测试」时回复一句确认。"


async def handle(client: LwApiClient, resp: SyncMessageResponse) -> None:
    for msg in resp.addMsgs or []:
        if msg.msgType != 1:
            continue  # 1 = 普通文本，其它类型请按需处理或跳过

        raw = msg.content.string or ""
        content = raw.strip()
        sender = msg.fromUserName.string or ""

        if content == "测试":
            logger.info(f"[{PLUGIN_ID}] reply to {sender}")
            await client.msg.send_text_message(to_wxid=sender, content="插件已收到：测试")
```

### 第二步：注册到 `registry.py`

1. 在文件头部 **import** 你的模块，例如：  
   `from src.plugins.my_hello import PLUGIN_DESCRIPTION as _HELLO_DESC, PLUGIN_ID as _HELLO_ID, PLUGIN_TITLE as _HELLO_TITLE, handle as _hello_handle`
2. 在 `_ALL` 元组中追加一个 **`PluginSpec`**：

```python
PluginSpec(
    id=_HELLO_ID,
    title=_HELLO_TITLE,
    description=_HELLO_DESC,
    handle=_hello_handle,
    version="0.1.0",
    author="你的名字",
),
```

**重要**：修改 `registry.py` 或**新增/重命名插件文件**后，必须 **重启 `python run.py` 进程**，Python 才会重新加载模块；仅靠改 `plugins.json` **不能**让「从未 import 过的新文件」生效。

### 第三步：启用插件

任选其一：

- 打开运维台 **插件管理**，勾选你的插件并保存（会调用 `PUT /api/plugins`）。
- 或手动编辑 `config/plugins.json`，在 `enabled` 数组中加入 **`my_hello`**（或你定义的 `PLUGIN_ID`）。

`enabled` 的**数组顺序**就是插件执行顺序：排在前面的先执行。若前一个插件已经回复了消息，后一个仍会执行——注意避免重复回复或逻辑打架。

### 第四步：验证

1. 重启进程（若刚改过 `registry.py`）。
2. 确认 `plugins.json` 里包含你的 id。
3. 启动对应账号机器人，私聊发送「测试」，观察日志与是否收到回复。

---

## 编写插件时应注意的事项

### 1. 异常与稳定性

`chain.py` 对每个插件的 `handle` 包了 **`try/except`**：你抛出的异常**不会**中断后续插件，但会打 **`logger.exception`**。仍建议在插件内对**可预期错误**自行处理，并避免在循环里抛未捕获异常刷屏。

### 2. `resp.addMsgs` 与消息类型

- `SyncMessageResponse.addMsgs` 是一批新消息，可能为空；建议写 **`for msg in resp.addMsgs or []:`**。
- 常见 **`msg.msgType == 1`** 为普通文本；图片、语音、系统消息等类型请参考 `builtin_debug_types.py` 或 LwApi 文档，**不要假设全是文本**。
- **`msg.content.string`**、**`msg.fromUserName.string`** 在模型里可能为 `None`，使用前建议 **`or ""`**，避免 `AttributeError`。

### 3. 私聊与群聊

- **私聊**：`fromUserName` 多为对方 wxid；发消息时 **`to_wxid`** 常用该 sender。
- **群聊**：`fromUserName` 常为 **`xxx@chatroom`**；正文里常带 **`发言者wxid:\n正文`** 前缀，需要自己拆分或参考 `builtin_text_helper.py` 的做法。若不想在群里误触自动回复，应加 **@机器人**、**固定前缀** 或关键词白名单等策略。

### 4. 避免「自己回自己」环路

同步下来的消息里可能包含**自己刚发出的消息**的回显。若插件对「包含某关键词」就自动回复，容易形成循环。应对 **`fromUserName`** 与当前 **`client.wxid`** 做判断，或忽略明显由本号发出的同步（具体字段以你抓包为准）；内置 `text_helper` 文档中也强调了类似防护思路。

### 5. 性能与异步

`handle` 必须是 **`async def`**。内部请 **`await`** SDK 的异步发送接口；**不要在插件里写长时间阻塞的同步 IO**，否则会拖慢整条消息链与后续插件。

### 6. 配置热更新 vs 代码热更新

| 操作 | 是否需要重启进程 |
|------|------------------|
| 只改 `config/plugins.json` 的 `enabled` 或顺序 | **一般不需要**（依赖 mtime 缓存失效后下一轮消息生效）。 |
| 改插件 **Python 代码**、改 **`registry.py`**、**新增插件文件** | **需要重启**。 |

### 7. 与内置插件对照学习

建议阅读顺序：`builtin_demo_replies.py`（最小闭环）→ `builtin_debug_types.py`（类型过滤）→ `builtin_text_helper.py`（群聊、字段、防环路）。发送接口参数还可对照 `lwapi/models/msg_requests.py` 。

---

## 运维台 HTTP API（速查）

更完整的路径与状态码以 `src/web/app.py` 为准。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 运维台首页。 |
| `GET` | `/api/accounts` | 账号列表（含 `running`、`pending_login`）。 |
| `POST` | `/api/accounts` | 新增账号。 |
| `PUT` | `/api/accounts/{idx}` | 更新账号（运行中/登录中不可改）。 |
| `DELETE` | `/api/accounts/{idx}` | 删除账号（运行中/登录中不可删）。 |
| `POST` | `/api/accounts/{idx}/start` | 启动该账号。 |
| `POST` | `/api/accounts/{idx}/stop` | 停止该账号。 |
| `POST` | `/api/start-all` | 顺序启动全部。 |
| `GET` | `/api/accounts/{idx}/log?lines=50` | 当日日志尾部。 |
| `GET` / `PUT` | `/api/plugins` | 列出插件元数据 / 保存 `enabled`。 |
| `GET` | `/ws/account/{idx}` | 账号级 WebSocket（扫码与登录事件）。 |

---
