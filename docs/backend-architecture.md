# VulnScope 后端技术架构文档

> 版本：v1.0 | 日期：2026-08-13 | 对应后端：`backend/` v0.1.0

---

## 目录

1. [技术栈](#1-技术栈)
2. [项目结构](#2-项目结构)
3. [架构分层](#3-架构分层)
4. [核心模块](#4-核心模块)
5. [数据模型](#5-数据模型)
6. [API 接口文档](#6-api-接口文档)
7. [配置说明](#7-配置说明)
8. [运行指引](#8-运行指引)
9. [开发指南](#9-开发指南)
10. [质量保障](#10-质量保障)

---

## 1. 技术栈

| 层次 | 组件 | 版本 | 用途 |
|------|------|------|------|
| 语言 | Python | 3.10+ | 宿主语言，POC 生态以 Python 为主 |
| Web 框架 | FastAPI | 0.110+ | 异步路由、Pydantic 校验、自动 OpenAPI 文档 |
| ORM | SQLAlchemy | 2.0+ | 声明式模型、异步查询、方言无关 |
| 数据库迁移 | Alembic | 1.13+ | 版本化数据库 schema 管理 |
| 数据校验 | Pydantic v2 | 2.6+ | 请求/响应模型、配置校验、自定义验证器 |
| 配置管理 | pydantic-settings | 2.2+ | 环境变量 + .env 文件分层配置 |
| 密码哈希 | bcrypt | 4.1+ | 含随机盐的密码哈希 |
| JWT | PyJWT | 2.8+ | HS256 签名 token 签发与验证 |
| 缓存 | cachetools | 5.3+ | 进程内 TTL 缓存（v1 默认） |
| 测试 | pytest + httpx | 8.0+ / 0.27+ | 单元测试 + 集成测试 + TestClient |
| 代码规范 | Ruff + Black + mypy | — | Lint / 格式化 / 类型检查 |

### 1.1 选型依据

- **FastAPI 而非 Flask/Django**：原生异步支持、Pydantic 深度集成、自动生成 OpenAPI 文档，减少接口文档维护成本。
- **SQLAlchemy 2.0 而非 Tortoise-ORM**：对 SQLite 和 MySQL 的全面支持，Alembic 迁移生态成熟，声明式模型与 Pydantic 配合良好。
- **PyJWT 而非 python-jose**：python-jose 已停止维护，PyJWT 是社区活跃的替代品。
- **bcrypt 而非 passlib**：passlib 对 bcrypt 新版本的兼容性存在问题，直接使用 bcrypt 更可靠。
- **cachetools 而非 Redis（v1）**：v1 单实例部署场景下进程内缓存足够，Redis 留待 v2 验证模块作为任务队列引入。

---

## 2. 项目结构

```
backend/
├── pyproject.toml              # 项目元数据、依赖声明、工具配置
├── alembic.ini                 # Alembic 配置文件
├── .env                        # 本地环境变量（不提交到版本库）
├── .env.example                # 环境变量模板
├── .gitignore
├── start.sh / start.bat        # 启动脚本
├── vulnscope.db                # 开发环境 SQLite 数据库文件
├── alembic/                    # 数据库迁移目录
│   ├── env.py                  # 迁移环境配置（复用项目数据库 URL）
│   ├── script.py.mako          # 迁移模板文件
│   └── versions/               # 版本化迁移文件
│       └── 1d9d32c2d30f_initial.py
├── tests/                      # 测试套件
│   ├── conftest.py             # 测试夹具：临时数据库、种子数据、客户端
│   ├── test_health.py          # 健康检查接口测试
│   └── test_auth.py            # 认证流程测试（10 个用例）
└── app/                        # 应用代码
    ├── __init__.py              # 版本声明
    ├── main.py                  # FastAPI 应用入口 + 生命周期管理
    ├── core/                    # 核心基础设施
    │   ├── __init__.py
    │   ├── config.py            # 分层配置（pydantic-settings）
    │   ├── exceptions.py        # 统一异常体系（15 个错误码）
    │   ├── security.py          # 密码哈希 + JWT 签发校验 + RBAC
    │   ├── events.py            # 事件总线（异步 asyncio 派发）
    │   └── cache.py             # 缓存抽象层（inproc / redis 可切换）
    ├── db/                      # 数据库层
    │   ├── __init__.py
    │   ├── base.py              # 声明式基类 + 公共 Mixin
    │   └── session.py           # 引擎 + 会话工厂 + FastAPI 依赖注入
    ├── models/                  # SQLAlchemy ORM 模型
    │   ├── __init__.py          # 模型聚合导出（Alembic autogenerate 依赖）
    │   └── user.py              # User / Role 模型
    ├── schemas/                 # Pydantic 请求/响应模型
    │   ├── __init__.py
    │   ├── common.py            # 统一响应包装（ApiResponse）
    │   └── auth.py              # 认证相关 schema
    ├── api/                     # API 路由层
    │   ├── __init__.py
    │   ├── deps.py              # 依赖注入（DbSession / CurrentUser / AdminUser）
    │   └── v1/                  # v1 API 版本
    │       ├── __init__.py
    │       ├── health.py        # 健康检查
    │       └── auth.py          # 认证路由
    ├── services/                # 业务服务层
    │   ├── __init__.py
    │   └── auth_service.py      # 认证业务 + 种子数据初始化
    └── plugins/                 # 插件框架（M3 完整实现）
        ├── __init__.py
        ├── base.py              # NormalizedPoc IR + 4 个接口契约
        ├── registry.py          # 插件注册表
        ├── parser/              # 解析器插件槽
        └── source/              # 来源插件槽
```

---

## 3. 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│  API 层 (app/api/v1/)                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 健康检查       │  │ 认证路由      │  │ POC 路由（M2）   │  │
│  │ /health       │  │ /auth/*      │  │ /pocs/*         │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────┘  │
│                           │ 依赖注入                          │
│                    ┌──────▼───────┐                          │
│                    │  deps.py      │                          │
│                    │ DbSession     │                          │
│                    │ CurrentUser   │                          │
│                    │ require_roles │                          │
│                    └──────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│  服务层 (app/services/)                                      │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ 认证服务          │  │ POC 服务（M2）    │                 │
│  │ 登录/刷新/种子    │  │ CRUD/搜索/导入   │                 │
│  └──────────────────┘  └──────────────────┘                 │
├─────────────────────────────────────────────────────────────┤
│  核心基础设施 (app/core/)                                    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐        │
│  │ 配置管理   │ │ 异常体系   │ │ 安全模块 │ │ 事件总线   │        │
│  │ config.py│ │exceptions│ │security│ │ events.py │        │
│  └──────────┘ └──────────┘ └────────┘ └───────────┘        │
│  ┌──────────┐ ┌────────────────────────────────┐            │
│  │ 缓存抽象  │ │ 插件框架（M3）                    │            │
│  │ cache.py │ │ plugins/base.py + registry     │            │
│  └──────────┘ └────────────────────────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  数据层 (app/db/ + app/models/)                              │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────┐         │
│  │ 会话管理   │ │ ORM 模型      │ │ Alembic 迁移      │         │
│  │ session.py│ │ models/      │ │ alembic/         │         │
│  └──────────┘ └──────────────┘ └──────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 分层职责

| 层 | 职责 | 约束 |
|----|------|------|
| API 层 | 路由分发、参数校验、统一响应包装 | 不承载业务逻辑；通过依赖注入获取服务对象 |
| 服务层 | 业务用例编排、事务边界、领域事件发布 | 依赖插件接口而非具体实现；可跨模型组合 |
| 核心层 | 跨模块公共能力（配置、安全、异常、事件、缓存） | 下层不反向依赖上层 |
| 数据层 | ORM 映射、数据库迁移、会话管理 | 全部经 SQLAlchemy，禁止裸 SQL 拼接 |

### 3.2 请求生命周期

```
客户端请求
    │
    ▼
FastAPI 路由匹配 → 依赖注入（DB 会话、当前用户、角色守卫）
    │
    ▼
Pydantic 请求参数校验（422 返回）
    │
    ▼
服务层业务逻辑（事务边界）
    │
    ▼
ORM 数据操作（SQLAlchemy 2.0）
    │
    ▼
统一响应包装 {code, message, data, request_id}
    │
    ▼
客户端响应
```

---

## 4. 核心模块

### 4.1 配置管理 (`app/core/config.py`)

基于 `pydantic-settings` 实现分层配置，优先级：环境变量 > `.env` 文件 > 默认值。

所有配置项以 `VULNSCOPE_` 为前缀，自动读取。核心配置项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VULNSCOPE_DB_BACKEND` | `sqlite` | 数据库后端，可选 `sqlite` / `mysql` |
| `VULNSCOPE_DATABASE_URL` | 自动拼接 | 显式数据库连接 URL，优先级最高 |
| `VULNSCOPE_SECRET_KEY` | 开发密钥 | JWT 签名密钥，生产环境务必更换 |
| `VULNSCOPE_CACHE_BACKEND` | `inproc` | 缓存后端，可选 `inproc` / `redis`（v2） |
| `VULNSCOPE_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | access token 过期时间（分钟） |
| `VULNSCOPE_REFRESH_TOKEN_EXPIRE_DAYS` | 7 | refresh token 过期时间（天） |

### 4.2 统一异常体系 (`app/core/exceptions.py`)

所有 API 错误通过 `AppError` 异常抛出，全局处理器统一渲染为 `{code, message, data, request_id}`。

内置错误码（15 个）：

| 错误码 | HTTP 状态 | 场景 |
|--------|----------|------|
| `AUTH_INVALID_CREDENTIALS` | 401 | 用户名或密码错误 |
| `AUTH_TOKEN_EXPIRED` | 401 | token 已过期 |
| `AUTH_TOKEN_INVALID` | 401 | token 无效或类型不符 |
| `FORBIDDEN` | 403 | 角色权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFLICT` | 409 | 数据冲突（如 POC 重复） |
| `POC_DUPLICATE` | 409 | POC 内容 hash 重复 |
| `POC_VALIDATION_ERROR` | 422 | POC 模板校验失败 |
| `PLUGIN_NOT_AVAILABLE` | 503 | 插件未启用 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

### 4.3 安全模块 (`app/core/security.py`)

**密码存储**：bcrypt 哈希，含随机盐，12 轮迭代。

```python
hash_password("admin123")  # → "$2b$12$..."（含盐的 bcrypt 字符串）
verify_password("admin123", hashed)  # → True/False
```

**JWT 双 token 机制**：

| Token 类型 | 过期时间 | 用途 |
|-----------|---------|------|
| access token | 30 分钟（可配置） | API 请求鉴权，携带 `Authorization: Bearer <token>` |
| refresh token | 7 天（可配置） | 换取新的 access token，无需重新登录 |

**RBAC 三角色**：

| 角色 | 标识 | 权限 |
|------|------|------|
| 查看者 | `viewer` | 只读：查看 POC、标签、插件状态 |
| 编辑者 | `editor` | 增删改：POC 增删改、导入导出、标签管理 |
| 管理员 | `admin` | 系统管理：用户、角色、审计日志 |

### 4.4 事件总线 (`app/core/events.py`)

进程内异步事件派发，使用 `asyncio.create_task` 异步执行订阅者，不阻塞发布方。

v1 事件类型：

| 事件 | 触发时机 | 消费者 |
|------|---------|--------|
| `poc.created` | POC 创建 | 审计日志（M2 接入） |
| `poc.updated` | POC 更新 | 审计日志（M2 接入） |
| `poc.deleted` | POC 删除 | 审计日志（M2 接入） |
| `poc.status_changed` | POC 状态变更 | 审计日志（M2 接入） |
| `poc.version_created` | POC 内容版本快照 | 审计日志（M2 接入） |
| `poc.batch_imported` | 批量导入完成 | 审计日志（M2 接入） |

### 4.5 缓存抽象 (`app/core/cache.py`)

统一接口，后端可切换：

```python
cache = get_cache()  # 根据 CACHE_BACKEND 配置返回对应实现
cache.set("key", value, ttl=60)
value = cache.get("key")
cache.delete("key")
```

- v1 默认：`InprocCache`（`cachetools.TTLCache`，maxsize=1024）
- v2 可切换：Redis（通过 `CACHE_BACKEND=redis` 配置）

### 4.6 插件框架 (`app/plugins/`)

v1 定义接口契约与注册表，M3 实现完整发现/加载/生命周期管理。

**NormalizedPoc（中间表示）**：插件与核心存储之间的稳定契约，任意来源的数据必须先归一化为 IR。

**接口契约**：

| 接口 | 方法 | 用途 |
|------|------|------|
| `PocSource` | `fetch(params) -> list[NormalizedPoc]` | POC 来源（手动/AI/爬取） |
| `PocParser` | `parse(raw) -> list[NormalizedPoc]` | 格式解析（nuclei/JSON/pocsuite3） |
| `PocVerifier` | `verify(poc, target, options)` | 验证引擎（v2 实现） |
| `PocExporter` | `export(pocs) -> str` | 导出（v2 实现） |

---

## 5. 数据模型

### 5.1 当前模型（M1）

**user 表**：用户认证与授权

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, AUTO_INCREMENT | 主键 |
| username | String(64) | UNIQUE, NOT NULL, INDEX | 用户名 |
| email | String(255) | UNIQUE, INDEX | 邮箱 |
| password_hash | String(128) | NOT NULL | bcrypt 哈希 |
| role_id | Integer | FK → role.id | 角色 |
| is_active | Boolean | NOT NULL, DEFAULT TRUE | 启用状态 |
| last_login_at | DateTime(3) | Nullable | 最后登录时间 |
| created_at | DateTime(3) | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime(3) | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**role 表**：RBAC 角色

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, AUTO_INCREMENT | 主键 |
| name | String(32) | UNIQUE, NOT NULL | 角色名 |
| description | String(255) | Nullable | 描述 |
| permissions | String(2048) | NOT NULL | 权限 JSON 字符串 |

### 5.2 规划模型（M2）

M2 将引入以下模型：

- **poc**：POC 主表（name, title, description, category, severity, format, content, content_hash, author, source, status, version, extra_meta JSON）
- **poc_version**：POC 内容历史版本快照
- **vuln**：CVE 漏洞实体
- **poc_vuln**：POC↔CVE 多对多关联
- **tag**：标签字典
- **poc_tag**：POC↔标签多对多关联
- **poc_source_record**：来源溯源记录
- **poc_attachment**：附属文件
- **audit_log**：操作审计日志

---

## 6. API 接口文档

### 6.1 接口规范

- **基础路径**：`/api/v1`
- **响应格式**：统一 `{code, message, data, request_id}`
- **鉴权方式**：`Authorization: Bearer <access_token>`
- **分页约定**：`?page=1&page_size=20`（上限 100）
- **错误码**：见 §4.2 统一异常体系

### 6.2 当前接口（M1）

#### 健康检查

```
GET /api/v1/health
```

无需鉴权。返回数据库连通性状态。

```json
// 200 OK
{
  "code": "OK",
  "message": "success",
  "data": {
    "status": "ok",
    "db": "up"
  },
  "request_id": ""
}
```

#### 用户登录

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

```json
// 200 OK
{
  "code": "OK",
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@vulnscope.local",
      "role": "admin",
      "is_active": true
    }
  },
  "request_id": ""
}
```

```json
// 401 认证失败
{
  "code": "AUTH_INVALID_CREDENTIALS",
  "message": "用户名或密码错误",
  "data": {},
  "request_id": ""
}
```

#### 刷新 Token

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

```json
// 200 OK
{
  "code": "OK",
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  },
  "request_id": ""
}
```

#### 获取当前用户

```
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

```json
// 200 OK
{
  "code": "OK",
  "message": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@vulnscope.local",
    "role": "admin",
    "is_active": true
  },
  "request_id": ""
}
```

### 6.3 规划接口（M2+）

| 方法 | 路径 | 说明 | 里程碑 |
|------|------|------|--------|
| GET/POST | `/pocs` | POC 分页查询 / 创建 | M2 |
| GET/PUT/DELETE | `/pocs/{id}` | POC 详情 / 更新 / 删除 | M2 |
| PATCH | `/pocs/{id}/status` | POC 状态流转 | M2 |
| GET | `/pocs/search?q=` | 关键字搜索 | M2 |
| GET | `/pocs/{id}/versions` | POC 版本历史 | M2 |
| POST | `/pocs/{id}/clone` | 复制 POC | M2 |
| POST | `/import` | 导入 POC | M2 |
| GET | `/export` | 导出 POC | M2 |
| GET/POST | `/tags` | 标签管理 | M2 |
| GET | `/vulns` | CVE 漏洞库 | M2 |
| GET | `/plugins` | 插件列表 | M3 |
| GET/POST | `/users` | 用户管理（管理员） | M2 |
| GET/POST | `/audit-logs` | 审计日志 | M2 |

---

## 7. 配置说明

### 7.1 快速配置

复制环境变量模板并修改：

```bash
cp .env.example .env
```

### 7.2 数据库切换

**SQLite（开发环境，默认）**：

```ini
VULNSCOPE_DB_BACKEND=sqlite
```

数据库文件为 `backend/vulnscope.db`，无需额外安装。

**MySQL（生产环境）**：

```ini
VULNSCOPE_DB_BACKEND=mysql
VULNSCOPE_DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/vulnscope?charset=utf8mb4
```

需要安装 `pymysql`：`pip install pymysql`。

### 7.3 生产环境配置清单

| 配置项 | 要求 |
|--------|------|
| `VULNSCOPE_SECRET_KEY` | 32 字节以上随机字符串，推荐 `openssl rand -hex 32` |
| `VULNSCOPE_DB_BACKEND` | 切换为 `mysql` |
| `VULNSCOPE_DATABASE_URL` | 使用最小权限数据库账号 |
| `VULNSCOPE_APP_ENV` | 设为 `prod` |
| `VULNSCOPE_DEBUG` | 设为 `false` |
| `VULNSCOPE_SEED_ADMIN_PASSWORD` | 修改为强密码 |

---

## 8. 运行指引

### 8.1 环境要求

- Python 3.10+
- 可选：MySQL 8.0（生产环境）
- 可选：Redis 7（v2 验证模块）

### 8.2 首次运行

```bash
# 进入后端目录
cd D:\Objects\VulnScope\backend

# 创建虚拟环境
python -m venv .venv

# 安装依赖（含开发依赖）
.venv\Scripts\pip install -e ".[dev]"

# 复制环境变量配置
cp .env.example .env

# 启动服务（自动执行数据库迁移）
start.bat       # Windows
# 或 ./start.sh  # Git Bash
```

### 8.3 启动脚本说明

**`start.bat`（Windows 命令提示符）**：

```batch
start.bat              # 迁移 + 启动
start.bat --no-migrate # 仅启动，跳过迁移
start.bat --port 8080  # 自定义端口
```

**`start.sh`（Git Bash）**：

```bash
./start.sh              # 迁移 + 启动
./start.sh --no-migrate # 仅启动
./start.sh --port 8080  # 自定义端口
```

### 8.4 手动启动步骤

```bash
# 1. 激活虚拟环境
.venv\Scripts\activate

# 2. 执行数据库迁移
alembic upgrade head

# 3. 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 8.5 访问地址

| 地址 | 说明 |
|------|------|
| http://127.0.0.1:8000 | API 基础地址 |
| http://127.0.0.1:8000/docs | Swagger UI 交互文档 |
| http://127.0.0.1:8000/redoc | ReDoc 文档 |
| http://127.0.0.1:8000/api/v1/health | 健康检查 |
| http://127.0.0.1:8000/openapi.json | OpenAPI 规范文件 |

### 8.6 默认管理员账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | admin |

首次启动时自动创建，修改密码请更新 `.env` 中的 `VULNSCOPE_SEED_ADMIN_PASSWORD` 后删除数据库重新迁移。

---

## 9. 开发指南

### 9.1 新增 API 路由

```python
# app/api/v1/poc.py
from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ok

router = APIRouter(prefix="/pocs", tags=["pocs"])


@router.get("")
def list_pocs(request: Request, db: DbSession, user: CurrentUser) -> dict:
    """获取 POC 列表。"""
    # 业务逻辑...
    return ok({"items": [], "total": 0}, request)
```

然后在 `app/api/v1/__init__.py` 中注册：

```python
from app.api.v1 import auth, health, poc  # noqa: F401
```

在 `app/main.py` 中挂载：

```python
app.include_router(poc.router, prefix=api_prefix)
```

### 9.2 新增数据模型

```python
# app/models/poc.py
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPKMixin, TimestampMixin


class Poc(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "poc"

    name: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
```

然后在 `app/models/__init__.py` 中导出：

```python
from app.models.poc import Poc  # noqa: F401
```

生成迁移：

```bash
alembic revision --autogenerate -m "add poc model"
alembic upgrade head
```

### 9.3 代码规范

```bash
# 代码格式
.venv\Scripts\black.exe app/ tests/

# 代码检查
.venv\Scripts\ruff.exe check app/ tests/

# 类型检查
.venv\Scripts\mypy.exe app/
```

### 9.4 数据库迁移管理

```bash
# 生成自动迁移（基于模型变更）
alembic revision --autogenerate -m "变更说明"

# 查看迁移历史
alembic history

# 应用所有待执行迁移
alembic upgrade head

# 回滚最近一次迁移
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>
```

---

## 10. 质量保障

### 10.1 运行测试

```bash
# 运行全部测试
.venv\Scripts\pytest.exe -v

# 运行指定测试文件
.venv\Scripts\pytest.exe -v tests/test_auth.py

# 运行指定测试类
.venv\Scripts\pytest.exe -v tests/test_auth.py::TestLogin

# 显示覆盖率（需安装 pytest-cov）
.venv\Scripts\pytest.exe --cov=app tests/
```

### 10.2 测试策略

| 层次 | 测试方法 | 工具 |
|------|---------|------|
| 服务层 | 单元测试，mock DB 会话 | pytest |
| API 层 | 集成测试，TestClient + 内存 SQLite | httpx + pytest |
| 插件契约 | 接口实现验证 | pytest |
| 迁移 | Alembic 升级/回滚验证 | alembic command |

### 10.3 测试夹具说明

`tests/conftest.py` 提供以下夹具：

| 夹具 | 类型 | 用途 |
|------|------|------|
| `db` | Session | 含种子数据的数据库会话 |
| `client` | TestClient | FastAPI 测试客户端，自动覆盖 DB 依赖 |
| `admin_token` | str | 管理员 access token |
| `auth_header` | dict | `Authorization: Bearer <token>` 请求头 |

### 10.4 测试用例清单（M1，12 个）

**健康检查**（`test_health.py`）：
- `test_health_ok`：正常响应用包含 status=ok 与 db=up
- `test_health_structure`：响应包含统一包装字段

**用户登录**（`test_auth.py::TestLogin`）：
- `test_login_success`：正常凭据返回 token 与用户信息
- `test_login_wrong_password`：错误密码返回 401
- `test_login_nonexistent`：不存在的用户返回 401（不区分原因）
- `test_login_empty_fields`：空字段触发 Pydantic 校验返回 422

**当前用户**（`test_auth.py::TestMe`）：
- `test_me_authenticated`：有效 token 返回用户信息
- `test_me_no_token`：无 token 返回 401
- `test_me_invalid_token`：伪造 token 返回 401
- `test_me_expired_token`：过期 token 返回 401

**Token 刷新**（`test_auth.py::TestRefresh`）：
- `test_refresh_success`：有效 refresh token 返回新 token 对
- `test_refresh_with_access_token`：用 access token 刷新被拒绝

---

## 附录

### A. 开发里程碑

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M1 骨架 | 项目脚手架、配置分层、DB 迁移、鉴权、统一异常、插件接口 | ✅ 完成 |
| M2 核心存储 | POC/Vuln/Tag/PocVersion 模型、CRUD API、过滤排序分页、搜索 | ⏳ 进行中 |
| M3 插件框架 | 注册表、事件总线、Parser/Source 槽、Nuclei 解析器、模板校验 | ⏳ 待开始 |
| M4 导入导出 | 导入向导 API、格式嗅探、去重、导出 | ⏳ 待开始 |
| M5 前端 | Vue3 列表/详情/导入/标签/插件面板/系统页 | ⏳ 待开始 |
| M6 收尾 | Docker Compose、种子数据、文档、压测 | ⏳ 待开始 |

### B. 依赖清单

```
fastapi>=0.110       # Web 框架
uvicorn[standard]    # ASGI 服务器
sqlalchemy>=2.0      # ORM
alembic>=1.13        # 数据库迁移
pydantic>=2.6        # 数据校验
pydantic-settings>=2.2  # 配置管理
PyJWT>=2.8           # JWT 签发校验
bcrypt>=4.1          # 密码哈希
python-multipart>=0.0.9  # 表单解析
cachetools>=5.3      # 进程内缓存

# 开发依赖
pytest>=8.0          # 测试框架
httpx>=0.27          # HTTP 测试客户端
ruff>=0.3            # 代码检查
black>=24.2          # 代码格式化
mypy>=1.9            # 类型检查
pytest-asyncio>=0.23  # 异步测试支持
```

### C. 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 开发方案总纲 | `docs/开发方案.md` | 完整系统设计方案 |
| Nuclei 模板参考 | `docs/poc-template/nuclei-reference.yaml` | 标准 POC 模板规范 |
| OpenAPI 文档 | `/docs`（运行时） | Swagger UI 交互式文档 |