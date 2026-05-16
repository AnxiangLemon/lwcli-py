在此目录放置自定义插件：文件名须为 lwplugin_*.py（仅扫描本层）。

示例：lwplugin_demo_helper.py（群聊命令）、lwplugin_my_hello.py（全生命周期 demo）。
详细说明见解压包外或仓库根目录 README.md。

在运维台「插件管理」勾选并保存后生效；改代码需重启程序。
若打包时项目根 plugins/ 存在，会自动复制到本目录。
