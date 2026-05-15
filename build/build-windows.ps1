# 在 Windows 上打包 lwapi-console（生成 dist\ 与 zip）
# 用法（PowerShell，项目根目录）:
#   .\build\build-windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Ensure-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        throw "未找到 python，请先安装 Python 3.9+ 并加入 PATH"
    }
    & python -c "import sys; assert sys.version_info >= (3, 9), '需要 Python 3.9+'"
}

Ensure-Python

$venv = Join-Path $Root "venv"
if (-not (Test-Path $venv)) {
    Write-Host "创建虚拟环境 venv ..."
    python -m venv $venv
}

$activate = Join-Path $venv "Scripts\Activate.ps1"
. $activate

Write-Host "安装依赖 ..."
python -m pip install -U pip
pip install -r requirements.txt -r build/requirements-build.txt

Write-Host "运行 PyInstaller ..."
pyinstaller build/lwapi-console.spec --noconfirm --clean

Write-Host "组装发布目录与 zip ..."
python build/package_dist.py

Write-Host ""
Write-Host "完成。请将 dist\ 下的 zip 发给对方，或整个 dist\lwapi-console 文件夹（含旁路 config/plugins）。"
Write-Host "macOS / Linux 包请在对应系统上分别执行 build-macos.sh / build-linux.sh。"
