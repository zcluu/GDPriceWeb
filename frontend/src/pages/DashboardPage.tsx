import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { Activity, BellRing, Clock, Eye, EyeOff, LogIn, LogOut, RefreshCw, X } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import MetricCard from "../components/MetricCard";
import PageHeader from "../components/PageHeader";
import PriceChart from "../components/PriceChart";
import QuickTradeForm from "../components/QuickTradeForm";
import { fmtMoney, fmtTime, intervalText, statusText, trendClass } from "../utils";
import { useAuthStore } from "../store";

const intervals = [60, 300, 600, 900, 1800, 3600];

function eventTypeText(type: string) {
  const map: Record<string, string> = {
    PRICE_ABOVE: "高于目标",
    PRICE_BELOW: "低于目标",
    POSITION_GAIN_PERCENT: "持仓涨幅",
    POSITION_LOSS_PERCENT: "持仓跌幅",
    WINDOW_RANGE_AMOUNT: "窗口价差",
    RANGE_STEP_AMOUNT: "阶梯价位",
    COLLECTOR_ERROR: "采集异常"
  };
  return map[type] || type;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const isAuthed = useAuthStore((state) => state.isAuthed);
  const signOut = useAuthStore((state) => state.signOut);
  const [chartMode, setChartMode] = useState<"line" | "candle">("line");
  const [interval, setIntervalValue] = useState(300);
  const [quickTradeOpen, setQuickTradeOpen] = useState(false);
  const [visibleEventTypes, setVisibleEventTypes] = useState<string[] | null>(() => {
    const saved = localStorage.getItem("金价守望_visible_event_types");
    if (!saved) return null;
    try {
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : null;
    } catch {
      return null;
    }
  });
  const loginUrl = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`;

  const [latestQuery, statusQuery, summaryQuery, portfolioQuery, ticksQuery, candlesQuery, tradesQuery, eventsQuery] = useQueries({
    queries: [
      { queryKey: ["latest"], queryFn: api.latest, refetchInterval: 15000 },
      { queryKey: ["status"], queryFn: api.status, refetchInterval: 15000 },
      { queryKey: ["market-summary"], queryFn: api.marketSummary, refetchInterval: 15000 },
      { queryKey: ["portfolio"], queryFn: api.portfolio, refetchInterval: 15000, enabled: isAuthed },
      { queryKey: ["ticks"], queryFn: () => api.ticks(800), refetchInterval: 15000 },
      { queryKey: ["candles", interval], queryFn: () => api.candles(interval, 800), refetchInterval: 15000 },
      { queryKey: ["trades"], queryFn: api.trades, enabled: isAuthed },
      { queryKey: ["events"], queryFn: api.events, refetchInterval: 15000, enabled: isAuthed }
    ]
  });

  const dingActionMutation = useMutation({
    mutationFn: (enabled: boolean) => api.updateSettings({ dingtalk_enabled: enabled }),
    onSuccess: () => queryClient.invalidateQueries()
  });
  const applyDingAction = dingActionMutation.mutate;

  const latest = latestQuery.data;
  const status = statusQuery.data;
  const summary = summaryQuery.data;
  const portfolio = portfolioQuery.data;
  const ticks = ticksQuery.data || [];
  const candles = candlesQuery.data || [];
  const trades = tradesQuery.data || [];
  const events = eventsQuery.data || [];
  const eventTypeOptions = useMemo(
    () =>
      Array.from(new Set(events.map((event) => event.event_type))).map((type) => ({
        value: type,
        label: eventTypeText(type)
      })),
    [events]
  );
  const activeEventTypes = visibleEventTypes ?? eventTypeOptions.map((item) => item.value);
  const filteredEvents = events.filter((event) => activeEventTypes.includes(event.event_type));

  const lastChange = useMemo(() => {
    if (ticks.length < 2) return 0;
    return Number(ticks[0].price) - Number(ticks[1].price);
  }, [ticks]);

  useEffect(() => {
    const action = searchParams.get("ding_action");
    if (!action) return;
    if (!isAuthed) return;
    if (action === "disable_dingtalk") {
      applyDingAction(false);
    }
    if (action === "enable_dingtalk") {
      applyDingAction(true);
    }
    searchParams.delete("ding_action");
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams, isAuthed, applyDingAction]);

  function toggleEventType(type: string) {
    const currentTypes = visibleEventTypes ?? eventTypeOptions.map((item) => item.value);
    const next = currentTypes.includes(type)
      ? currentTypes.filter((item) => item !== type)
      : [...currentTypes, type];
    setVisibleEventTypes(next);
    localStorage.setItem("金价守望_visible_event_types", JSON.stringify(next));
  }

  return (
    <div className="page">
      <PageHeader
        title="行情看板"
        subtitle="最近 48 小时积存金价格、持仓和提醒状态集中在这里。"
        actions={
          <>
            <button className="ghost-button" onClick={() => window.location.reload()}>
              <RefreshCw size={16} />
              刷新
            </button>
            <button
              className="ghost-button"
              onClick={() => {
                if (isAuthed) {
                  signOut();
                  navigate("/dashboard");
                } else {
                  navigate(loginUrl);
                }
              }}
            >
              {isAuthed ? <LogOut size={16} /> : <LogIn size={16} />}
              {isAuthed ? "退出登录" : "登录"}
            </button>
          </>
        }
      />

      <section className="status-strip">
        <div className={`status-dot ${status?.collector_status || "idle"}`} />
        <span>{statusText(status?.collector_status || "idle")}</span>
        <span>{status?.trading_hours_description || "周一 09:00 至周六 02:00（中国时间）"}</span>
        {status?.next_trading_start_at && <span>下次开盘：{fmtTime(status.next_trading_start_at)}</span>}
      </section>

      <section className="metric-grid">
        <MetricCard
          label="当前金价"
          value={`${fmtMoney(latest?.price)} 元/克`}
          hint={`更新时间 ${fmtTime(latest?.fetched_at)}`}
        />
        <MetricCard
          label="涨跌幅"
          value={`${Number(summary?.change_percent || 0) >= 0 ? "+" : ""}${fmtMoney(summary?.change_percent)}%`}
          tone={trendClass(summary?.change_percent) as "up" | "down" | "normal"}
          hint={`${lastChange >= 0 ? "+" : ""}${fmtMoney(lastChange)} 元`}
        />
        <MetricCard
          label={isAuthed ? "持仓均价" : "今日最高"}
          value={`${fmtMoney(isAuthed ? portfolio?.average_price : summary?.today_high)} 元/克`}
          hint={isAuthed ? `${fmtMoney(portfolio?.holding_grams)} 克` : `最低 ${fmtMoney(summary?.today_low)} 元/克`}
        />
        <MetricCard
          label={isAuthed ? "浮动盈亏" : "今日最低"}
          value={`${fmtMoney(isAuthed ? portfolio?.floating_pnl : summary?.today_low)} ${isAuthed ? "元" : "元/克"}`}
          tone={isAuthed ? (trendClass(portfolio?.floating_pnl) as "up" | "down" | "normal") : "normal"}
          hint={isAuthed ? `${fmtMoney(portfolio?.floating_pnl_percent)}%` : `最高 ${fmtMoney(summary?.today_high)} 元/克`}
        />
      </section>

      <section className="dashboard-layout">
        <div className="chart-panel">
          <div className="panel-toolbar">
            <div>
              <h2>价格走势</h2>
              <p>默认最近 {status?.visualization_window_hours || 48} 小时</p>
            </div>
            <div className="toolbar-controls">
              <div className="segmented compact">
                <button className={chartMode === "line" ? "active" : ""} onClick={() => setChartMode("line")}>
                  折线
                </button>
                <button className={chartMode === "candle" ? "active" : ""} onClick={() => setChartMode("candle")}>
                  分钟线
                </button>
              </div>
              <select value={interval} onChange={(event) => setIntervalValue(Number(event.target.value))}>
                {intervals.map((item) => (
                  <option key={item} value={item}>
                    {intervalText(item)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <PriceChart ticks={ticks} candles={candles} trades={isAuthed ? trades : []} events={isAuthed ? filteredEvents : []} mode={chartMode} />
        </div>

        {isAuthed ? (
          <div className="dashboard-second-row">
          <section className="panel event-panel">
            <div className="panel-toolbar">
              <div>
                <h2>最近异动</h2>
                <p>提醒引擎记录的价格突破、短时波动和阶梯价差</p>
              </div>
              {eventTypeOptions.length > 0 && (
                <div className="event-filter">
                  {eventTypeOptions.map((item) => {
                    const visible = activeEventTypes.includes(item.value);
                    return (
                      <button
                        type="button"
                        key={item.value}
                        className={visible ? "active" : ""}
                        onClick={() => toggleEventType(item.value)}
                        title={visible ? "点击后隐藏" : "点击后显示"}
                      >
                        {visible ? <Eye size={13} /> : <EyeOff size={13} />}
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            {filteredEvents.length ? (
              <div className="event-grid">
                {filteredEvents.slice(0, 8).map((event) => (
                  <article className="event-card" key={event.id}>
                    <div className="event-icon">
                      <BellRing size={18} />
                    </div>
                    <div>
                      <strong>{event.rule_name}</strong>
                      <p>{event.triggered_level ? `触发 ${event.triggered_level} 档阶梯提醒` : "触发价格提醒"}</p>
                      <div className="event-meta">
                        <span>{fmtTime(event.created_at)}</span>
                        {event.price && <span>{fmtMoney(event.price)} 元/克</span>}
                        {event.window_range && <span>价差 {fmtMoney(event.window_range)} 元</span>}
                        <span>{event.sent ? "已发送" : "已记录"}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-events">
                <BellRing size={24} />
                <strong>{events.length ? "当前筛选下暂无异动" : "暂无异动记录"}</strong>
                <span>{events.length ? "可以在右上角重新显示被隐藏的异动类型。" : "当价格突破、短时波动或阶梯价差触发后，会在这里集中展示。"}</span>
              </div>
            )}
          </section>

          <aside className="panel portfolio-panel">
            <div className="panel-title">
              <Activity size={18} />
              持仓概览
            </div>
            <div className="mini-list">
              <span>当前市值</span>
              <strong>{fmtMoney(portfolio?.market_value)} 元</strong>
              <span>持仓成本</span>
              <strong>{fmtMoney(portfolio?.cost_amount)} 元</strong>
              <span>已实现盈亏</span>
              <strong className={trendClass(portfolio?.realized_pnl)}>{fmtMoney(portfolio?.realized_pnl)} 元</strong>
            </div>
          </aside>
        </div>
        ) : (
          <section className="panel public-note">
            <div className="panel-title">
              <BellRing size={18} />
              公开行情模式
            </div>
            <p>当前未登录，只展示金价曲线和公开行情摘要。登录后可以查看异动、持仓、交易记录和系统设置。</p>
            <button className="primary-button" onClick={() => navigate(loginUrl)}>
              <LogIn size={16} />
              登录查看完整版本
            </button>
          </section>
        )}
      </section>

      {isAuthed && <button
        className="quick-trade-toggle"
        onClick={() => setQuickTradeOpen((open) => !open)}
        aria-expanded={quickTradeOpen}
        aria-controls="quick-trade-panel"
      >
        <Clock size={18} />
        快捷交易
      </button>}

      {isAuthed && <aside
        id="quick-trade-panel"
        className={`panel quick-trade-float ${quickTradeOpen ? "open" : ""}`}
      >
        <div className="quick-trade-popover-title">
          <span>
            <Clock size={16} />
            快捷交易
          </span>
          <button
            type="button"
            className="icon-button quick-trade-close"
            onClick={() => setQuickTradeOpen(false)}
            title="关闭"
          >
            <X size={15} />
          </button>
        </div>
        <div className="panel-title quick-trade-static-title">
          <Clock size={18} />
          快捷交易
        </div>
        <QuickTradeForm currentPrice={latest?.price} />
      </aside>}
    </div>
  );
}
