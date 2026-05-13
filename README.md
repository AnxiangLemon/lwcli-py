# lwapi-py

基于 **LwApi（微信 4.0 协议服务）** 的 Python 工程：内含 **`lwapi/` SDK** 与 **`src/` Web 运维台**——管理多账号、扫码登录、消息插件与日志查看。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| `lwapi/` | 异步 HTTP 客户端：登录、消息同步与发送等 API 封装。 |
| `src/web/` | aiohttp 运维台：账号 CRUD、启停机器人、插件开关、当日日志尾、账号级 WebSocket 推送扫码状态。 |
| `src/services/bot_service.py` | 每个账号独立协程：登录 → 心跳 → 消息轮询，任务键为「备注 + device_id」。 |
| `src/plugins/` | 消息处理插件：由 `config/plugins.json` 控制启用顺序，可在网页勾选保存。 |

---

## 环境要求

- Python **≥ 3.9**
- 已部署可访问的 **LwApi HTTP 服务**（默认假设为 `http://localhost:8081`）

安装依赖：

```bash
pip install -r requirements.txt
```

---

## 快速启动

```bash
python run.py
```

默认监听 **`0.0.0.0:8090`**。浏览器打开终端里打印的地址（本机一般为 `http://127.0.0.1:8090`）。

### 环境变量

| 变量 | 默认值 | 含义 |
|------|--------|------|
| `LWAPI_BASE_URL` | `http://localhost:8081` | LwApi 服务根地址（供 `BotService` / SDK 使用）。 |
| `LWAPI_WEB_HOST` | `0.0.0.0` | 运维台监听地址。 |
| `LWAPI_WEB_PORT` | `8090` | 运维台端口。 |

可在项目根目录放置 **`.env`**（`python-dotenv` 已在 `BotService` 中加载）。

---

## 配置文件

### `config/accounts.json`

账号列表，每项常见字段：

- `device_id`：设备标识（**允许在不同备注下重复**，运行期用「备注+device_id」区分任务）。
- `wxid`：登录成功后回写；有有效值时可走缓存二次登录，减少扫码。
- `remark`：备注，用于日志文件名与槽位键；建议与业务含义一致。
- `proxy`：可选，结构与 LwApi `ProxyInfo` 一致。

### `config/plugins.json`

控制消息插件启用与顺序，例如：

```json
{
  "enabled": ["demo_replies", "debug_types"]
}
```

保存后**无需重启进程**，下一轮消息同步会按新配置加载（内部按文件 mtime 缓存）。

---

## 仓库结构（节选）

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

## HTTP API（运维台）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/accounts` | 账号列表（含 `running` / `pending_login` 等派生字段）。 |
| `POST` | `/api/accounts` | 新增账号。 |
| `PUT` | `/api/accounts/{idx}` | 更新指定下标账号（运行中不可改）。 |
| `DELETE` | `/api/accounts/{idx}` | 删除账号。 |
| `POST` | `/api/accounts/{idx}/start` | 启动该账号机器人（宜先打开页面 WS）。 |
| `POST` | `/api/accounts/{idx}/stop` | 停止。 |
| `POST` | `/api/start-all` | 顺序启动全部账号。 |
| `GET` | `/api/accounts/{idx}/log?lines=50` | 当日该备注日志文件末尾。 |
| `GET` / `PUT` | `/api/plugins` | 列出插件元数据 / 保存 `enabled` 列表。 |
| `GET` | `/ws/account/{idx}` | 该账号登录与扫码事件推送。 |

---

## 新增消息插件

1. 在 `src/plugins/` 下新建模块，定义 `PLUGIN_ID`、`PLUGIN_TITLE`、`PLUGIN_DESCRIPTION` 与 `async def handle(client, resp)`。
2. 在 `src/plugins/registry.py` 的 `_ALL` 中追加对应的 `PluginSpec`。
3. 打开运维台 **插件管理** 页勾选并保存。

内置参考：`builtin_demo_replies.py`、`builtin_debug_types.py`。

---

## 独立脚本读取账号

若编写自己的 CLI（非 Web），可调用 `src.account_loader.load_accounts()`：当 `config/accounts.json` 不存在时会生成示例并 **`SystemExit(1)`**。

Web 与长期服务应使用 **`load_accounts_safe()`**，避免因配置缺失导致进程直接退出。

---

## 说明

- **扫码登录**依赖运维台 WebSocket 推送二维码与状态；已移除纯终端 ASCII 扫码路径。
- 业务消息逻辑请放在 **插件** 中，避免再向单一巨型 `message_handler` 堆叠代码。
