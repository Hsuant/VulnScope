# VulnScope 前端镜像
# 基于自建 vulnscope 镜像，内置宿主机预编译的 dist + 轻量边缘服务。
# 不引入 nginx/node 镜像，满足全栈统一 vulnscope 镜像的部署约束。

FROM vulnscope:latest

# vulnscope 镜像以 app 非 root 运行；安装 httpx 需切回 root
USER root

# 边缘服务依赖（httpx 反向代理）
RUN pip install --no-cache-dir httpx

# 边缘服务代码
COPY edge_server.py /app/edge_server.py

# 宿主机预编译的前端静态产物（vite build 输出）
COPY dist /app/dist

# 归属回 app 用户
RUN chown -R app:app /app/edge_server.py /app/dist
USER app

ENV DIST_DIR=/app/dist \
    BACKEND_URL=http://backend:8000

EXPOSE 80

# uvicorn 托管 Starlette 边缘服务
CMD ["uvicorn", "edge_server:app", "--host", "0.0.0.0", "--port", "80"]
