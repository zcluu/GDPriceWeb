# 金价守望

金价守望是一套单用户使用的积存金价格监控与交易提醒系统。它会在后端定时采集黄金价格，保存最近行情，生成分钟线，记录个人买入/卖出流水，计算持仓均价和盈亏，并在价格触达规则时通过钉钉机器人发送提醒。

系统界面和通知文案以中文为主，适合部署在个人服务器上，通过一个域名同时访问前端页面和后端 API。

## 功能概览

- 实时金价、最近 48 小时走势和分钟 K 线。
- 未登录用户可以查看行情曲线，登录后可以查看异动、交易、持仓、提醒规则和系统设置。
- 个人买入/卖出记录、持仓克重、持仓均价、浮动盈亏和已实现盈亏计算。
- 固定价格、持仓涨跌幅、短时涨跌、窗口价差、阶梯价位等提醒规则。
- 异动类型筛选，刷新后保留上次选择。
- 钉钉机器人提醒，支持加签、行情摘要、规则列表和 actionCard 快捷按钮。
- 积存金交易时间控制：默认只在中国时间周一 09:00 至周六 02:00 监控。
- 前端构建产物可由 FastAPI 托管，部署后一个域名即可访问完整系统。

## 技术栈

- 后端：Python 3.11+、FastAPI、Uvicorn、SQLAlchemy、SQLite、httpx、python-dotenv。
- 前端：React、TypeScript、Vite、React Router、TanStack Query、Zustand、ECharts、Lucide React。
- 通知：钉钉自定义机器人 Webhook。

## 目录结构

```text
WatchGoldPrice/
  backend/
    app/                 # FastAPI 应用
    scripts/             # 自测与密码哈希脚本
    requirements.txt
    pyproject.toml
    .env.example
  frontend/
    src/                 # React 前端源码
    package.json
    vite.config.ts
  tips.md                # 系统开发规格说明
```

## 本地开发

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

开发环境可以先使用 `.env.example` 中的默认密码。公开部署前必须修改 `APP_SECRET_KEY`，并使用 `APP_PASSWORD_HASH` 替代明文 `APP_PASSWORD`。

生成密码哈希：

```powershell
cd backend
.\.venv\Scripts\python.exe .\scripts\hash_password.py
```

### 2. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

开发环境默认访问：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8000
```

Vite 开发代理会把 `/api` 转发到 `http://127.0.0.1:8000`。如需修改：

```powershell
$env:VITE_DEV_API_TARGET="http://127.0.0.1:8000"
npm run dev
```

## 单域名部署

前端构建时会输出到 `backend/app/static/frontend`，然后由 FastAPI 托管静态页面。

```powershell
cd frontend
npm install
npm run build
```

构建完成后启动后端：

```powershell
cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

部署时建议在反向代理中把域名转发到后端服务，例如：

```text
https://example.com        -> FastAPI 静态前端
https://example.com/api    -> FastAPI API
```

`.env` 中的 `APP_PUBLIC_URL` 应设置为实际访问域名，钉钉消息里的按钮链接会使用这个地址。

## 关键配置

后端配置来自 `backend/.env`。仓库只提交 `backend/.env.example`，不要提交真实 `.env`。

```text
APP_PUBLIC_URL=https://example.com
APP_SECRET_KEY=请替换为随机长密钥
APP_PASSWORD_HASH=通过 scripts/hash_password.py 生成
DATABASE_URL=sqlite:///./runtime/watchgold.db
DINGTALK_ENABLED=false
DINGTALK_WEBHOOK=
DINGTALK_SECRET=
MARKET_VISUALIZATION_WINDOW_HOURS=48
ACCUMULATION_GOLD_TRADING_HOURS_ENABLED=true
TRADING_TIMEZONE=Asia/Shanghai
```

## 自测

后端包含一个轻量自测脚本，覆盖认证、公开行情、异动鉴权、分钟线、交易、持仓和阶梯提醒。

```powershell
cd backend
.\.venv\Scripts\python.exe .\scripts\self_test.py
```

前端构建检查：

```powershell
cd frontend
npm run build
```

## 公开仓库注意事项

- 不要提交 `backend/.env`、数据库文件、日志、虚拟环境和 `node_modules`。
- 钉钉 Webhook、Secret、真实访问域名、密码哈希应只放在部署环境变量或服务器本地 `.env` 中。
- SQLite 数据库建议放在持久化目录，并定期备份。
- 第三方金价接口不保证金融级可用性，系统会尽量保留最近一次成功行情用于展示。

