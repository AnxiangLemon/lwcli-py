# lwcli-py

写个python客户端好了

```t
lwapi_sdk/
  lwapi/
    __init__.py              # SDK 初始化
    config.py                # 配置管理（支持多账号和动态配置）
    transport.py             # HTTP 传输层（请求封装）
    exceptions.py            # 异常管理（错误处理）
    models/                  # 数据模型（根据 swagger 定义）
      __init__.py
      login.py               # 登录相关数据模型
      msg.py                 # 消息相关数据模型
      ...
    apis/                    # API 客户端（按模块拆分）
      __init__.py
      login.py               # 登录接口
      msg.py                 # 消息接口
      ...
    client.py                # SDK 客户端入口（聚合所有模块）
  tests/                     # 单元测试
    test_login.py            # 登录功能测试
    test_msg.py              # 消息功能测试
    ...
  swagger/                   # Swagger 文件存放位置（json 或 yaml 格式）
  pyproject.toml / setup.cfg  # 包配置文件
  README.md                  # 使用说明文档
```