# VulnScope 后端 Docker 镜像
# 多阶段构建：阶段 1 — 安装依赖，阶段 2 — 运行

# ── 阶段 1: 依赖安装 ────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装系统依赖（编译 bcrypt 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# ── 阶段 2: 运行 ────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# 安装运行时系统依赖（SQLite 支持）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 site-packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建 .env 软链接
RUN if [ ! -f .env ]; then cp .env.example .env; fi

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 启动命令
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]