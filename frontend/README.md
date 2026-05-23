# 金价守望前端

这是金价守望的 React + TypeScript 前端，包含行情看板、分钟线图表、异动筛选、快捷交易、交易记录、提醒规则和系统设置页面。

## 环境要求

- Node.js 18+
- npm

## 安装

```powershell
cd frontend
npm install
```

## 开发运行

```powershell
npm run dev
```

默认访问地址：

```text
http://127.0.0.1:5173
```

开发环境下，Vite 会把 `/api` 代理到：

```text
http://127.0.0.1:8000
```

如需调整后端地址：

```powershell
$env:VITE_DEV_API_TARGET="http://127.0.0.1:8000"
npm run dev
```

## 构建

```powershell
npm run build
```

构建产物会输出到：

```text
../backend/app/static/frontend
```

后端启动后会自动托管这些静态文件，因此生产环境可以只暴露后端服务，通过同一个域名访问页面和 `/api`。

## 页面说明

- 行情看板：未登录也可查看实时行情、走势图和分钟线；登录后可查看异动、持仓和快捷交易。
- 交易记录：登录后维护买入/卖出流水。
- 提醒规则：登录后创建、编辑、启用、停用和删除提醒规则。
- 系统设置：登录后修改采集间隔、可视化范围、交易时间控制和钉钉通知。
- 登录页：输入系统密码后保存本地 token。

## 前端配置

前端默认通过相对路径访问 API：

```text
VITE_API_BASE=/api
```

生产部署通常不需要设置 `VITE_API_BASE`。只有当前端和后端部署在不同域名时，才需要在构建前指定完整 API 地址。

