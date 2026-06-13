# lwapi Relay 登录 — 客户端开发文档

> 适用项目：`wxhook`（Rust）及任意 HTTP 客户端  
> 服务端：lwapi `POST /api/Login/Relay/*`  
> 目标：客户端用**本地出口 IP** POST 微信 MMTLS 网关；服务端负责组包、加解密、会话存储。

---

## 1. 架构概览

```
┌─────────────┐     JSON API      ┌─────────────┐
│   wxhook    │ ◄──────────────► │    lwapi    │
│  (你的客户端) │                   │  组包/解密   │
└──────┬──────┘                   └─────────────┘
       │
       │  HTTP POST（本地 IP，不走 lwapi 代理）
       ▼
┌─────────────┐
│  微信 MMTLS  │
│ short.weixin │
└─────────────┘
```

**客户端只做两件事：**

1. 调 lwapi 拿 `http` 规格（url + headers + body hex）
2. 按规格 POST 微信，把响应 body 转 hex 回传 lwapi

**客户端不做：** protobuf 组包、MMTLS 加解密、CCD 风控数据。

---

## 2. 基础约定

| 项 | 约定 |
|----|------|
| lwapi 基址 | `http://{host}:{port}`，见 `conf/app.toml` 的 `app.port` |
| Content-Type | `application/json` |
| 响应外壳 | `{ "code": 200, "message": "", "data": { ... } }` |
| 二进制传输 | 所有 `body` 字段为**小写 hex**（无 `0x`） |
| POST 微信 | 必须使用**本机网络**；请求里的 `proxy` 仅服务端存会话用 |
| 会话 TTL | `sessionId` 在 Redis 约 **600 秒**，过期需从头 Init |

### 2.1 成功 / 失败

- `code == 200`：HTTP 层成功（业务成败看 `data.result.type`）
- `code == -2020`：需先 Init（`data.needInit == true`）
- 其他负数：见 [错误码](#8-错误码)

---

## 3. 接口列表

| 顺序 | 方法 | 路径 |
|------|------|------|
| 1 | POST | `/api/Login/Relay/Init/Prepare` |
| 2 | POST | `/api/Login/Relay/Init/Complete` |
| 3 | POST | `/api/Login/Relay/Biz/Prepare` |
| 4 | POST | `/api/Login/Relay/Biz/Complete` |

**固定模式（每阶段两步）：**

```
Prepare → [有 http 则 POST 微信] → Complete
```

---

## 4. 数据结构（Rust serde 参考）

### 4.1 通用响应

```rust
#[derive(Deserialize)]
struct ApiResponse<T> {
    code: i32,
    message: String,
    data: Option<T>,
}
```

### 4.2 HTTP 规格（下发给客户端 POST 微信）

```rust
#[derive(Deserialize, Clone)]
struct HttpSpec {
    method: String,              // 固定 "POST"
    url: String,                 // 完整 URL
    headers: HashMap<String, String>,
    body: String,                // hex 编码的请求体
}
```

### 4.3 Proxy（仅 Init 首次创建会话时可选）

```rust
#[derive(Serialize, Default)]
struct ProxyInfo {
    #[serde(rename = "proxyIp")]
    proxy_ip: String,
    #[serde(rename = "proxyUser")]
    proxy_user: String,
    #[serde(rename = "proxyPassword")]
    proxy_password: String,
}
```

---

## 5. Init 握手（必须先成功）

### 5.1 Init/Prepare

**首次（创建 sessionId + 下发握手包）：**

```json
POST /api/Login/Relay/Init/Prepare

{
  "deviceId": "device123",
  "osType": 0,
  "proxy": {
    "proxyIp": "",
    "proxyUser": "",
    "proxyPassword": ""
  }
}
```

**再次（已有 sessionId，检查是否要重握手）：**

```json
{ "sessionId": "rs_a1b2c3d4e5f67890" }
```

**响应 data（需要握手）：**

```json
{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "inited": false,
  "http": {
    "method": "POST",
    "url": "http://short.weixin.qq.com/mmtls/0000a1b2",
    "headers": {
      "Accept": "*/*",
      "Cache-Control": "no-cache",
      "Upgrade": "mmtls",
      "Content-Type": "application/octet-stream",
      "User-Agent": "MicroMessenger Client"
    },
    "body": "16f104..."
  }
}
```

**响应 data（已握手，跳过 POST）：**

```json
{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "inited": true
}
```

| 字段 | 说明 |
|------|------|
| `sessionId` | **必须保存**，后续 Init/Biz 全程携带 |
| `inited` | `true` = 不必 POST；`false` = 按 `http` POST 后调 Complete |
| `http` | 仅 `inited=false` 时有 |

### 5.2 Init/Complete

```json
POST /api/Login/Relay/Init/Complete

{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "statusCode": 200,
  "body": "17f104a1b2c3..."
}
```

**响应 data：**

```json
{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "inited": true
}
```

---

## 6. Biz 业务

### 6.1 flow 枚举

| flow | 说明 | 前置条件 |
|------|------|----------|
| `qr_get` | 获取登录二维码 | Init 成功 |
| `qr_check` | 轮询扫码状态 | 已完成 `qr_get` |
| `sec_manual_auth` | 手动登录（SecManualAuth） | `qr_check` 返回 `confirmed` |
| `sec_auto_auth` | 二次自动登录 | 需传 `wxid`，Init 成功 |

### 6.2 Biz/Prepare

```json
POST /api/Login/Relay/Biz/Prepare

{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "flow": "qr_get"
}
```

`sec_auto_auth` 额外字段：

```json
{
  "sessionId": "rs_...",
  "flow": "sec_auto_auth",
  "wxid": "wxid_xxx"
}
```

**响应 data（正常）：**

```json
{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "flow": "qr_get",
  "http": { ... }
}
```

**响应（需 Init，`code=-2020`）：**

```json
{
  "code": -2020,
  "message": "需要先完成 MMTLS 握手",
  "data": {
    "sessionId": "rs_...",
    "flow": "qr_get",
    "needInit": true
  }
}
```

### 6.3 Biz/Complete

```json
POST /api/Login/Relay/Biz/Complete

{
  "sessionId": "rs_a1b2c3d4e5f67890",
  "flow": "qr_get",
  "statusCode": 200,
  "body": "17f104..."
}
```

**响应 data（成功）：**

```json
{
  "sessionId": "rs_...",
  "flow": "qr_get",
  "result": {
    "type": "qr",
    "qrImage": "data:image/jpg;base64,...",
    "expireSec": 300,
    "deviceId": "..."
  }
}
```

---

## 7. result.type 分支

### `qr` — 取码成功

```json
{
  "type": "qr",
  "qrImage": "data:image/jpg;base64,...",
  "expireSec": 300,
  "deviceId": "..."
}
```

### `qr_status` — 等待扫码

```json
{
  "type": "qr_status",
  "scanState": 0,
  "avatar": "",
  "nickname": ""
}
```

| scanState | 含义 |
|-----------|------|
| 0 | 未扫码 |
| 1 | 已扫，未点确认 |
| 2 | 已确认（服务端可能直接返回 `confirmed`，见下） |

**处理：** `scanState` 为 0 或 1 → `sleep(1500ms)` → 再 `Biz/Prepare(qr_check)`。

### `confirmed` — 用户已在手机确认

```json
{
  "type": "confirmed",
  "scanState": 2,
  "message": "用户已确认，请调用 flow=sec_manual_auth"
}
```

**处理：** 调 `Biz/Prepare(flow=sec_manual_auth)` → POST → Complete。

### `login_ok` — 登录成功

```json
{
  "type": "login_ok",
  "wxid": "wxid_xxx",
  "nickname": "昵称",
  "avatar": "https://..."
}
```

**处理：** 保存 `wxid`；后续调 lwapi 其它接口用 Header `X-Wxid: {wxid}`。

### `error` — 微信业务错误

```json
{
  "type": "error",
  "ret": -301,
  "msg": "..."
}
```

---

## 8. 错误码

| code | 含义 | 客户端处理 |
|------|------|------------|
| 200 | 成功 | 正常解析 `data` |
| -1001 | 缺少参数 | 检查请求字段 |
| -1002 | 用户数据无效 | session/wxid 无效 |
| -1019 | 登录缓存失效 | session 过期，重新 Init |
| -2020 | 需要 Init | 见 `needInit` / `needInitReason` |
| -2004 | MMTLS 失败 | 检查 hex body 是否正确 |
| -2001 | 请求失败 | 解密/网络异常 |

### needInit 场景

| needInitReason | 含义 | 处理 |
|----------------|------|------|
| `mmtls_expired` | 31 字节短包 / 会话失效 | Init/Prepare → Complete → 重试原 Biz |
| `host_redirect` | -301 换机房 | Init → 重试 `sec_manual_auth` |

---

## 9. 完整扫码登录时序

```
① Init/Prepare { deviceId, osType }
   ← sessionId + http (inited=false)

② POST 微信 (http) → Init/Complete { sessionId, body }
   ← inited=true

③ Biz/Prepare { sessionId, flow:"qr_get" }
   ← http

④ POST 微信 → Biz/Complete { flow:"qr_get", body }
   ← result.type=qr  （展示二维码）

⑤ loop 每 1.5s:
   Biz/Prepare { sessionId, flow:"qr_check" }
   POST → Biz/Complete
   ├─ type=qr_status, scanState in (0,1) → continue loop
   └─ type=confirmed → break loop

⑥ Biz/Prepare { sessionId, flow:"sec_manual_auth" }
   POST → Biz/Complete
   ← type=login_ok  （保存 wxid）
```

### 二次登录（sec_auto_auth）

```
Init/Prepare { deviceId } → Complete
Biz/Prepare { sessionId, flow:"sec_auto_auth", wxid }
POST → Biz/Complete
← type=login_ok
```

---

## 10. Rust 实现要点（wxhook）

### 10.1 依赖建议

```toml
[dependencies]
reqwest = { version = "0.12", features = ["json"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
hex = "0.4"
tokio = { version = "1", features = ["full"] }
anyhow = "1"
```

### 10.2 POST 微信（核心函数）

```rust
use anyhow::{Context, Result};
use reqwest::Client;

/// 按 lwapi 下发的 HttpSpec 向微信 POST，返回 raw body。
pub async fn post_wechat(spec: &HttpSpec) -> Result<Vec<u8>> {
    let body = hex::decode(spec.body.trim())
        .context("decode http.body hex")?;

    let client = Client::builder()
        .no_proxy() // 关键：必须本地 IP，不走系统代理
        .build()?;

    let mut req = client.post(&spec.url).body(body);
    for (k, v) in &spec.headers {
        req = req.header(k, v);
    }

    let resp = req.send().await.context("post wechat")?;
    let status = resp.status().as_u16();
    let bytes = resp.bytes().await.context("read wechat body")?;

    if status != 200 {
        anyhow::bail!("wechat http status {}", status);
    }
    Ok(bytes.to_vec())
}

/// raw body → 小写 hex（回传 lwapi）
pub fn to_hex(data: &[u8]) -> String {
    hex::encode(data)
}
```

### 10.3 Prepare → POST → Complete 模板

```rust
async fn relay_round<T, R>(
    lwapi: &str,
    prepare_path: &str,
    complete_path: &str,
    prepare_body: &impl serde::Serialize,
) -> Result<R>
where
    R: serde::de::DeserializeOwned,
{
    // 1. Prepare
    let prep: ApiResponse<R> = reqwest::Client::new()
        .post(format!("{}{}", lwapi, prepare_path))
        .json(prepare_body)
        .send().await?
        .json().await?;

    if prep.code == -2020 {
        // 调 ensure_init 后重试（自行实现）
        anyhow::bail!("need init");
    }
    if prep.code != 200 {
        anyhow::bail!("prepare failed: {} {}", prep.code, prep.message);
    }

    // 2. 若有 http 则 POST 微信
    // 注：Init/Biz 的 data 结构不同，实际需按字段解析 http
    // ...

    Ok(prep.data.unwrap())
}
```

### 10.4 本地状态（建议）

```rust
struct RelaySession {
    session_id: String,
    wxid: Option<String>,
}

impl RelaySession {
    async fn ensure_init(&mut self, lwapi: &str, device_id: &str) -> Result<()> {
        // Init/Prepare → 若 !inited 则 post_wechat → Init/Complete
        Ok(())
    }

    async fn biz(&self, lwapi: &str, flow: &str, wxid: Option<&str>) -> Result<serde_json::Value> {
        // Biz/Prepare → post_wechat → Biz/Complete → 返回 result
        Ok(serde_json::Value::Null)
    }
}
```

### 10.5 注意事项

1. **Prepare 与 Complete 必须配对**，且 `flow` 一致；不可跳过 Complete。
2. **同一 sessionId 不要并发** Prepare/Complete。
3. **hex 必须小写**（`hex::encode` 默认小写，符合要求）。
4. **POST 微信禁用代理**（`no_proxy()`），否则达不到「本地 IP 登录」目的。
5. `qrImage` 可直接给 UI 显示（已是 `data:image/jpg;base64,...`）。
6. session 过期（约 10 分钟无操作）需从 Init 重新开始。

---

## 11. curl 调试示例

```bash
LWAPI=http://127.0.0.1:8080

# 1. Init Prepare
curl -s "$LWAPI/api/Login/Relay/Init/Prepare" \
  -H 'Content-Type: application/json' \
  -d '{"deviceId":"test001","osType":0}' | jq .

# 2. Init Complete（body 替换为微信返回 hex）
curl -s "$LWAPI/api/Login/Relay/Init/Complete" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"rs_xxx","body":"..."}' | jq .

# 3. Biz Prepare 取码
curl -s "$LWAPI/api/Login/Relay/Biz/Prepare" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"rs_xxx","flow":"qr_get"}' | jq .
```

---

## 12. 与旧接口关系

| 旧接口（服务端直连微信） | Relay 等价 |
|--------------------------|------------|
| POST /api/Login/QRGet | Init + Biz(qr_get) |
| POST /api/Login/QRCheck | Biz(qr_check) + Biz(sec_manual_auth) |
| POST /api/Login/SecAutoAuth | Init + Biz(sec_auto_auth) |

旧接口**保持不变**；Relay 为新增路径，互不影响。

---

## 13. 源码索引（维护用）

| 路径 | 说明 |
|------|------|
| `internal/service/relay/types.go` | 请求/响应/result 定义 |
| `internal/service/relay/init.go` | Init 逻辑 |
| `internal/service/relay/biz_prepare.go` | Biz Prepare |
| `internal/service/relay/biz_complete.go` | Biz Complete |
| `internal/mmtls/relay_*.go` | MMTLS 组包/解包 |
| `internal/api/controllers/wx/relay.go` | HTTP 入口 |

Swagger：`GET /docs` 搜索 `Relay`。
