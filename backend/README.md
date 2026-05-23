# 金价守望后端

这是金价守望的 FastAPI 后端，负责金价采集、历史行情保存、分钟线聚合、交易与持仓计算、提醒规则判断、钉钉通知和前端静态文件托管。

## 环境要求

- Python 3.11+
- SQLite
- Windows PowerShell、Linux shell 或同等命令行环境

## 安装

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Linux/macOS 可使用：

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

## 配置

主要配置位于 `.env`：

```text
APP_NAME=金价守望
APP_ENV=development
APP_PUBLIC_URL=http://localhost:8000
APP_SECRET_KEY=change-me
APP_PASSWORD_HASH=
APP_PASSWORD=change-me-in-development-only
DATABASE_URL=sqlite:///./runtime/watchgold.db
DINGTALK_ENABLED=false
DINGTALK_WEBHOOK=
DINGTALK_SECRET=
```

公开部署前请至少修改：

- `APP_PUBLIC_URL`：部署后的真实访问地址，用于钉钉消息按钮。
- `APP_SECRET_KEY`：JWT 签名密钥，必须使用随机长字符串。
- `APP_PASSWORD_HASH`：登录密码哈希，建议设置后移除或留空 `APP_PASSWORD`。
- `DINGTALK_WEBHOOK` / `DINGTALK_SECRET`：钉钉机器人配置。

生成密码哈希：

```powershell
.\.venv\Scripts\python.exe .\scripts\hash_password.py
```

## 启动

开发模式：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

生产模式示例：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如果已经执行过前端构建，后端会自动托管 `app/static/frontend` 下的页面文件。

## 鉴权边界

- 公开接口：`GET /api/health`、`POST /api/auth/login`、`GET /api/market/latest`、`GET /api/market/ticks`、`GET /api/market/status`、`GET /api/market/summary`、`GET /api/candles`。
- 登录后可用：交易记录、持仓、提醒规则、异动事件、系统设置、钉钉测试。

请求受保护接口时需要携带：

```text
Authorization: Bearer <token>
```

## 采集时间

积存金默认只在中国时间周一 09:00 至周六 02:00 监控。其他时间后台采集器会暂停抓取和提醒，状态接口会返回暂停状态以及下一次开盘时间。

前端行情和分钟线默认返回最近 48 小时数据，可通过 `.env` 或系统设置中的 `MARKET_VISUALIZATION_WINDOW_HOURS` 调整。

## 主要接口

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/market/latest`
- `GET /api/market/ticks`
- `GET /api/market/status`
- `GET /api/market/summary`
- `GET /api/candles`
- `GET /api/trades`
- `POST /api/trades`
- `GET /api/trades/portfolio`
- `GET /api/alerts/rules`
- `POST /api/alerts/rules`
- `PUT /api/alerts/rules/{rule_id}`
- `DELETE /api/alerts/rules/{rule_id}`
- `GET /api/alerts/events`
- `POST /api/alerts/test-dingtalk`
- `GET /api/settings`
- `PUT /api/settings`

## 自测

```powershell
.\.venv\Scripts\python.exe .\scripts\self_test.py
```

自测会使用 `backend/runtime/self_test.db`，该目录不会提交到仓库。
