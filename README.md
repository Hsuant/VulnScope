<div align="center">
  <h1>VulnScope</h1>
  <p><strong>POC（Proof of Concept）漏洞验证脚本管理系统</strong></p>
  <p>以 POC 为核心资产，提供管理、存储、检索、导入导出、标签分类、CVE 关联能力</p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.4%2B-4FC08D?logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-333333?logo=sqlalchemy" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 特性

- **POC 全生命周期管理** — 创建、编辑、版本回溯、克隆、状态流转
- **多格式支持** — Nuclei YAML、Pocsuite3、JSON、原始脚本，格式无关架构
- **批量导入导出** — 自动格式嗅探、内容去重、批量多文件支持
- **标签分类系统** — 命名空间标签 + 树形分类，灵活组织 POC 资产
- **CVE 漏洞库** — CVE 详情、编辑、新建、批量导入（JSON/JSONL/YAML/Markdown），POC 导入自动同步 CVE 元数据，漏洞与 POC 双向检索
- **统计看板** — 严重级别/状态/来源分布、创建趋势、热门标签、高产作者
- **RBAC 权限** — 三角色（查看者/编辑者/管理员），颗粒度操作控制
- **审计日志** — 所有写操作全量留痕，操作前后摘要 + IP 记录
- **插件框架** — Parser/Source/Verifier/Exporter 四插槽，即插即用
- **事件驱动架构** — 领域事件异步派发，模块间解耦联动

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- 可选：MySQL 8.0（生产环境）

### 后端

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv

# 安装依赖（含开发依赖）
.venv/Scripts/pip install -e ".[dev]"

# 复制环境变量配置
cp .env.example .env

# 执行数据库迁移
.venv/Scripts/alembic upgrade head

# 启动开发服务器（自动 reload）
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### Docker 部署（可选，进行中）

仓库自带 `docker-compose.yml`，用于本地一键拉起前后端容器：

```bash
# 在项目根目录
docker compose up -d
```

> 该编排当前为开发用途（前端运行 `npm run dev` 热更新开发服务器，未做生产构建与镜像发布），生产级容器化（多阶段构建、Nginx 静态托管、健康检查与数据卷持久化）随 M6 推进中。

### 访问地址

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端管理后台 |
| http://localhost:8000/docs | Swagger UI 交互文档 |
| http://localhost:8000/api/v1/health | 健康检查 |

### 默认管理员账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | admin |

## 项目结构

```
VulnScope/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 应用入口 + 生命周期
│   │   ├── core/             # 配置 / 异常 / 安全 / 事件 / 缓存
│   │   ├── db/               # 会话管理 / 基类
│   │   ├── models/           # ORM 模型
│   │   ├── schemas/          # Pydantic 请求/响应
│   │   ├── api/v1/           # REST 路由
│   │   ├── services/         # 业务服务层
│   │   └── plugins/          # 插件框架
│   ├── tests/                # pytest 测试
│   ├── alembic/              # 数据库迁移
│   ├── Dockerfile            # 后端镜像
│   ├── start.bat / start.sh  # 启动脚本
│   └── pyproject.toml        # 依赖 + 工具配置
├── frontend/                 # Vue 3 前端
│   └── src/
│       ├── views/            # 页面
│       ├── components/       # 组件
│       ├── composables/      # 组合式函数
│       ├── api/              # API 客户端
│       ├── stores/           # 状态管理
│       ├── router/           # 路由
│       └── styles/           # 全局样式
├── templates/                # 导入/参考模板
│   ├── cve/                  # CVE 导入模板（json/jsonl/yaml/markdown）
│   └── poc/                  # POC 模板（nuclei-template.yaml）
├── docs/                     # 开发文档 + 使用说明书
└── docker-compose.yml        # Docker 一键部署（M6 进行中）
```

## API 概览

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/v1/auth/login` | 登录 | 无需 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 无需 |
| GET | `/api/v1/auth/me` | 当前用户 | 需认证 |
| PUT | `/api/v1/auth/profile` | 更新个人资料 | 需认证 |
| GET/POST | `/api/v1/pocs` | POC 列表/创建 | 需认证 |
| GET | `/api/v1/pocs/search` | 关键字搜索 | 需认证 |
| GET/PUT/DELETE | `/api/v1/pocs/{id}` | POC 详情/更新/删除 | 需认证 |
| PATCH | `/api/v1/pocs/{id}/status` | 状态流转 | editor/admin |
| POST | `/api/v1/pocs/{id}/clone` | 克隆 POC | editor/admin |
| GET | `/api/v1/pocs/{id}/versions` | 版本历史 | 需认证 |
| GET | `/api/v1/pocs/{id}/source-records` | 来源溯源 | 需认证 |
| POST | `/api/v1/pocs/verify-url` | 验证 URL | 需认证 |
| POST | `/api/v1/import` | 导入 POC | editor/admin |
| GET | `/api/v1/export` | 导出 POC | 需认证 |
| GET/POST/PUT/DELETE | `/api/v1/tags` | 标签管理 | 需认证 |
| GET | `/api/v1/tags/namespaces` | 标签命名空间 | 需认证 |
| GET | `/api/v1/vulns` | CVE 列表（分页/筛选/搜索） | 需认证 |
| GET/POST | `/api/v1/vulns` / `/api/v1/vulns/{id}` | CVE 查询 / 创建 / 详情 / 更新 | 需认证（写操作 editor/admin） |
| GET | `/api/v1/vulns/by-cve/{cve_id}` | 按 CVE 编号查询 | 需认证 |
| POST | `/api/v1/vulns/import` | 批量导入 CVE（json/jsonl/yaml/markdown） | editor/admin |
| DELETE | `/api/v1/vulns/{id}` | 删除单个/批量 CVE | editor/admin |
| GET | `/api/v1/dashboard/*` | 统计看板 | 需认证 |
| GET/POST/PUT/DELETE | `/api/v1/users` | 用户管理 | admin |
| GET | `/api/v1/users/roles` | 角色列表 | admin |
| GET | `/api/v1/plugins` | 插件列表 | 需认证 |
| GET | `/api/v1/plugins/{slot}` | 按槽位查插件 | 需认证 |
| GET | `/api/v1/audit-logs` | 审计日志 | admin |

## 配置

通过环境变量或 `.env` 文件配置，前缀 `VULNSCOPE_`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VULNSCOPE_APP_ENV` | `dev` | 运行环境（dev / test / prod） |
| `VULNSCOPE_DB_BACKEND` | `sqlite` | 数据库后端（sqlite / mysql） |
| `VULNSCOPE_DATABASE_URL` | 按后端生成 | 显式数据库连接 URL（优先级最高） |
| `VULNSCOPE_CACHE_BACKEND` | `inproc` | 缓存后端（inproc / redis，v2 引入） |
| `VULNSCOPE_SECRET_KEY` | 开发密钥 | JWT 签名密钥，生产环境务必更换 |
| `VULNSCOPE_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | access token 过期时间 |
| `VULNSCOPE_REFRESH_TOKEN_EXPIRE_DAYS` | 7 | refresh token 过期时间 |
| `VULNSCOPE_SEED_ADMIN_USERNAME` | `admin` | 种子管理员用户名 |
| `VULNSCOPE_SEED_ADMIN_PASSWORD` | `admin123` | 种子管理员密码 |

> 完整的可配置项以 `backend/app/core/config.py` 为准，所有变量均带 `VULNSCOPE_` 前缀。

## 运行测试

```bash
cd backend
.venv/Scripts/pytest -v                    # 全部测试
.venv/Scripts/pytest --cov=app tests/       # 带覆盖率
```

## 技术栈

| 层次 | 组件 | 用途 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | 异步路由、自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 + Alembic | 声明式模型、版本化迁移 |
| 数据校验 | Pydantic v2 | 请求/响应模型、配置校验 |
| 认证 | bcrypt + PyJWT | 密码哈希、双 token 机制 |
| 缓存 | cachetools | 进程内 TTL 缓存 |
| 前端 | Vue 3 + TypeScript | Composition API |
| UI | Element Plus | 组件库 |
| 构建 | Vite | 前端构建工具 |

## 详细使用说明

📖 完整的使用指南请查阅 [使用说明书](docs/usage-guide.md)，涵盖：

- **新建 POC** — 基本信息填写、关联信息配置、表单构建模式（HTTP/TCP/DNS 协议）、匹配规则配置、源码模式编辑
- **标签管理** — 命名空间体系、新建/编辑/删除标签、最佳实践
- **导入导出** — 批量文件上传、粘贴文本、格式自动识别
- **CVE 漏洞库** — 列表/详情/编辑/新建、批量导入（JSON/JSONL/YAML/Markdown）、POC 导入联动同步
- **常见问题** — 名称冲突、格式限制、版本回滚、内容去重

## 开发里程碑

- ✅ **M1 骨架** — 项目脚手架、配置、鉴权、异常、插件接口
- ✅ **M2 核心存储** — POC CRUD、标签分类、CVE 关联、搜索
- ✅ **M3 插件框架** — 注册表、事件总线、Parser/Source 槽
- ✅ **M4 导入导出** — 导入向导、格式嗅探、去重、导出
- ✅ **M5 前端** — 完整管理后台
- ⏳ **M6 部署** — Docker Compose 一键部署（尚未完成）
- ⏳ **M7 收尾** — 压测、性能优化
- ⏳ **v2 验证模块** — POC 远程验证执行
- ⏳ **v2 AI 生成** — 基于漏洞描述的 POC 自动生成
- ⏳ **v2 爬取** — 自动化 POC 爬取

## License

MIT