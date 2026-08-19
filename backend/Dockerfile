# VulnScope 后端 Docker 镜像
# 单阶段构建：基于 python:3.10-slim 安装运行时依赖并打包应用。
# 说明：bcrypt / pydantic-core 等均提供 manylinux 预编译 wheel，无需编译工具链；
#       python:3.10-slim 自带 libsqlite3，满足 SQLite 运行需求，故无需 apt。

FROM python:3.10-slim

WORKDIR /app

# 升级 pip 以更好解析 wheel
RUN pip install --no-cache-dir --upgrade pip

# 先拷依赖清单利用层缓存（仅 pyproject，应用代码后拷）
COPY pyproject.toml ./
COPY app ./app

# 安装运行时依赖（不含 dev 工具，降低体积与攻击面）
RUN pip install --no-cache-dir .

# 非 root 运行 + 数据目录（SQLite 持久卷挂载点）
RUN groupadd -r app && useradd -r -g app -d /app -s /usr/sbin/nologin app && \
    mkdir -p /app/data && \
    chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 启动：先幂等建表，再启动 API（lifespan 也会建表 + 种子角色/管理员）
CMD ["sh", "-c", "python -m app.db.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
