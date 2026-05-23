# 金价守望 - 金价监控与交易提醒系统开发规格

## 1. 系统定位

系统名称：金价守望

用户可见语言：全系统面向个人使用，页面标题、导航、按钮、表单、图表标签、提醒规则名称、钉钉通知文案全部使用中文。技术依赖包名、接口路径、数据库字段和代码文件名可以保留英文命名，但不能直接暴露为前端用户文案。

系统目标：开发一套单用户使用的金价监控网站，用于实时抓取黄金价格、记录历史价格、维护个人买入/卖出流水、计算持仓均价，并在价格触达阈值、涨跌幅达到设定比例、短时间异动或窗口内最高最低价差达到阶梯阈值时，通过钉钉机器人发送提醒。

使用场景：

- 用户在浏览器中查看实时金价、分时图、持仓均价、浮动盈亏。
- 用户可以快捷记录买入、卖出，并自动更新持仓克重、持仓成本、当前市值。
- 系统在服务器后台按设定间隔自动刷新价格，不依赖前端页面是否打开。
- 系统根据用户配置的规则触发钉钉机器人通知。
- 系统面向单用户，但所有 API 与实时连接必须经过 token 校验。
- 系统中的所有配置项都应可在页面上可视化设置，避免要求用户直接修改配置文件。
- 行情可视化默认展示最近 48 小时的数据。
- 积存金只在交易时间内监控，交易时间为周一 09:00 至周六 02:00（中国时间）；其他时间后台采集器应暂停抓取、暂停提醒，并在状态接口中说明当前处于非交易时间。

非目标：

- 不做多用户体系、权限分组和角色管理。
- 不做日线、周线、月线等长期 K 线分析。
- 不做真实下单交易，仅做个人交易记录和提醒。
- 不承诺第三方金价接口的金融级可用性，接口异常时应降级展示最近一次成功价格。

## 2. 技术栈

### 2.1 后端

后端基座：FastAPI

推荐运行环境：

- Python 3.11+
- FastAPI
- Uvicorn
- SQLite

核心包：

- `fastapi`：HTTP API、依赖注入、鉴权依赖、WebSocket。
- `uvicorn[standard]`：ASGI 服务运行。
- `httpx`：异步请求金价接口和钉钉 Webhook。
- `pydantic` / `pydantic-settings`：请求响应模型、环境变量配置。
- `sqlalchemy`：数据库 ORM 与查询构建。
- `aiosqlite`：SQLite 异步驱动。
- `alembic`：数据库迁移，开发初期也可以先用自动建表，后续补迁移。
- `PyJWT`：JWT token 签发和校验。
- `pwdlib[argon2]`：登录密码哈希校验。
- `tenacity`：第三方接口请求重试。
- `orjson`：高性能 JSON 序列化，可用于 FastAPI 响应优化。
- `structlog` 或 `loguru`：结构化日志。
- `pytest`、`pytest-asyncio`、`respx`、`httpx`：自动化测试。
- `ruff`：代码检查和格式化。

钉钉签名不需要额外包，使用 Python 标准库：

- `time`
- `hmac`
- `hashlib`
- `base64`
- `urllib.parse`

### 2.2 前端

前端推荐：React + TypeScript + Vite

核心包：

- `react` / `react-dom`：前端基础框架。
- `vite`：前端开发和构建工具。
- `typescript`：静态类型。
- `react-router-dom`：页面路由。
- `@tanstack/react-query`：API 请求缓存、刷新和状态同步。
- `zustand`：轻量全局状态，保存认证状态、实时价格快照、用户偏好。
- `echarts` / `echarts-for-react`：价格折线图、分钟线图、成交点标记。
- `dayjs`：时间格式化和分钟桶计算展示。
- `lucide-react`：图标。
- `clsx`：条件 className 拼接。
- `tailwindcss`：样式系统，也可以用 CSS Modules；推荐 Tailwind 以便快速构建稳定后台界面。

前端请求：

- 普通 API 使用 `fetch` 封装或 `ky`。
- 实时行情优先使用 WebSocket。
- WebSocket 不可用时降级为定时轮询 `/api/market/latest`。
- 前端代码内部可以使用英文文件名、组件名和变量名；界面呈现给用户的所有文字必须为中文。

## 3. 总体架构

系统分为四层：

1. 数据采集层
   - 后端启动时创建价格刷新任务。
   - 按配置的刷新间隔请求金价接口。
   - 将成功获取的价格写入 SQLite。
   - 接口失败时记录错误，不覆盖最新成功价格。

2. 业务计算层
   - 计算当前持仓、均价、成本、市值、浮动盈亏。
   - 根据历史价格生成 5 分钟、10 分钟、15 分钟等分钟线。
   - 根据规则判断是否触发价格提醒、涨跌幅提醒、异动提醒、阶梯价差提醒。

3. 通知层
   - 通过钉钉自定义机器人发送卡片化通知，优先使用 actionCard，必要时降级为 Markdown。
   - 支持加签安全模式。
   - 支持提醒冷却时间，避免同一规则在短时间内刷屏。

4. 展示层
   - 登录页。
   - 行情可视化页。
   - 交易记录与持仓页。
   - 提醒规则页。
   - 系统配置页。

推荐目录结构：

```text
WatchGoldPrice/
  backend/
    app/
      main.py
      core/
        config.py
        security.py
        logging.py
      db/
        session.py
        models.py
        migrations/
      services/
        price_provider.py
        price_collector.py
        candle_service.py
        portfolio_service.py
        alert_engine.py
        dingtalk_notifier.py
      api/
        auth.py
        market.py
        candles.py
        trades.py
        alerts.py
        settings.py
        websocket.py
      schemas/
        auth.py
        market.py
        trade.py
        alert.py
        settings.py
    tests/
    pyproject.toml
  frontend/
    src/
      api/
      components/
      pages/
        LoginPage.tsx        # 页面显示为：登录
        DashboardPage.tsx    # 页面显示为：行情看板
        TradesPage.tsx       # 页面显示为：交易记录
        AlertsPage.tsx       # 页面显示为：提醒规则
        SettingsPage.tsx     # 页面显示为：系统设置
      stores/
      charts/
      styles/
      main.tsx
    package.json
  tips.md
  temp.py
```

## 4. 金价数据源

当前参考接口来自 `temp.py`：

```text
https://api.jdjygold.com/gw/generic/hj/h5/m/latestPrice
```

示例代码中的解析路径为：

```text
response["resultData"]["datas"]["price"]
```

开发要求：

- `temp.py` 只作为接口参考，不沿用其中的处理器结构。
- 后端必须重新实现为独立的 `PriceProvider`。
- 请求必须使用 `httpx.AsyncClient`。
- 价格字段必须转换为 `Decimal` 或数据库中的整数分单位，避免浮点误差。
- 每次抓取记录抓取时间、接口响应时间、原始价格、数据源名称。
- 接口异常、JSON 结构变化、价格为空、价格非数字时，必须记录日志并返回明确错误。

推荐数据模型：

```text
PriceTick
  id: integer primary key
  source: string, 默认 jd_gold
  price: decimal, 当前金价
  fetched_at: datetime, 请求完成时间
  remote_time: datetime nullable, 第三方接口若提供则保存
  raw_payload: json/text nullable, 可选，用于调试
  created_at: datetime
```

## 5. 后台刷新逻辑

刷新逻辑由 FastAPI lifespan 启动：

1. 应用启动。
2. 初始化数据库。
3. 读取系统配置中的刷新间隔 `refresh_interval_seconds`。
4. 创建 `asyncio.create_task(price_collector.run_forever())`。
5. 循环执行：
   - 判断当前是否处于积存金交易时间。
   - 如果不在交易时间内，则暂停本轮抓取和提醒，只更新采集器状态。
   - 请求金价接口。
   - 校验并规范化价格。
   - 写入 `price_ticks`。
   - 重新计算最新分钟线。
   - 执行提醒规则判断。
   - 通过 WebSocket 广播最新价格。
   - 等待当前刷新间隔。
6. 应用关闭时取消后台任务并关闭 HTTP client。

刷新间隔：

- 默认值：30 秒。
- 最小值：5 秒，防止过高频率请求第三方接口。
- 最大值：3600 秒。
- 用户可在配置页修改。
- 修改后下一轮刷新生效，不需要重启服务。

交易时间：

- 默认启用积存金交易时间控制。
- 交易时间按中国时间判断：周一 09:00 至周六 02:00。
- 周六 02:00 至周一 09:00 不抓取金价、不触发提醒、不发送价格类钉钉通知。
- 非交易时间内，采集状态为“已暂停”，状态接口返回下一次开盘时间。
- 配置页可提供开关，用于测试或特殊情况下临时关闭交易时间控制。

接口失败策略：

- 单次失败：记录错误，前端显示“最近更新失败”，继续展示最近成功价格。
- 连续失败达到 3 次：发送一次钉钉异常提醒。
- 异常提醒也需要冷却时间，默认 30 分钟。
- 成功恢复后发送一条恢复提醒，可选开启。

## 6. 分钟线与图表数据逻辑

不绘制日线，仅支持分钟级聚合。

支持周期：

- 1 分钟
- 5 分钟
- 10 分钟
- 15 分钟
- 30 分钟
- 60 分钟

聚合规则：

- 将 `fetched_at` 向下取整到对应分钟桶。
- 同一个分钟桶内：
  - `open`：第一条价格。
  - `high`：最高价格。
  - `low`：最低价格。
  - `close`：最后一条价格。
  - `count`：该桶内价格点数量。
- 前端可直接请求聚合后的 candle，也可以请求最近 tick 后由前端渲染折线。

推荐数据模型：

```text
PriceCandle
  id: integer primary key
  interval_seconds: integer
  bucket_start: datetime
  open: decimal
  high: decimal
  low: decimal
  close: decimal
  count: integer
  updated_at: datetime
```

图表要求：

- 实时价格主图用 ECharts 折线图。
- 分钟线用 ECharts candlestick 或 OHLC 风格图。
- 默认可视化范围为最近 48 小时。
- 支持切换 1/5/10/15/30/60 分钟。
- 支持 `tooltip` 查看具体时间和价格。
- 支持 `dataZoom` 拖动查看最近一段历史。
- 在图上标记买入点和卖出点。
- 在图上标记触发过提醒的时间点。

## 7. 交易记录与持仓逻辑

交易类型：

- 买入 `BUY`
- 卖出 `SELL`
- 手动修正 `ADJUST`，可选，开发第一版可以不做。

交易字段：

```text
Trade
  id: integer primary key
  side: BUY | SELL
  price: decimal
  grams: decimal
  fee: decimal default 0
  traded_at: datetime
  note: string nullable
  created_at: datetime
```

买入逻辑：

- 输入买入克重、买入单价、手续费、交易时间。
- 新持仓克重 = 原持仓克重 + 买入克重。
- 新持仓成本 = 原持仓成本 + 买入单价 * 买入克重 + 手续费。
- 新持仓均价 = 新持仓成本 / 新持仓克重。

卖出逻辑：

- 输入卖出克重、卖出单价、手续费、交易时间。
- 卖出克重不能大于当前持仓克重。
- 卖出时按当前均价扣减成本。
- 已实现盈亏 = 卖出收入 - 扣减成本 - 手续费。
- 若卖出后持仓为 0，则持仓成本归零，均价归零。
- 若卖出后仍有持仓，剩余均价保持不变。

当前持仓计算结果：

```text
PortfolioSnapshot
  holding_grams: decimal
  cost_amount: decimal
  average_price: decimal
  current_price: decimal
  market_value: decimal
  floating_pnl: decimal
  floating_pnl_percent: decimal
  realized_pnl: decimal
```

快捷操作：

- 前端在可视化页右侧或底部提供快捷买入/卖出面板。
- 默认价格填入当前实时价格。
- 用户只需输入克重和手续费即可快速提交。
- 提交后刷新持仓卡片、交易列表、图表买卖点。

## 8. 提醒规则设计

提醒规则分为五类。

通用要求：

- 所有提醒规则都必须能在页面上可视化创建、编辑、启用、停用和删除。
- 所有规则都必须支持冷却时间，防止重复刷屏。
- 所有规则都必须支持通知模板风格：简洁、标准、详细。
- 所有规则都必须支持站内颜色标识，默认普通为蓝色、重要为橙色、强提醒为红色。
- 规则编辑页面必须展示中文规则预览，让用户不用理解内部字段也能确认规则含义。

### 8.1 固定价格提醒

规则示例：

- 当前金价 >= 780 元/克时提醒。
- 当前金价 <= 720 元/克时提醒。

字段：

```text
AlertRule
  id: integer primary key
  name: string
  type: PRICE_ABOVE | PRICE_BELOW
  target_price: decimal
  enabled: boolean
  cooldown_seconds: integer
  last_triggered_at: datetime nullable
  created_at: datetime
  updated_at: datetime
```

触发逻辑：

- `PRICE_ABOVE`：最新价格大于等于目标价格。
- `PRICE_BELOW`：最新价格小于等于目标价格。
- 命中后检查冷却时间。
- 在冷却时间内不重复发送。

### 8.2 持仓涨跌幅提醒

用于提醒当前价格相对持仓均价的变化。

规则示例：

- 当前价较持仓均价上涨 5% 时提醒。
- 当前价较持仓均价下跌 3% 时提醒。

触发逻辑：

```text
change_percent = (current_price - average_price) / average_price * 100
```

- `POSITION_GAIN_PERCENT`：`change_percent >= target_percent`
- `POSITION_LOSS_PERCENT`：`change_percent <= -target_percent`
- 当前无持仓或均价为 0 时，该类规则不触发。

### 8.3 短时间异动提醒

用于捕捉短时间快速拉升或下跌。

规则示例：

- 5 分钟内涨跌幅超过 1% 时提醒。
- 10 分钟内价格波动超过 8 元/克时提醒。
- 近 5 分钟从最低点上涨超过 6 元/克时提醒。
- 近 5 分钟从最高点下跌超过 6 元/克时提醒。

字段：

```text
AlertRule
  type: VOLATILITY_PERCENT | VOLATILITY_AMOUNT | WINDOW_RANGE_AMOUNT
  window_seconds: integer
  target_percent: decimal nullable
  target_amount: decimal nullable
```

触发逻辑：

- 查询窗口期内最早价格和最新价格。
- 百分比异动：
  - `abs(latest - first) / first * 100 >= target_percent`
- 绝对值异动：
  - `abs(latest - first) >= target_amount`
- 窗口最高最低价差：
  - 查询窗口期内最高价 `window_high` 和最低价 `window_low`。
  - `window_high - window_low >= target_amount` 时触发。
  - 如果最新价格更接近窗口最高价，提醒文案描述为“短时拉升”；如果最新价格更接近窗口最低价，提醒文案描述为“短时回落”；无法判断时描述为“短时振幅扩大”。
- 通知内容要说明方向：快速上涨或快速下跌。

### 8.4 阶梯价差提醒

用于设置多档窗口价差阈值。它和普通“短时间异动提醒”的区别是：用户可以在同一条规则里配置多个价差档位，系统按档位逐级提醒，适合“近 5 分钟最高点和最低点价差达到 3 元、5 元、8 元分别提醒”的场景。

规则示例：

- 近 5 分钟最高价和最低价价差达到 3 元/克，发送普通提醒。
- 近 5 分钟最高价和最低价价差达到 5 元/克，发送重要提醒。
- 近 5 分钟最高价和最低价价差达到 8 元/克，发送强提醒。
- 近 10 分钟最高价和最低价价差达到 10 元/克，只提醒一次，直到价差回落到 6 元/克以下后才允许再次触发。

字段：

```text
AlertRule
  type: RANGE_STEP_AMOUNT
  window_seconds: integer
  step_thresholds: json
  reset_threshold_amount: decimal nullable
  trigger_mode: ONCE_PER_STEP | REPEAT_AFTER_RESET
```

`step_thresholds` 示例：

```json
[
  {
    "level": 1,
    "label": "轻微波动",
    "amount": "3.00",
    "color": "蓝色"
  },
  {
    "level": 2,
    "label": "明显波动",
    "amount": "5.00",
    "color": "橙色"
  },
  {
    "level": 3,
    "label": "剧烈波动",
    "amount": "8.00",
    "color": "红色"
  }
]
```

触发逻辑：

1. 查询窗口期内所有价格点。
2. 计算窗口最低价、窗口最高价、最高最低价差、最低价时间、最高价时间。
3. 找到所有满足 `price_range >= step.amount` 的档位。
4. 只触发当前达到的最高档位，避免一次刷新发送多条消息。
5. 如果 `trigger_mode = ONCE_PER_STEP`，同一窗口内同一档位只提醒一次。
6. 如果 `trigger_mode = REPEAT_AFTER_RESET`，必须等价差低于 `reset_threshold_amount` 后，才允许再次提醒。
7. 触发后在提醒事件中记录档位、窗口最高价、窗口最低价、价差和方向。

前端配置要求：

- 阶梯提醒必须在配置页或提醒规则页中可视化编辑。
- 用户可以新增、删除、拖拽排序档位。
- 每个档位包含：档位名称、价差金额、提醒颜色、是否启用。
- 页面实时展示当前规则的人类可读描述，例如：`近 5 分钟最高最低价差达到 5.00 元/克时，发送“明显波动”提醒`。
- 页面提供“用当前历史数据预览触发效果”的按钮，展示近一段数据中会命中的档位。

### 8.5 接口异常提醒

规则示例：

- 连续 3 次抓取失败时提醒。
- 抓取恢复时提醒。

触发逻辑：

- `price_collector` 维护连续失败次数。
- 达到阈值后发出异常通知。
- 恢复成功后将失败次数归零。

提醒事件记录：

```text
AlertEvent
  id: integer primary key
  rule_id: integer nullable
  rule_name: string
  event_type: string
  price: decimal nullable
  window_high: decimal nullable
  window_low: decimal nullable
  window_range: decimal nullable
  triggered_level: integer nullable
  message: text
  sent: boolean
  sent_at: datetime nullable
  error_message: text nullable
  created_at: datetime
```

## 9. 钉钉机器人通知

通知方式：钉钉自定义机器人 Webhook。

安全要求：

- 使用钉钉机器人加签模式。
- Webhook、secret、access token 等敏感配置只保存在后端。
- 前端配置页展示时只展示脱敏内容。

加签逻辑：

```text
timestamp = 当前毫秒时间戳
string_to_sign = timestamp + "\n" + secret
sign = url_encode(base64(hmac_sha256(string_to_sign, secret)))
webhook = 原始 webhook + "&timestamp=" + timestamp + "&sign=" + sign
```

通知格式：

- 优先使用钉钉 `actionCard` 消息，让通知更接近信息卡片：标题醒目、正文分区、底部可带一个打开系统的按钮。
- 如果当前机器人能力或实现阶段暂不支持 `actionCard`，则降级为 Markdown 消息。
- 钉钉自定义机器人 Markdown 本身不支持任意字体颜色，颜色效果不能依赖 HTML/CSS；可以通过 `actionCard` 的标题、按钮、分隔线、符号和清晰排版提升观感。
- 通知标题明确，例如：`金价守望提醒：价格突破目标价`
- 通知中不出现英文系统名，数据源也展示为中文名称，例如 `京东金融黄金价格`。
- 内容包含：
  - 当前价格
  - 触发规则
  - 目标阈值
  - 最高价、最低价、价差，适用于阶梯价差提醒
  - 当前涨跌幅
  - 持仓均价
  - 持仓克重
  - 浮动盈亏
  - 触发时间
  - 数据源

卡片化通知示例：

```markdown
金价守望提醒
价格突破目标价

当前金价：782.30 元/克
触发规则：当前价格已高于 780.00 元/克
提醒级别：重要

持仓概览
持仓均价：735.20 元/克
持仓克重：12.50 克
浮动盈亏：+588.75 元（+6.41%）

行情信息
较均价变化：+47.10 元/克
触发时间：2026-05-22 09:35:12
数据来源：京东金融黄金价格

按钮：打开金价守望
```

阶梯价差通知示例：

```markdown
金价守望提醒
短时波动达到“明显波动”档位

近 5 分钟最高最低价差：5.80 元/克
窗口最低价：776.50 元/克（09:31:08）
窗口最高价：782.30 元/克（09:35:12）
当前金价：781.90 元/克
波动方向：短时拉升后高位波动

持仓概览
持仓均价：735.20 元/克
浮动盈亏：+583.75 元（+6.35%）

触发规则：近 5 分钟价差达到 5.00 元/克
触发时间：2026-05-22 09:35:12
数据来源：京东金融黄金价格
```

发送策略：

- 通知发送失败时记录 `AlertEvent.error_message`。
- 通知发送失败不影响价格采集主流程。
- 钉钉发送设置 5 秒超时。
- 对网络错误使用最多 2 次重试。
- 每条规则必须有冷却时间，默认 10 分钟。
- 每条规则可配置通知模板风格：简洁、标准、详细。
- 提醒颜色在系统内用于卡片、标签和预览；发送到钉钉时根据钉钉机器人能力尽量映射为标题提示、按钮样式或文案标识，不能强依赖任意颜色渲染。

## 10. 认证与安全

系统是单用户使用，但必须防止未授权访问。

登录流程：

1. 用户首次打开浏览器进入登录页。
2. 输入系统密码。
3. 前端调用 `POST /api/auth/login`。
4. 后端校验密码哈希。
5. 校验成功后签发 JWT access token。
6. 前端保存 token，并在所有 API 请求中带上：

```text
Authorization: Bearer <token>
```

Token 要求：

- 默认有效期：12 小时。
- 支持手动退出，前端清除 token。
- JWT payload 包含：
  - `sub`: 固定值 `single-user`
  - `iat`
  - `exp`
  - `jti`

API 校验：

- 除 `/api/auth/login`、`/api/health` 外，所有 HTTP API 必须校验 token。
- WebSocket 连接也必须校验 token，可通过 query 参数或首条消息传入。
- 登录失败需要限流，建议同一 IP 1 分钟最多 5 次。
- CORS 只允许配置中的前端域名。

密码配置：

- 初始密码通过环境变量设置。
- 后端保存密码哈希，不保存明文。
- 推荐环境变量：

```text
APP_SECRET_KEY=
APP_PASSWORD_HASH=
JWT_EXPIRE_MINUTES=720
```

## 11. API 设计

统一前缀：`/api`

### 11.1 认证

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

### 11.2 行情

```text
GET /api/market/latest
GET /api/market/ticks?limit=500
GET /api/market/ticks?start=...&end=...
GET /api/market/status
```

返回 `latest` 示例：

```json
{
  "price": "782.30",
  "source": "jd_gold",
  "fetched_at": "2026-05-22T09:35:12+08:00",
  "collector_status": "ok",
  "failed_count": 0
}
```

### 11.3 分钟线

```text
GET /api/candles?interval=300&limit=300
GET /api/candles?interval=900&start=...&end=...
```

### 11.4 交易与持仓

```text
GET    /api/trades
POST   /api/trades
PUT    /api/trades/{trade_id}
DELETE /api/trades/{trade_id}
GET    /api/portfolio
```

### 11.5 提醒规则

```text
GET    /api/alerts/rules
POST   /api/alerts/rules
PUT    /api/alerts/rules/{rule_id}
DELETE /api/alerts/rules/{rule_id}
GET    /api/alerts/events
POST   /api/alerts/test-dingtalk
```

### 11.6 系统配置

```text
GET /api/settings
PUT /api/settings
```

可配置项：

- 刷新间隔。
- 历史价格保留天数。
- 可视化默认时间范围，默认最近 48 小时。
- 是否启用积存金交易时间控制。
- 交易时间时区，默认中国时间。
- 默认图表周期。
- 钉钉 Webhook。
- 钉钉 Secret。
- 是否启用钉钉通知。
- 是否启用接口异常恢复提醒。
- 通知模板风格：简洁、标准、详细。
- 阶梯提醒默认档位。
- 阶梯提醒默认窗口，例如近 5 分钟、近 10 分钟。
- 阶梯提醒重置阈值。
- 页面涨跌颜色偏好，默认中文金融习惯：上涨红色、下跌绿色。

### 11.7 实时连接

```text
WS /api/ws/market
```

推送消息类型：

```json
{
  "type": "price_tick",
  "payload": {
    "price": "782.30",
    "fetched_at": "2026-05-22T09:35:12+08:00"
  }
}
```

```json
{
  "type": "alert_event",
  "payload": {
    "rule_name": "突破 780",
    "message": "当前价格已达到 782.30 元/克"
  }
}
```

## 12. 前端页面设计

整体风格：

- 类型：专业型个人资产监控后台。
- 首屏不是营销页，登录后直接进入行情看板。
- 主色使用中性灰白背景，少量金色作为品牌强调。
- 涨价使用红色，跌价使用绿色，符合中文金融软件常见习惯。
- 卡片圆角不超过 8px。
- 图表区域清晰、密度适中，适合长时间查看。
- 避免大面积金色、深蓝、渐变背景和装饰性元素。
- 移动端重点保证查看价格、持仓和快捷买卖可用。
- 用户可见文案全部使用中文，不出现 `Dashboard`、`Settings`、`Alert`、`Trade` 等英文页面名称。
- 前端页面标题建议为：行情看板、交易记录、提醒规则、系统设置、登录。

### 12.1 登录页

元素：

- 系统名：金价守望。
- 密码输入框。
- 登录按钮。
- 登录失败提示。

交互：

- 回车提交。
- 登录成功跳转行情看板。
- token 过期时自动回到登录页。

### 12.2 行情可视化页

布局：

- 顶部状态栏：
  - 当前金价。
  - 最近更新时间。
  - 数据源状态。
  - 刷新间隔。
- 左侧主图表：
  - 实时折线图。
  - 分钟线切换。
  - 买入/卖出点标记。
  - 提醒事件标记。
- 右侧持仓卡片：
  - 当前持仓克重。
  - 持仓均价。
  - 当前市值。
  - 浮动盈亏。
  - 已实现盈亏。
- 右侧快捷交易：
  - 买入/卖出切换。
  - 克重输入。
  - 单价输入，默认当前价。
  - 手续费输入。
  - 备注输入。
  - 提交按钮。
- 底部最近价格列表：
  - 时间。
  - 价格。
  - 与上一条差值。
  - 与上一条涨跌幅。

### 12.3 交易记录页

功能：

- 列表展示买入、卖出记录。
- 支持新增、编辑、删除。
- 支持按类型过滤。
- 支持按时间排序。
- 顶部展示当前持仓汇总。

表格字段：

- 类型。
- 交易时间。
- 克重。
- 单价。
- 手续费。
- 成交金额。
- 备注。

### 12.4 提醒规则页

功能：

- 创建固定价格提醒。
- 创建持仓涨跌幅提醒。
- 创建短时间异动提醒。
- 创建阶梯价差提醒。
- 启用/停用规则。
- 设置冷却时间。
- 查看最近提醒事件。
- 发送钉钉测试消息。
- 可视化配置所有规则，不要求用户理解内部字段。

阶梯提醒编辑器：

- 使用“时间窗口 + 阶梯档位”的方式配置。
- 时间窗口使用分段控件或下拉框，例如近 1 分钟、近 5 分钟、近 10 分钟、近 15 分钟、近 30 分钟。
- 阶梯档位使用可编辑列表，每一行包含档位名称、价差金额、提醒颜色、开关、删除按钮。
- 提供新增档位按钮。
- 提供预览区域，用中文自然语言解释规则。
- 提供测试按钮，使用最近历史价格模拟是否会触发。
- 档位颜色只用于站内视觉标识和钉钉通知风格映射，不保证钉钉 Markdown 中原样显示颜色。

### 12.5 系统配置页

功能：

- 修改刷新间隔。
- 修改图表默认周期。
- 修改默认可视化范围，默认最近 48 小时。
- 查看当前是否处于积存金交易时间。
- 配置是否启用积存金交易时间控制。
- 配置钉钉机器人。
- 配置历史数据保留天数。
- 查看采集器状态。
- 配置提醒默认值，包括默认冷却时间、默认时间窗口、默认阶梯价差档位。
- 配置通知模板风格，包括简洁、标准、详细。
- 配置站内颜色习惯，默认上涨红色、下跌绿色。

敏感信息展示：

- Webhook 只显示前后少量字符，中间用 `******`。
- Secret 不回显明文，只支持重新填写覆盖。

## 13. 数据库表汇总

```text
settings
  key
  value
  updated_at

price_ticks
  id
  source
  price
  fetched_at
  remote_time
  raw_payload
  created_at

price_candles
  id
  interval_seconds
  bucket_start
  open
  high
  low
  close
  count
  updated_at

trades
  id
  side
  price
  grams
  fee
  traded_at
  note
  created_at
  updated_at

alert_rules
  id
  name
  type
  target_price
  target_percent
  target_amount
  window_seconds
  step_thresholds
  reset_threshold_amount
  trigger_mode
  notification_style
  cooldown_seconds
  enabled
  last_triggered_at
  created_at
  updated_at

alert_events
  id
  rule_id
  rule_name
  event_type
  price
  window_high
  window_low
  window_range
  triggered_level
  message
  sent
  sent_at
  error_message
  created_at
```

## 14. 配置文件与环境变量

推荐 `.env`：

```text
APP_NAME=金价守望
APP_ENV=development
APP_SECRET_KEY=change-me
APP_PASSWORD_HASH=
JWT_EXPIRE_MINUTES=720

DATABASE_URL=sqlite+aiosqlite:///./watchgold.db

PRICE_SOURCE=jd_gold
PRICE_REFRESH_INTERVAL_SECONDS=30
PRICE_REQUEST_TIMEOUT_SECONDS=5
PRICE_HISTORY_RETENTION_DAYS=30
MARKET_VISUALIZATION_WINDOW_HOURS=48
ACCUMULATION_GOLD_TRADING_HOURS_ENABLED=true
TRADING_TIMEZONE=Asia/Shanghai

DINGTALK_ENABLED=false
DINGTALK_WEBHOOK=
DINGTALK_SECRET=
DINGTALK_AT_MOBILES=
DINGTALK_IS_AT_ALL=false
DINGTALK_MESSAGE_STYLE=standard

DEFAULT_ALERT_COOLDOWN_SECONDS=600
DEFAULT_RANGE_WINDOW_SECONDS=300
DEFAULT_RANGE_STEPS=3:轻微波动,5:明显波动,8:剧烈波动

CORS_ORIGINS=http://localhost:5173
```

## 15. 后端关键服务说明

### 15.1 `PriceProvider`

职责：

- 调用第三方金价接口。
- 解析价格。
- 返回统一结构。

返回结构：

```text
PriceQuote
  source
  price
  fetched_at
  raw_payload
```

### 15.2 `PriceCollector`

职责：

- 后台循环刷新。
- 写入价格历史。
- 调用告警引擎。
- 广播 WebSocket 消息。
- 维护采集状态。

### 15.3 `CandleService`

职责：

- 将 tick 聚合为分钟线。
- 提供 candle 查询接口。
- 支持增量更新最新 bucket。

### 15.4 `PortfolioService`

职责：

- 校验交易记录。
- 计算当前持仓。
- 计算均价、浮动盈亏、已实现盈亏。
- 为告警通知提供持仓上下文。

### 15.5 `AlertEngine`

职责：

- 读取启用的提醒规则。
- 判断是否触发。
- 计算窗口最高价、最低价、价差和阶梯档位。
- 检查冷却时间。
- 写入提醒事件。
- 调用通知服务。

### 15.6 `DingTalkNotifier`

职责：

- 生成钉钉签名。
- 组装 actionCard 或 Markdown 通知。
- 发送 Webhook。
- 处理发送失败与重试。
- 根据规则级别和通知模板风格生成更美观的中文消息。

## 16. 开发阶段拆分

### 第一阶段：后端基础

- FastAPI 项目初始化。
- SQLite 数据库模型。
- 登录鉴权。
- 金价接口抓取。
- 后台刷新任务。
- 最新价格与历史价格 API。

验收标准：

- 启动后能自动抓取金价。
- `/api/market/latest` 能返回最近价格。
- 未登录访问业务 API 返回 401。
- 非积存金交易时间内，后台采集器暂停抓取并返回暂停状态。

### 第二阶段：前端看板

- React 项目初始化。
- 登录页。
- 行情看板。
- 实时价格展示。
- ECharts 折线图。
- WebSocket 或轮询刷新。

验收标准：

- 用户登录后可以看到当前金价。
- 图表随新价格自动更新。
- token 过期后回到登录页。
- 行情图默认只展示最近 48 小时。

### 第三阶段：交易与持仓

- 交易记录 CRUD。
- 快捷买入/卖出。
- 持仓均价计算。
- 浮动盈亏展示。
- 图表买卖点标记。

验收标准：

- 买入后持仓克重和均价正确。
- 卖出后持仓和已实现盈亏正确。
- 不能卖出超过持仓克重。

### 第四阶段：提醒与钉钉

- 提醒规则 CRUD。
- 固定价格提醒。
- 持仓涨跌幅提醒。
- 短时间异动提醒。
- 阶梯价差提醒。
- 提醒规则可视化编辑器。
- 钉钉加签发送。
- 钉钉卡片化通知。
- 提醒事件记录。

验收标准：

- 命中规则后能发送钉钉消息。
- 冷却时间内不会重复刷屏。
- 钉钉测试消息可从前端触发。
- 近 5 分钟最高最低价差达到配置档位时能触发对应阶梯提醒。
- 用户可以在页面上新增、删除、调整阶梯提醒档位。

### 第五阶段：配置与完善

- 系统配置页。
- 刷新间隔动态调整。
- 历史数据保留策略。
- 错误状态展示。
- 自动化测试。
- 部署文档。

验收标准：

- 修改刷新间隔后后台任务生效。
- 修改默认可视化范围后，行情和分钟线查询默认窗口生效。
- 接口异常时前端有状态提示。
- 关键业务逻辑有测试覆盖。

## 17. 测试要求

后端单元测试：

- 金价接口解析成功。
- 金价接口异常处理。
- 买入均价计算。
- 卖出盈亏计算。
- 固定价格提醒触发。
- 持仓涨跌幅提醒触发。
- 短时间异动提醒触发。
- 阶梯价差提醒触发。
- 阶梯价差提醒重置阈值生效。
- 积存金交易时间判断正确：周一 09:00 开始，周六 02:00 停止。
- 行情和分钟线默认只返回最近 48 小时数据。
- 钉钉签名生成。
- 未授权 API 返回 401。

前端测试建议：

- 登录表单。
- 行情页加载状态。
- 快捷买入/卖出表单校验。
- 提醒规则表单校验。
- 阶梯提醒编辑器新增、删除、预览档位。

手工验收：

- 启动后等待两轮刷新，确认数据库有价格记录。
- 修改刷新间隔，确认下一轮生效。
- 创建一个容易触发的价格规则，确认钉钉能收到通知。
- 断开网络或模拟接口失败，确认异常状态不影响页面基础展示。

## 18. 部署建议

开发环境：

- 后端：`uvicorn app.main:app --reload`
- 前端：`vite --host 0.0.0.0`

生产环境：

- 后端使用 `uvicorn` 或 `gunicorn + uvicorn worker`。
- 前端构建为静态文件，由 Nginx 或 FastAPI 静态服务托管。
- SQLite 数据库文件必须放在持久化目录。
- `.env` 不提交到代码仓库。
- 定期备份 SQLite 数据库。

Docker 可选：

- 一个后端容器。
- 一个前端静态服务容器。
- 或者后端同时托管前端构建产物，简化个人部署。

## 19. 关键验收清单

- 系统有明确名称：金价守望。
- 用户可见页面、按钮、表单、通知文案全部使用中文。
- 后端采用 FastAPI。
- 金价采集逻辑已重写，不依赖 `temp.py` 的处理器结构。
- 服务器后台能自动异步刷新价格。
- 前端能实时展示最新价格。
- 历史价格存入 SQLite。
- 支持配置刷新间隔。
- 默认可视化范围为最近 48 小时。
- 支持积存金交易时间控制，非交易时间暂停监控。
- 支持 1/5/10/15/30/60 分钟线。
- 支持买入、卖出、均价和盈亏计算。
- 支持固定价格提醒。
- 支持持仓涨跌幅提醒。
- 支持短时间异动提醒。
- 支持近 5 分钟等窗口内最高最低价差达到指定金额时提醒。
- 支持阶梯价差提醒，并可在页面上可视化配置多个档位。
- 支持钉钉机器人加签通知。
- 通知内容完整、美观、可读，优先使用卡片化消息。
- 浏览器首次使用必须登录。
- 所有业务 API 都有 token 校验。
- 配置页和可视化页明确区分。
- 前端有快捷买入/卖出入口。
- 系统异常时有日志和页面状态提示。
