#!/usr/bin/env bash
# 在 Linux 上打包 lwapi-console
# 用法（项目根目录）:
#   chmod +x build/build-linux.sh
#   ./build/build-linux.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误: 未找到 python3，请安装 Python 3.9+" >&2
  exit 1
fi

python3 -c 'import sys; assert sys.version_info >= (3, 9), "需要 Python 3.9+"'

VENV="$ROOT/venv"
if [[ ! -d "$VENV" ]]; then
  echo "创建虚拟环境 venv ..."
  python3 -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"

echo "安装依赖 ..."
python -m pip install -U pip
pip install -r requirements.txt -r build/requirements-build.txt

echo "运行 PyInstaller ..."
pyinstaller build/lwapi-console.spec --noconfirm --clean

echo "组装发布目录与 zip ..."
python build/package_dist.py

echo ""
echo "完成: dist/lwapi-console-*-linux-*.zip"
echo "Windows / macOS 包请在对应系统上执行 build-windows.ps1 / build-macos.sh。"
