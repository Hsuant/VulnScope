#!/bin/bash
# VulnScope 后端启动脚本（Git Bash 环境）
# 用法: ./start.sh [--no-migrate] [--port 8000]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
VENV_UVICORN="$SCRIPT_DIR/.venv/Scripts/uvicorn.exe"
PORT=${2:-8000}

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[错误] 虚拟环境未找到，请先执行: python -m venv .venv && ./.venv/Scripts/pip install -e ."
    exit 1
fi

# 执行数据库迁移
if [ "$1" != "--no-migrate" ]; then
    echo "[启动] 执行数据库迁移..."
    "$SCRIPT_DIR/.venv/Scripts/alembic.exe" upgrade head
    echo "[启动] 迁移完成"
fi

# 启动开发服务器
echo "[启动] VulnScope API 服务: http://127.0.0.1:$PORT"
echo "[启动] Swagger 文档: http://127.0.0.1:$PORT/docs"
exec "$VENV_UVICORN" app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload