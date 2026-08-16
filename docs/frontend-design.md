# VulnScope POC 管理系统 — 前端设计文档

> 版本：v1.0 | 日期：2026-08-14 | 对应后端：`backend/` v0.1.0 | 技术栈：Vue 3 + TypeScript + Vite + Element Plus + Pinia

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈与工程规范](#2-技术栈与工程规范)
3. [项目结构](#3-项目结构)
4. [路由与导航架构](#4-路由与导航架构)
5. [状态管理](#5-状态管理)
6. [API 层设计](#6-api-层设计)
7. [页面详细设计](#7-页面详细设计)
   - [7.1 登录页](#71-登录页)
   - [7.2 工作台（Dashboard）](#72-工作台dashboard)
   - [7.3 POC 列表页](#73-poc-列表页)
   - [7.4 POC 详情页](#74-poc-详情页)
   - [7.5 POC 新建/编辑页](#75-poc-新建编辑页)
   - [7.6 导入向导页](#76-导入向导页)
   - [7.7 标签管理页](#77-标签管理页)
   - [7.8 CVE 漏洞库页](#78-cve-漏洞库页)
   - [7.9 插件面板页](#79-插件面板页)
   - [7.10 用户管理页](#710-用户管理页)
   - [7.11 审计日志页](#711-审计日志页)
8. [组件树](#8-组件树)
9. [设计系统](#9-设计系统)
10. [路由守卫与权限](#10-路由守卫与权限)
11. [国际化与文案](#11-国际化与文案)
12. [开发优先级](#12-开发优先级)

---

## 1. 项目概述

### 1.1 产品定位

VulnScope 是一套**以 POC（Proof of Concept，漏洞验证脚本/模板）为核心资产**的管理系统。前端为 Web 管理后台，面向安全工程师、渗透测试人员、安全运维团队，提供 POC 的检索、管理、导入导出、分类标签等能力，未来扩展至验证执行、AI 生成等模块。

### 1.2 用户角色

| 角色 | 标识 | 权限范围 |
|------|------|---------|
| 查看者 | `viewer` | 只读：查看 POC 列表/详情、标签、CVE、插件状态、Dashboard |
| 编辑者 | `editor` | 增删改：POC 增删改、导入导出、标签管理 |
| 管理员 | `admin` | 系统管理：用户管理、角色管理、审计日志查看 |

### 1.3 设计原则

1. **内容为王，克制美学**：以深色中性色为背景，低饱和度冷色调强调色，全界面仅使用一种点缀色。拒绝毛玻璃、多色渐变、高饱和荧光色。
2. **扁平且坚实**：容器分隔依靠干净利落的实线边框，不使用发散型投影或光晕。
3. **动效服务于功能**：仅 hover/click 触发短暂样式切换（透明度/颜色渐变），过渡干脆。禁止自动播放、循环无限的入场动画。
4. **语义化网格**：信息层级严格遵循三种字号（标题/正文/辅助），模块间距遵循内在数学网格。

---

## 2. 技术栈与工程规范

### 2.1 技术选型

| 层次 | 组件 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | 3.4+ | `<script setup>` + TypeScript 组合式 API |
| 构建 | Vite | 5.x | 开发服务器 + 生产构建 |
| UI 库 | Element Plus | 2.6+ | 基础组件（表格、表单、对话框、菜单、分页、通知） |
| 状态管理 | Pinia | 2.1+ | 用户会话、缓存数据 |
| 路由 | vue-router | 4.3+ | 声明式路由 + 导航守卫 |
| HTTP | axios | 1.6+ | 请求封装、拦截器、JWT 刷新 |
| 代码编辑器 | Monaco Editor | 0.47+ | POC 内容编辑（YAML/JSON/Python 高亮） |
| 代码规范 | ESLint + Prettier | — | 代码检查与格式化 |
| 包管理 | pnpm | 9.x | 依赖管理 |

### 2.2 工程规范

- 组件命名：PascalCase，单文件组件（`.vue`）
- 组合式函数：`useXxx` 命名，存放于 `composables/` 目录
- API 模块：`api/xxx.ts`，每个文件对应一个后端资源模块
- Pinia Store：`stores/xxx.ts`，按业务模块拆分
- 类型定义：`types/` 目录，与后端 schema 对齐
- 样式：`<style scoped>` 优先，全局样式变量集中管理

---

## 3. 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── .env                          # 环境变量
├── .env.development              # 开发环境
├── .env.production               # 生产环境
├── public/
│   └── favicon.svg
└── src/
    ├── main.ts                   # 应用入口
    ├── App.vue                   # 根组件（布局容器）
    │
    ├── types/                    # TypeScript 类型定义
    │   ├── api.ts                # 统一响应类型 ApiResponse<T>、Page<T>
    │   ├── auth.ts               # 认证相关类型
    │   ├── poc.ts                # POC 类型
    │   ├── tag.ts                # 标签类型
    │   ├── vuln.ts               # CVE 漏洞类型
    │   ├── user.ts               # 用户类型
    │   ├── audit.ts              # 审计日志类型
    │   ├── dashboard.ts          # Dashboard 统计类型
    │   └── plugin.ts             # 插件类型
    │
    ├── api/                      # API 请求层
    │   ├── request.ts            # axios 实例 + 拦截器（JWT 刷新、错误处理）
    │   ├── auth.ts               # POST /auth/login, /auth/refresh, GET /auth/me
    │   ├── poc.ts                # POC CRUD + 搜索 + 版本 + 克隆 + 状态
    │   ├── tag.ts                # 标签 CRUD + 命名空间
    │   ├── vuln.ts               # CVE 漏洞库
    │   ├── dashboard.ts          # Dashboard 统计
    │   ├── import-export.ts      # 导入导出
    │   ├── plugin.ts             # 插件管理
    │   ├── audit.ts              # 审计日志
    │   └── user.ts               # 用户管理
    │
    ├── stores/                   # Pinia 状态管理
    │   ├── auth.ts               # 用户会话、token、角色
    │   └── app.ts                # 应用全局状态（侧边栏折叠、主题）
    │
    ├── composables/              # 组合式函数
    │   ├── usePagination.ts      # 分页逻辑复用
    │   ├── useTableSelection.ts  # 表格多选逻辑
    │   └── usePermission.ts      # 角色权限判断
    │
    ├── router/                   # 路由配置
    │   ├── index.ts              # 路由定义 + 导航守卫
    │   └── routes.ts             # 路由表
    │
    ├── layouts/                  # 布局组件
    │   ├── AppLayout.vue         # 主布局（侧边栏 + 顶栏 + 内容区）
    │   └── AuthLayout.vue        # 登录布局（居中卡片）
    │
    ├── views/                    # 页面组件
    │   ├── login/
    │   │   └── LoginView.vue
    │   ├── dashboard/
    │   │   └── DashboardView.vue
    │   ├── poc/
    │   │   ├── PocListView.vue
    │   │   ├── PocDetailView.vue
    │   │   ├── PocFormView.vue
    │   │   └── PocImportView.vue
    │   ├── tags/
    │   │   └── TagManageView.vue
    │   ├── vulns/
    │   │   └── VulnListView.vue
    │   ├── plugins/
    │   │   └── PluginListView.vue
    │   ├── system/
    │   │   ├── UserManageView.vue
    │   │   └── AuditLogView.vue
    │   └── error/
    │       ├── NotFoundView.vue
    │       └── ForbiddenView.vue
    │
    ├── components/               # 公共组件
    │   ├── common/
    │   │   ├── StatusBadge.vue    # 状态标签（severity/status 着色）
    │   │   ├── SeverityBadge.vue  # 严重级别徽标
    │   │   ├── TagChip.vue        # 标签色块
    │   │   ├── EmptyState.vue     # 空状态占位
    │   │   ├── ConfirmDialog.vue  # 确认对话框
    │   │   └── PageHeader.vue     # 页面标题 + 操作区
    │   ├── poc/
    │   │   ├── PocFilters.vue     # 高级筛选栏
    │   │   ├── PocTable.vue       # POC 列表表格
    │   │   ├── PocCodeViewer.vue  # 只读代码展示
    │   │   └── VersionTimeline.vue # 版本历史时间线
    │   ├── dashboard/
    │   │   ├── StatsCard.vue      # 统计卡片
    │   │   ├── DistributionChart.vue # 分布图表（饼图/柱状图）
    │   │   └── TrendChart.vue     # 趋势折线图
    │   └── layout/
    │       ├── SidebarNav.vue     # 侧边栏导航
    │       ├── TopBar.vue         # 顶栏（用户信息、搜索入口）
    │       └── BreadcrumbNav.vue  # 面包屑导航
    │
    ├── styles/                   # 全局样式
    │   ├── variables.scss        # SCSS 变量（色彩、间距、字号）
    │   ├── reset.scss            # 浏览器默认样式重置
    │   ├── global.scss           # 全局样式（导入 variables + reset）
    │   └── transitions.scss      # 过渡动画定义
    │
    └── utils/                    # 工具函数
        ├── format.ts             # 日期格式化、枚举映射
        ├── constants.ts          # 常量定义（状态枚举、严重级别映射）
        └── validators.ts         # 表单校验规则
```

---

## 4. 路由与导航架构

### 4.1 路由表

```typescript
// router/routes.ts
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '工作台', icon: 'Grid' },
      },
      {
        path: 'pocs',
        name: 'PocList',
        component: () => import('@/views/poc/PocListView.vue'),
        meta: { title: 'POC 列表', icon: 'Document' },
      },
      {
        path: 'pocs/new',
        name: 'PocCreate',
        component: () => import('@/views/poc/PocFormView.vue'),
        meta: { title: '新建 POC', icon: 'Edit', roles: ['editor', 'admin'] },
      },
      {
        path: 'pocs/:id',
        name: 'PocDetail',
        component: () => import('@/views/poc/PocDetailView.vue'),
        meta: { title: 'POC 详情' },
      },
      {
        path: 'pocs/:id/edit',
        name: 'PocEdit',
        component: () => import('@/views/poc/PocFormView.vue'),
        meta: { title: '编辑 POC', roles: ['editor', 'admin'] },
      },
      {
        path: 'pocs/import',
        name: 'PocImport',
        component: () => import('@/views/poc/PocImportView.vue'),
        meta: { title: '导入 POC', icon: 'Upload', roles: ['editor', 'admin'] },
      },
      {
        path: 'tags',
        name: 'TagManage',
        component: () => import('@/views/tags/TagManageView.vue'),
        meta: { title: '标签管理', icon: 'Collection' },
      },
      {
        path: 'vulns',
        name: 'VulnList',
        component: () => import('@/views/vulns/VulnListView.vue'),
        meta: { title: 'CVE 漏洞库', icon: 'Warning' },
      },
      {
        path: 'plugins',
        name: 'PluginList',
        component: () => import('@/views/plugins/PluginListView.vue'),
        meta: { title: '插件面板', icon: 'Setting' },
      },
      {
        path: 'system/users',
        name: 'UserManage',
        component: () => import('@/views/system/UserManageView.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] },
      },
      {
        path: 'system/audit-logs',
        name: 'AuditLog',
        component: () => import('@/views/system/AuditLogView.vue'),
        meta: { title: '审计日志', icon: 'List', roles: ['admin'] },
      },
    ],
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/ForbiddenView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFoundView.vue'),
  },
]
```

### 4.2 侧边栏导航结构

```
┌─ 工作台           ─┐  /dashboard             viewer/editor/admin
├─ POC 管理          ─┤
│  ├─ POC 列表       │  /pocs                  viewer/editor/admin
│  ├─ 新建 POC       │  /pocs/new              editor/admin
│  └─ 导入 POC       │  /pocs/import           editor/admin
├─ 标签管理          ─┤  /tags                  viewer/editor/admin
├─ CVE 漏洞库        ─┤  /vulns                 viewer/editor/admin
├─ 插件面板          ─┤  /plugins               viewer/editor/admin
└─ 系统管理          ─┤
   ├─ 用户管理       │  /system/users           admin
   └─ 审计日志       │  /system/audit-logs      admin
```

### 4.3 导航守卫逻辑

```typescript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 1. 未登录 → 重定向到 /login
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // 2. 已登录访问 /login → 重定向到 /dashboard
  if (to.name === 'Login' && authStore.isAuthenticated) {
    return next({ name: 'Dashboard' })
  }

  // 3. RBAC 角色校验
  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles && !requiredRoles.includes(authStore.user.role)) {
    return next({ name: 'Forbidden' })
  }

  next()
})
```

---

## 5. 状态管理

### 5.1 auth Store

```typescript
// stores/auth.ts
interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserInfo | null
}

// getters
isAuthenticated: boolean     // accessToken 存在
userRole: string             // 当前用户角色
isAdmin: boolean             // 角色 === 'admin'
isEditor: boolean            // 角色 === 'editor'
isViewer: boolean            // 角色 === 'viewer'

// actions
login(username, password)    // 登录 + 存储 token + 用户信息
logout()                     // 清除 token + 跳转登录页
refreshToken()               // 使用 refresh_token 获取新 token
fetchCurrentUser()           // GET /auth/me 刷新用户信息
```

### 5.2 app Store

```typescript
// stores/app.ts
interface AppState {
  sidebarCollapsed: boolean
  globalLoading: boolean
}

// actions
toggleSidebar()
setGlobalLoading(loading)
```

---

## 6. API 层设计

### 6.1 axios 实例封装

```typescript
// api/request.ts
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：注入 Authorization header
service.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  return config
})

// 响应拦截器：统一错误处理 + JWT 自动刷新
service.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data
    if (code !== 'OK') {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }
    return data  // 直接返回 data 字段，简化调用方
  },
  async (error) => {
    // 401 token 过期 → 尝试刷新
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      if (authStore.refreshToken) {
        try {
          await authStore.refreshToken()
          // 重试原请求
          const config = error.config
          config.headers.Authorization = `Bearer ${authStore.accessToken}`
          return service(config)
        } catch {
          authStore.logout()
        }
      } else {
        authStore.logout()
      }
    }
    ElMessage.error(error.response?.data?.message || '网络错误')
    return Promise.reject(error)
  }
)
```

### 6.2 API 模块清单

| 模块 | 文件 | 方法 | 后端接口 |
|------|------|------|---------|
| 认证 | `api/auth.ts` | `login()`, `refresh()`, `getMe()` | POST login, POST refresh, GET me |
| POC | `api/poc.ts` | `list()`, `get()`, `create()`, `update()`, `remove()`, `search()`, `changeStatus()`, `clone()`, `getVersions()`, `getSourceRecords()` | GET/POST /pocs, GET/PUT/DELETE /pocs/{id}, GET /pocs/search, PATCH /pocs/{id}/status, POST /pocs/{id}/clone, GET /pocs/{id}/versions, GET /pocs/{id}/source-records |
| 标签 | `api/tag.ts` | `list()`, `get()`, `create()`, `update()`, `remove()`, `listNamespaces()` | GET/POST /tags, GET/PUT/DELETE /tags/{id}, GET /tags/namespaces |
| CVE | `api/vuln.ts` | `list()`, `get()`, `getByCveId()` | GET /vulns, GET /vulns/{id}, GET /vulns/by-cve/{cve_id} |
| Dashboard | `api/dashboard.ts` | `getStats()`, `getSeverity()`, `getStatus()`, `getSource()`, `getFormat()`, `getTimeline()`, `getTopTags()`, `getTopAuthors()`, `getRecentActivities()`, `getTrend()`, `getTagCloud()`, `getFull()` | GET /dashboard/stats, /severity, /status, /source, /format, /timeline, /top-tags, /top-authors, /recent-activities, /trend, /tag-cloud, /full |
| 导入导出 | `api/import-export.ts` | `importPocs()`, `exportPocs()` | POST /import, GET /export |
| 插件 | `api/plugin.ts` | `list()`, `listBySlot()` | GET /plugins, GET /plugins/{slot} |
| 审计 | `api/audit.ts` | `list()` | GET /audit-logs |
| 用户 | `api/user.ts` | `list()`, `get()`, `create()`, `update()`, `remove()`, `listRoles()` | GET/POST /users, GET/PUT/DELETE /users/{id}, GET /users/roles |

---

## 7. 页面详细设计

### 7.1 登录页

**路径**：`/login`
**角色**：无需认证
**布局**：`AuthLayout`（居中卡片，深色背景）

**功能点**：
- 用户名/密码表单（Element Plus 表单组件）
- 登录按钮 → 调 `POST /auth/login` → 存储 token → 跳转 redirect 或 /dashboard
- 错误提示：用户名或密码错误（统一文案，不区分具体原因）

**设计要点**：
- 居中卡片容器，宽度 420px，实线边框，无投影
- 品牌 Logo 位于卡片上方（文字 Logo "VulnScope"）
- 表单字段：用户名（输入框）、密码（密码框，可切换可见性）
- 提交按钮 100% 宽度，禁用状态在请求期间

**状态流转**：
- 默认 → 输入中 → 提交中（按钮 loading）→ 成功（跳转）或失败（错误提示）

---

### 7.2 工作台（Dashboard）

**路径**：`/dashboard`
**角色**：viewer / editor / admin
**后端 API**：`GET /dashboard/full`（一次获取全量数据）

**布局**：统计卡片行（4 列）→ 分布图行（3 列）→ 趋势图行（2 列）→ 列表行（2 列）

**区块划分**：

| 区域 | 内容 | 数据来源 |
|------|------|---------|
| 统计卡片行 | POC 总数、活跃 POC 数、CVE 漏洞数、标签数 | `stats` |
| 分布图行 | 严重级别分布（柱状图）、状态分布（饼图）、来源分布（饼图） | `severity_distribution`, `status_distribution`, `source_distribution` |
| 趋势图行 | POC 创建趋势（折线图）、漏洞趋势对比（双轴折线图） | `creation_timeline`, `trend` |
| 底部行 | 热门标签（柱状图/标签云）、最近活动（时间线列表） | `top_tags`, `recent_activities` |

**数据加载策略**：
- 页面加载时一次调用 `GET /dashboard/full` 获取全量数据
- 后端缓存 5 分钟，POC 变更时自动失效
- 无需手动刷新按钮，数据过期后自动重新请求

**设计要点**：
- 统计卡片：纯数字 + 标签文字，无图标/装饰，字号层级分明
- 图表：使用原生 SVG 或轻量级 canvas 图表库（如 Chart.js 或自定义 SVG）
- 最近活动：简洁列表，展示 poc_name + action 中文映射 + 相对时间

---

### 7.3 POC 列表页

**路径**：`/pocs`
**角色**：viewer / editor / admin
**后端 API**：`GET /pocs?page=&page_size=&severity=&status=&source=&format=&q=&tag_ids=&cve=&category_id=&sort_by=&sort_order=`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "POC 列表"  [新建 POC] [导入 POC] [导出]       │
├──────────────────────────────────────────────────────────────┤
│  筛选栏（多行）                                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ ┌──────┐ │
│  │ 关键字 │ │ 级别  │ │ 状态  │ │ 来源  │ │ 标签选择  │ │ 筛选 │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘ └──────┘ │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ ┌────────────────┐│
│  │ 格式  │ │ CVE  │ │ 分类  │ │ 时间范围  │ │ 清空筛选       ││
│  └──────┘ └──────┘ └──────┘ └──────────┘ └────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  批量操作栏（选中时显示）                                     │
│  已选 N 项  [批量改状态] [批量导出] [批量删除]               │
├──────────────────────────────────────────────────────────────┤
│  POC 表格                                                     │
│  ┌──┬────────┬────────┬────┬────┬────┬────┬────┬──────────┐ │
│  │□ │ 名称   │ 标题   │ 级别│状态│来源│格式│CVE │ 更新时间  │ │
│  │□ │ struts │ ...    │ 高  │启用│手动│yaml│CVE-│ 2026-... │ │
│  │  │ ...    │ ...    │ ...│ ...│ ...│ ...│ ...│ ...      │ │
│  └──┴────────┴────────┴────┴────┴────┴────┴────┴──────────┘ │
├──────────────────────────────────────────────────────────────┤
│  分页                                                         │
│  共 N 条  第 1/10 页  < 1 2 3 ... 10 >  每页 20 条          │
└──────────────────────────────────────────────────────────────┘
```

**筛选栏详细**：

| 筛选器 | 组件 | 后端参数 | 数据来源 |
|--------|------|---------|---------|
| 关键字搜索 | el-input + search icon | `q` | 用户输入 |
| 严重级别 | el-select 多选 | `severity` | 常量枚举 |
| 状态 | el-select 多选 | `status` | 常量枚举 |
| 来源 | el-select 多选 | `source` | 常量枚举 |
| 格式 | el-select 多选 | `format` | 常量枚举 |
| 标签 | el-select 多选（带搜索） | `tag_ids` | `GET /tags` |
| CVE 编号 | el-input | `cve` | 用户输入 |
| 分类 | el-tree-select 或 el-cascader | `category_id` | `GET /categories`（需后端补充） |
| 时间范围 | el-date-picker (daterange) | `created_at_from`, `created_at_to` | 用户选择 |
| 排序 | 表头点击切换 | `sort_by`, `sort_order` | 交互触发 |

**表格列定义**：

| 列 | 宽度 | 展示 | 说明 |
|----|------|------|------|
| 选择框 | 40px | el-checkbox | 批量操作 |
| 名称 | 180px | 文字 + 复制按钮 | `poc.name` |
| 标题 | 200px | 文字 | `poc.title`，超长省略 |
| 严重级别 | 90px | `<SeverityBadge>` | 按级别着色（critical=红, high=橙, medium=黄, low=蓝, info=灰） |
| 状态 | 80px | `<StatusBadge>` | 着色区分（active=绿, draft=灰, disabled=红, archived=紫） |
| 来源 | 80px | 文字 | 中文映射 |
| 格式 | 80px | 文字 | 格式标识 |
| 标签 | 150px | `<TagChip>` 行内展示 | 展示前 3 个，多余显示 "+N" |
| CVE | 130px | 文字 | 逗号分隔 |
| 作者 | 100px | 文字 | `poc.author` |
| 更新时间 | 160px | 相对时间 | 鼠标悬停显示完整时间 |
| 操作 | 120px | 查看/编辑/删除按钮 | 编辑/删除仅 editor/admin |

**批量操作**：

| 操作 | 按钮 | 确认 | 权限 |
|------|------|------|------|
| 批量改状态 | 下拉选择目标状态 | 确认对话框 | editor/admin |
| 批量导出 | 点击后下载文件 | 无 | viewer/editor/admin |
| 批量删除 | 红色按钮 | 确认对话框，输入删除数量确认 | editor/admin |

**空状态**：
- 无筛选条件时：显示"尚未添加任何 POC，点击「新建 POC」开始使用"
- 有筛选条件但无结果：显示"未找到匹配的 POC，请调整筛选条件"

---

### 7.4 POC 详情页

**路径**：`/pocs/:id`
**角色**：viewer / editor / admin
**后端 API**：`GET /pocs/{id}`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: 返回  [poc.name]  [编辑] [克隆] [删除] [状态]  │
├──────────────────────────────────────────────────────────────┤
│  两列布局                                                     │
│  ┌──────────── 左列（元数据） ────┬── 右列（代码内容） ───────┐│
│  │ 基本信息                       │  POC 内容                 ││
│  │  ┌────────────────────────┐   │  ┌──────────────────────┐ ││
│  │  │ 名称: struts2-s2-045   │   │  │ 代码编辑器（只读）     │ ││
│  │  │ 标题: Apache Struts2...│   │  │ 语法高亮              │ ││
│  │  │ 级别: 高               │   │  │ 行号                  │ ││
│  │  │ 状态: 已启用           │   │  │ 可折叠                │ ││
│  │  │ 来源: 手动             │   │  │ 复制按钮              │ ││
│  │  │ 格式: nuclei      │   │  └──────────────────────┘ ││
│  │  │ 语言: -                │   │                           ││
│  │  │ 作者: xiaoming         │   │                           ││
│  │  │ 版本: 3                │   │                           ││
│  │  │ 内容哈希: sha256...    │   │                           ││
│  │  │ 创建时间: 2026-08-10   │   │                           ││
│  │  │ 更新时间: 2026-08-13   │   │                           ││
│  │  └────────────────────────┘   │                           ││
│  │                               │                           ││
│  │  关联信息                     │                           ││
│  │  ┌────────────────────────┐   │                           ││
│  │  │ CVE 编号: CVE-2017-... │   │                           ││
│  │  │ 标签: rce, unauth, ... │   │                           ││
│  │  │ 分类: web.framework... │   │                           ││
│  │  └────────────────────────┘   │                           ││
│  │                               │                           ││
│  │  版本历史                     │                           ││
│  │  ┌────────────────────────┐   │                           ││
│  │  │ 时间线                  │   │                           ││
│  │  │ v3 2026-08-13 ...      │   │                           ││
│  │  │ v2 2026-08-11 ...      │   │                           ││
│  │  │ v1 2026-08-10 ...      │   │                           ││
│  │  └────────────────────────┘   │                           ││
│  │                               │                           ││
│  │  来源溯源                     │                           ││
│  │  ┌────────────────────────┐   │                           ││
│  │  │ 来源类型: manual        │   │                           ││
│  │  │ 抓取时间: -             │   │                           ││
│  │  └────────────────────────┘   │                           ││
│  └───────────────────────────────┴───────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**元数据面板**：
- 展示全部字段（对应 `PocResponse` schema）
- 严重级别、状态使用 `<SeverityBadge>` / `<StatusBadge>` 组件
- 标签使用 `<TagChip>` 组件行内展示
- 分类展示 slug 路径，带链接可跳转按分类筛选

**代码面板**：
- 使用 Monaco Editor，只读模式
- 语言根据 `format` 字段切换：nuclei → yaml, json → json, pocsuite3 → python, raw-script → 对应 `language` 字段
- 右上角：复制全文按钮、在新标签页打开原始内容

**版本历史**：
- 时间线组件，按 `version_seq` 降序排列
- 每条展示：版本号、变更时间、变更人
- 点击某版本可查看该版本内容（新版弹窗或切换编辑器内容）

**操作按钮**：

| 按钮 | 行为 | 权限 |
|------|------|------|
| 编辑 | 跳转 `/pocs/:id/edit` | editor/admin |
| 克隆 | 弹窗输入新名称 → `POST /pocs/{id}/clone` | editor/admin |
| 删除 | 确认对话框 → `DELETE /pocs/{id}` | editor/admin |
| 状态切换 | 下拉菜单，选项根据当前状态动态计算合法流转目标 | editor/admin |

---

### 7.5 POC 新建/编辑页

**路径**：`/pocs/new` / `/pocs/:id/edit`
**角色**：editor / admin
**后端 API**：`POST /pocs` / `PUT /pocs/{id}`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "新建 POC" / "编辑 POC"  [取消] [保存]          │
├──────────────────────────────────────────────────────────────┤
│  两列布局                                                     │
│  ┌──────────── 左列（表单） ────┬── 右列（代码编辑器） ───────┐│
│  │  基本字段                    │  代码编辑器（可编辑）        ││
│  │  ┌────────────────────────┐  │  ┌──────────────────────┐  ││
│  │  │ 名称 * (input)         │  │  │ Monaco Editor         │  ││
│  │  │ 标题 (input)           │  │  │ 语法高亮              │  ││
│  │  │ 严重级别 (select)      │  │  │ 行号                  │  ││
│  │  │ 状态 (select)          │  │  │ 自动补全（YAML）      │  ││
│  │  │ 来源 (select)          │  │  │ 全屏模式              │  ││
│  │  │ 格式 (select)          │  │  └──────────────────────┘  ││
│  │  │ 作者 (input)           │  │                            ││
│  │  │ 语言 (input, 条件显)   │  │                            ││
│  │  └────────────────────────┘  │                            ││
│  │                              │                            ││
│  │  关联字段                    │                            ││
│  │  ┌────────────────────────┐  │                            ││
│  │  │ CVE 编号 (tag-input)   │  │                            ││
│  │  │ 标签 (select)          │  │                            ││
│  │  │ 描述 (textarea)        │  │                            ││
│  │  └────────────────────────┘  │                            ││
│  └──────────────────────────────┴────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**表单字段**：

| 字段 | 组件 | 必填 | 默认值 | 校验规则 |
|------|------|------|--------|---------|
| 名称 | el-input | 是 | — | 小写字母数字开头，仅允许 `[a-z0-9.-]`，1-128 字符 |
| 标题 | el-input | 否 | — | 最大 255 字符 |
| 严重级别 | el-select | 是 | info | 枚举：info/low/medium/high/critical |
| 状态 | el-select | 是 | draft | 枚举：draft/active/disabled/archived |
| 来源 | el-select | 是 | manual | 枚举：manual/imported/ai/crawler |
| 格式 | el-select | 是 | nuclei | 枚举：nuclei/json/pocsuite3/raw-script |
| 作者 | el-input | 否 | — | 最大 128 字符 |
| 语言 | el-input | 否 | — | 格式为 raw-script 时显示 |
| 描述 | el-input type="textarea" | 否 | — | 富文本纯文本 |
| CVE 编号 | el-input (tag 模式) | 否 | [] | 匹配 `^CVE-\d{4}-\d{4,}$` |
| 标签 | el-select 多选 | 否 | [] | 从已有标签选择 |
| 代码内容 | Monaco Editor | 是 | — | 非空 |

**编辑模式特殊处理**：
- 加载时 `GET /pocs/{id}` 预填表单
- 内容变更时自动创建版本快照（后端逻辑）
- 名称字段不可编辑（显示为灰色只读，或提示"名称不可变更，如需改名请使用克隆功能"）

**保存行为**：
- 新建：`POST /pocs` → 成功后跳转 `/pocs/{id}` 
- 编辑：`PUT /pocs/{id}` → 成功后跳转 `/pocs/{id}`
- 失败时显示后端返回的错误消息（如内容重复、名称冲突）

---

### 7.6 导入向导页

**路径**：`/pocs/import`
**角色**：editor / admin
**后端 API**：`POST /import`

**步骤**：

```
Step 1: 选择导入方式    Step 2: 解析预览    Step 3: 完成报告
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │ 上传文件   │  ──→   │ 解析结果  │  ──→   │ 导入结果  │
   │ 粘贴文本   │         │ 冲突处理  │         │ 详细报告  │
   └──────────┘         └──────────┘         └──────────┘
```

**Step 1 详细**：
- 拖拽上传区域（Element Plus el-upload dragger）：支持 .yaml/.yml/.json/.py 文件，限制 10MB
- 文本粘贴区域（el-input type="textarea"）：粘贴 POC 模板文本
- 底部：来源类型选择（默认 "imported"）、默认状态选择（默认 "draft"）
- 下一步按钮

**Step 2 详细**：
- 解析完成后展示待导入 POC 列表（名称、级别、格式、CVE 预览）
- 已存在的 POC（content_hash 重复）标记为"已存在"，自动跳过
- 名称冲突（name + source 重复）标记为"待处理"：自动重命名或跳过
- 用户可手动勾选/取消各条 POC
- 确认导入按钮

**Step 3 详细**：
- 导入结果报告：成功数、跳过数、失败数
- 失败条目列表：展示每条失败原因（格式错误、校验失败等）
- 完成按钮 → 跳转 POC 列表（携带筛选参数显示新导入的 POC）

---

### 7.7 标签管理页

**路径**：`/tags`
**角色**：viewer / editor / admin（增删改需 editor/admin）
**后端 API**：`GET/POST /tags`, `GET/PUT/DELETE /tags/{id}`, `GET /tags/namespaces`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "标签管理"  [新建标签]                          │
├──────────────────────────────────────────────────────────────┤
│  标签表格（按命名空间分组）                                   │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ attack 命名空间                                          ││
│  │  ┌──────┬──────┬──────┬────────┬──────────┬──────────┐  ││
│  │  │ 名称  │ 颜色  │ 描述  │ POC 数 │ 操作     │          ││
│  │  │ rce   │ ● 红 │ 远程执行 │ 12    │ 编辑 删除 │          ││
│  │  │ sqli  │ ● 蓝 │ SQL注入  │ 8     │ 编辑 删除 │          ││
│  │  └──────┴──────┴──────┴────────┴──────────┴──────────┘  ││
│  │                                                          ││
│  │ auth 命名空间                                            ││
│  │  ┌──────┬──────┬──────┬────────┬──────────┬──────────┐  ││
│  │  │ unauth│ ● 灰 │ 未授权 │ 15    │ 编辑 删除 │          ││
│  │  └──────┴──────┴──────┴────────┴──────────┴──────────┘  ││
│  └──────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  （无分页或简短分页，标签数量通常 < 200）                     │
└──────────────────────────────────────────────────────────────┘
```

**新建/编辑标签对话框**：

| 字段 | 组件 | 必填 | 说明 |
|------|------|------|------|
| 命名空间 | el-select + 可输入 | 是 | 从已有命名空间选择或输入新值 |
| 标签名 | el-input | 是 | 唯一约束 `(namespace, name)` |
| 颜色 | el-color-picker | 否 | 十六进制颜色，用于标签展示 |
| 描述 | el-input | 否 | 255 字符以内 |

---

### 7.8 CVE 漏洞库页

**路径**：`/vulns`
**角色**：viewer / editor / admin
**后端 API**：`GET /vulns?page=&page_size=&severity=&q=`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "CVE 漏洞库"                                    │
├──────────────────────────────────────────────────────────────┤
│  筛选栏                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ 搜索 CVE  │ │ 级别筛选  │ │ 筛选按钮  │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
├──────────────────────────────────────────────────────────────┤
│  CVE 表格                                                    │
│  ┌──────────┬──────────┬──────┬──────┬────────┬──────────┐  │
│  │ CVE 编号  │ 标题     │ 级别  │ CVSS │ POC 数 │ 操作     │  │
│  │ CVE-2017 │ Apache... │ 高   │ 10.0 │ 3      │ 查看详情  │  │
│  └──────────┴──────────┴──────┴──────┴────────┴──────────┘  │
├──────────────────────────────────────────────────────────────┤
│  分页                                                        │
└──────────────────────────────────────────────────────────────┘
```

- 点击 CVE 编号可查看详情（弹窗展示完整的 CVE 信息 + 关联 POC 列表）
- POC 数可点击跳转至 POC 列表并预填 CVE 筛选条件

---

### 7.9 插件面板页

**路径**：`/plugins`
**角色**：viewer / editor / admin
**后端 API**：`GET /plugins`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "插件面板"                                       │
├──────────────────────────────────────────────────────────────┤
│  按插件槽分组展示                                             │
│                                                              │
│  ┌─ Parser 解析器 ───────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ nuclei v1.0.0  ● 已启用                    │   │   │
│  │  │ json-parser v0.1.0  ● 已启用                    │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Source 来源 ─────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ manual v1.0.0  ● 已启用                         │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Verifier 验证引擎 ──────────────────────────────────┐   │
│  │  （暂无注册插件）                                       │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Exporter 导出器 ────────────────────────────────────┐   │
│  │  （暂无注册插件）                                       │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

- 每个插件条目展示：名称、版本、启用状态（绿色/灰色圆点）
- 插件状态为启动时加载，运行期不可动态装卸（仅展示）

---

### 7.10 用户管理页

**路径**：`/system/users`
**角色**：admin
**后端 API**：`GET/POST /users`, `GET/PUT/DELETE /users/{id}`, `GET /users/roles`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "用户管理"  [新建用户]                          │
├──────────────────────────────────────────────────────────────┤
│  用户表格                                                    │
│  ┌────┬──────────┬──────────┬──────┬──────┬────────┬──────┐ │
│  │ ID │ 用户名    │ 邮箱     │ 角色  │ 状态  │ 最后登录│ 操作 │ │
│  │ 1  │ admin    │ admin@..│ 管理员│ 启用  │ 2026-.. │ 编辑 │ │
│  │ 2  │ zhangsan │ zhang@..│ 编辑者│ 启用  │ 2026-.. │ 编辑 │ │
│  └────┴──────────┴──────────┴──────┴──────┴────────┴──────┘ │
├──────────────────────────────────────────────────────────────┤
│  分页                                                        │
└──────────────────────────────────────────────────────────────┘
```

**新建/编辑用户对话框**：

| 字段 | 组件 | 必填 | 说明 |
|------|------|------|------|
| 用户名 | el-input | 是 | 3-64 字符，字母数字下划线连字符 |
| 邮箱 | el-input | 否 | 邮箱格式 |
| 密码 | el-input type="password" | 新建必填/编辑可选 | 最少 8 字符 |
| 角色 | el-select | 是 | viewer/editor/admin |
| 启用状态 | el-switch | 否 | 默认启用 |

**约束**：
- 不能删除内置 `admin` 账号
- 不能将自己（当前登录用户）的角色降级为无法管理用户的角色

---

### 7.11 审计日志页

**路径**：`/system/audit-logs`
**角色**：admin
**后端 API**：`GET /audit-logs?page=&page_size=&action=&resource_type=&user_id=`

**页面结构**：

```
┌──────────────────────────────────────────────────────────────┐
│  PageHeader: "审计日志"                                       │
├──────────────────────────────────────────────────────────────┤
│  筛选栏                                                      │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐    │
│  │ 操作类型  │ │ 资源类型      │ │ 用户 ID  │ │ 筛选按钮  │    │
│  └──────────┘ └──────────────┘ └──────────┘ └──────────┘    │
├──────────────────────────────────────────────────────────────┤
│  日志表格                                                    │
│  ┌────┬────────┬────────────┬────────┬──────────┬──────────┐│
│  │ 时间│ 用户    │ 操作       │ 资源   │ 资源 ID  │ 详情     ││
│  │ 08-│ admin  │ poc.created│ poc    │ 42       │ 摘要...  ││
│  │ ...│ ...    │ ...        │ ...    │ ...      │ ...      ││
│  └────┴────────┴────────────┴────────┴──────────┴──────────┘│
├──────────────────────────────────────────────────────────────┤
│  分页                                                        │
└──────────────────────────────────────────────────────────────┘
```

- 操作类型映射为中文：`poc.created` → "创建 POC", `poc.updated` → "更新 POC" 等
- 详情列：展示 `detail.before` 和 `detail.after` 的摘要，可点击展开查看完整 JSON
- 时间列：完整时间格式 `YYYY-MM-DD HH:mm:ss`

---

## 8. 组件树

### 8.1 公共组件

| 组件 | 用途 | Props |
|------|------|-------|
| `<StatusBadge>` | 状态标签着色 | `status: string`, `type?: 'status' \| 'severity'` |
| `<SeverityBadge>` | 严重级别徽标 | `severity: string`, `size?: 'small' \| 'default'` |
| `<TagChip>` | 标签色块展示 | `tag: { name, namespace, color }`, `closable?: boolean` |
| `<EmptyState>` | 空状态占位 | `icon?: string`, `title: string`, `description?: string`, `action?: { label, handler }` |
| `<ConfirmDialog>` | 确认对话框（封装 el-dialog） | `visible: boolean`, `title: string`, `message: string`, `confirmText?: string`, `type?: 'danger'` |
| `<PageHeader>` | 页面标题 + 操作区 | `title: string`, `description?: string`, `slots?: { actions }` |
| `<PocFilters>` | 高级筛选栏 | `filters: PocFilters`, `@change: (filters) => void` |
| `<PocTable>` | POC 列表表格 | `items: PocListItem[]`, `loading: boolean`, `selected: number[]`, `@selection-change`, `@row-click` |
| `<PocCodeViewer>` | 只读代码展示 | `content: string`, `language: string`, `height?: string` |
| `<VersionTimeline>` | 版本历史时间线 | `versions: PocVersion[]` |
| `<StatsCard>` | 统计卡片 | `label: string`, `value: number \| string`, `trend?: number` |
| `<DistributionChart>` | 分布图表 | `data: { key, count }[]`, `type: 'pie' \| 'bar'`, `title?: string` |
| `<TrendChart>` | 趋势折线图 | `data: { date, value }[]`, `title?: string` |

### 8.2 组件层级

```
App.vue
├── AuthLayout.vue
│   └── LoginView.vue
│
└── AppLayout.vue
    ├── SidebarNav.vue
    ├── TopBar.vue
    │   └── BreadcrumbNav.vue
    └── <router-view> (页面内容)
        │
        ├── DashboardView.vue
        │   ├── StatsCard.vue × 4
        │   ├── DistributionChart.vue × 3
        │   ├── TrendChart.vue × 2
        │   └── PocTable.vue (最近活动)
        │
        ├── PocListView.vue
        │   ├── PocFilters.vue
        │   ├── PocTable.vue
        │   └── ConfirmDialog.vue
        │
        ├── PocDetailView.vue
        │   ├── SeverityBadge.vue
        │   ├── StatusBadge.vue
        │   ├── TagChip.vue × N
        │   ├── PocCodeViewer.vue
        │   └── VersionTimeline.vue
        │
        ├── PocFormView.vue
        │   └── Monaco Editor
        │
        ├── PocImportView.vue
        │   └── el-upload / el-input (textarea)
        │
        ├── TagManageView.vue
        │   ├── TagChip.vue
        │   └── ConfirmDialog.vue
        │
        ├── VulnListView.vue
        ├── PluginListView.vue
        ├── UserManageView.vue
        │   └── ConfirmDialog.vue
        └── AuditLogView.vue
```

---

## 9. 设计系统

### 9.1 色彩系统

```
背景色（最深）:   #0e0e10   — 全局主背景
背景色（中深）:   #161618   — 卡片/容器背景
背景色（浅深）:   #1e1e22   — 侧边栏/顶栏
边框色:          #2a2a30   — 容器与卡片分隔（实线 1px）
文字色（主）:     #e0e0e6   — 正文
文字色（次）:     #909098   — 辅助说明
文字色（禁用）:   #505058   — 禁用状态

点缀色（冷色调，低饱和度，仅此一种）:
  强调蓝:         #4a8cba   — 按钮、链接、选中态、激活指示
  强调蓝悬停:     #5a9cca   — hover 状态

语义色（仅用于严重级别/状态标识，不参与主视觉）:
  critical:       #c43e3e   — 深红
  high:           #c47a3e   — 橙褐
  medium:         #c4a63e   — 金黄
  low:            #3e7ec4   — 灰蓝
  info:           #6a6a72   — 灰色
  active:         #3ea85e   — 绿
  disabled:       #c43e3e   — 红
  archived:       #7e5ec4   — 紫
```

### 9.2 排版系统

```
字体栈: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif

字号层级:
  Title:   16px/24px 600  — 页面标题、卡片标题
  Body:    14px/22px 400  — 正文、表格内容、表单标签
  Caption: 12px/18px 400  — 辅助说明、时间戳、标签

行高倍率: 1.5 (body), 1.4 (title)
```

### 9.3 间距网格

```
基础网格单元: 4px

间距系统（4px 倍数）:
  xs:  4px
  sm:  8px
  md:  12px
  lg:  16px
  xl:  24px
  xxl: 32px

卡片内边距: 16px (lg)
卡片间距:   16px (lg)
列表行高:   44px (含 padding)
```

### 9.4 交互反馈

```
按钮:
  - 默认状态: 填充色 强调蓝 #4a8cba
  - hover:    填充色 强调蓝悬停 #5a9cca
  - 过渡:     150ms ease（仅颜色变化）
  - 禁用:     透明度 0.4

表格行:
  - hover:    背景色变为 #1a1a20（仅亮度变化，无投影）
  - 选中:     背景色变为 #1e2230

链接:
  - 默认:     强调蓝 #4a8cba
  - hover:    强调蓝悬停 #5a9cca
  - 过渡:     100ms ease

输入框聚焦:
  - 边框色:   强调蓝 #4a8cba
  - 过渡:     150ms ease
```

### 9.5 容器与卡片

```
卡片:
  - 背景: #161618
  - 边框: 1px solid #2a2a30
  - 圆角: 4px
  - 投影: 无（禁止发散型投影）

对话框:
  - 背景: #161618
  - 边框: 1px solid #2a2a30
  - 遮罩: rgba(0, 0, 0, 0.6) 实色遮罩
  - 圆角: 4px

侧边栏:
  - 宽度: 220px（折叠后 64px）
  - 背景: #1e1e22
  - 右边框: 1px solid #2a2a30
```

### 9.6 动效规范

```
允许的过渡:
  1. hover 颜色变化: 150ms ease
  2. 侧边栏展开/折叠: 200ms ease（宽度变化）
  3. 弹窗出现/消失: 200ms ease（透明度 + 轻微位移 Y: -10px → 0）
  4. 加载状态: 简洁的线性旋转图标（非循环动画，仅请求期间展示）

严格禁止:
  - 任何自动播放、循环无限次的动画（呼吸灯、浮动、旋转）
  - 入场即触发的关键帧动画
  - 毛玻璃模糊效果（backdrop-filter: blur）
  - 拖沓的缓动曲线（cubic-bezier 超出 200ms）
```

---

## 10. 路由守卫与权限

### 10.1 权限矩阵

| 页面 | viewer | editor | admin |
|------|--------|--------|-------|
| 工作台（Dashboard） | ✅ | ✅ | ✅ |
| POC 列表 | ✅ | ✅ | ✅ |
| POC 详情 | ✅ | ✅ | ✅ |
| 新建 POC | ❌ | ✅ | ✅ |
| 编辑 POC | ❌ | ✅ | ✅ |
| 删除 POC | ❌ | ✅ | ✅ |
| 导入 POC | ❌ | ✅ | ✅ |
| 导出 POC | ✅ | ✅ | ✅ |
| 标签管理（查看） | ✅ | ✅ | ✅ |
| 标签管理（增删改） | ❌ | ✅ | ✅ |
| CVE 漏洞库 | ✅ | ✅ | ✅ |
| 插件面板 | ✅ | ✅ | ✅ |
| 用户管理 | ❌ | ❌ | ✅ |
| 审计日志 | ❌ | ❌ | ✅ |

### 10.2 前端权限实现

```typescript
// composables/usePermission.ts
export function usePermission() {
  const authStore = useAuthStore()

  const hasRole = (...roles: string[]) => {
    return roles.includes(authStore.user?.role || '')
  }

  const canEdit = () => hasRole('editor', 'admin')
  const canAdmin = () => hasRole('admin')

  return { hasRole, canEdit, canAdmin }
}
```

- 路由级：`meta.roles` 数组 + 导航守卫（见 §4.3）
- 组件级：`v-if="canEdit()"` 控制按钮/操作的显隐
- API 级：后端返回 403 时前端统一拦截并提示"权限不足"

---

## 11. 国际化与文案

### 11.1 文案准则

- 所有 UI 文案使用中文（简体）
- 操作按钮：使用"新建"、"编辑"、"删除"、"导入"、"导出"、"筛选"、"取消"、"保存"等职场高频动词
- 禁止"立即体验"、"马上去做"、"点击这里"等诱导式表达
- 错误提示：冷静、客观，直接说明原因

### 11.2 枚举中文映射

```typescript
// utils/constants.ts
export const SEVERITY_MAP: Record<string, string> = {
  info: '信息',
  low: '低危',
  medium: '中危',
  high: '高危',
  critical: '严重',
}

export const STATUS_MAP: Record<string, string> = {
  draft: '草稿',
  active: '已启用',
  disabled: '已禁用',
  archived: '已归档',
}

export const SOURCE_MAP: Record<string, string> = {
  manual: '手动录入',
  imported: '导入',
  ai: 'AI 生成',
  crawler: '爬取',
}

export const FORMAT_MAP: Record<string, string> = {
  'nuclei': 'Nuclei YAML',
  json: 'JSON',
  pocsuite3: 'Pocsuite3',
  'raw-script': '原始脚本',
}

export const ACTION_MAP: Record<string, string> = {
  'poc.created': '创建 POC',
  'poc.updated': '更新 POC',
  'poc.deleted': '删除 POC',
  'poc.status_changed': '状态变更',
  'poc.version_created': '版本快照',
  'poc.batch_imported': '批量导入',
}
```

---

## 12. 开发优先级

### Phase 1 — 基础框架（3 天）

| 任务 | 产出 |
|------|------|
| 项目脚手架搭建 | Vite + Vue 3 + TypeScript + Element Plus + Pinia + vue-router |
| 路由配置 + 导航守卫 | 路由表 + 登录守卫 + RBAC 守卫 |
| 登录页 | LoginView + auth store + axios 拦截器 |
| 主布局 | AppLayout + SidebarNav + TopBar |
| 全局样式系统 | SCSS 变量 + 色彩体系 + 排版 + 间距网格 |

### Phase 2 — POC 核心（5 天）

| 任务 | 产出 |
|------|------|
| POC 列表页 | PocListView + PocFilters + PocTable + 分页 + 筛选 |
| POC 详情页 | PocDetailView + 元数据面板 + 代码展示 + 版本历史 |
| POC 新建/编辑页 | PocFormView + Monaco Editor 集成 + 表单校验 |
| POC 状态流转 + 克隆 + 删除 | 操作按钮 + ConfirmDialog |

### Phase 3 — Dashboard（2 天）

| 任务 | 产出 |
|------|------|
| 统计卡片 | StatsCard × 4 |
| 分布图表 | DistributionChart（饼图 + 柱状图） |
| 趋势图表 | TrendChart（折线图） |
| 最近活动 | 时间线列表 |
| 全量数据加载 | `GET /dashboard/full` 集成 |

### Phase 4 — 辅助功能（2 天）

| 任务 | 产出 |
|------|------|
| 标签管理 | TagManageView + 标签 CRUD + 命名空间分组 |
| CVE 漏洞库 | VulnListView + 搜索筛选 |
| 导入向导 | PocImportView + 三步流程 |
| 导出功能 | 导出按钮 + 格式选择 |

### Phase 5 — 系统管理（2 天）

| 任务 | 产出 |
|------|------|
| 用户管理 | UserManageView + CRUD + 角色管理 |
| 审计日志 | AuditLogView + 筛选 + 详情展开 |
| 插件面板 | PluginListView + 按槽位分组 |

### Phase 6 — 收尾（1 天）

| 任务 | 产出 |
|------|------|
| 错误页 | 404 + 403 页面 |
| 空状态处理 | EmptyState 组件统一 |
| 加载态优化 | 骨架屏 / loading 状态 |
| 响应式适配 | 1080p+ 桌面端适配 |

---

## 附录

### A. 环境变量

```env
# .env.development
VITE_API_BASE_URL=/api/v1
VITE_APP_TITLE=VulnScope

# .env.production
VITE_API_BASE_URL=/api/v1
VITE_APP_TITLE=VulnScope
```

### B. 关键依赖清单

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.6.0",
    "axios": "^1.6.0",
    "@element-plus/icons-vue": "^2.3.0",
    "monaco-editor": "^0.47.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.4.0",
    "sass": "^1.71.0",
    "eslint": "^8.57.0",
    "prettier": "^3.2.0"
  }
}
```

### C. 后端 API 响应结构参考

```typescript
// types/api.ts
interface ApiResponse<T> {
  code: string      // "OK" 或错误码
  message: string   // "success" 或错误描述
  data: T           // 业务数据
  request_id: string
}

interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
```

### D. 数据模型类型定义（对应后端 Schema）

```typescript
// types/poc.ts
interface PocListItem {
  id: number
  uuid: string
  name: string
  title: string | null
  severity: string
  format: string
  source: string
  status: string
  author: string | null
  version: number
  tags: TagBrief[]
  cve_ids: string[]
  created_at: string | null
  updated_at: string | null
}

interface PocDetail extends PocListItem {
  description: string | null
  language: string | null
  content: string
  content_hash: string
  extra_meta: Record<string, any> | null
  categories: CategoryBrief[]
  created_by: number | null
  updated_by: number | null
}

interface PocVersion {
  id: number
  version_seq: number
  content_hash: string
  changed_by: number | null
  changed_at: string | null
}

interface PocCreatePayload {
  name: string
  title?: string
  description?: string
  severity: string
  format: string
  language?: string
  content: string
  author?: string
  source: string
  status: string
  cve_ids?: string[]
  tag_ids?: number[]
  category_ids?: number[]
  extra_meta?: Record<string, any>
}

// types/tag.ts
interface TagBrief {
  id: number
  namespace: string
  name: string
  color: string | null
}

interface TagItem extends TagBrief {
  description: string | null
  poc_count: number
}

// types/dashboard.ts
interface DashboardData {
  stats: {
    total_pocs: number
    total_active_pocs: number
    total_vulns: number
    total_tags: number
    total_categories: number
    total_authors: number
  }
  severity_distribution: Array<{ severity: string; count: number }>
  status_distribution: Array<{ status: string; count: number }>
  source_distribution: Array<{ source: string; count: number }>
  format_distribution: Array<{ format: string; count: number }>
  creation_timeline: Array<{ date: string; count: number }>
  top_tags: Array<{ tag_name: string; namespace: string; count: number }>
  top_authors: Array<{ author: string; count: number }>
  recent_activities: Array<{ poc_id: number; poc_name: string; action: string; timestamp: string }>
}
```

---

> 本文档对应后端 API 版本 v0.1.0，前端实现 Phase 1~6 总计约 15 天开发周期。