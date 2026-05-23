import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { api } from "../api/endpoints";
import PageHeader from "../components/PageHeader";
import { statusText } from "../utils";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: api.status, refetchInterval: 20000 });
  const [form, setForm] = useState<Record<string, string | boolean>>({});

  useEffect(() => {
    if (!settingsQuery.data) return;
    setForm({
      refresh_interval_seconds: String(settingsQuery.data.refresh_interval_seconds),
      history_retention_days: String(settingsQuery.data.history_retention_days),
      default_chart_interval_seconds: String(settingsQuery.data.default_chart_interval_seconds),
      market_visualization_window_hours: String(settingsQuery.data.market_visualization_window_hours),
      accumulation_gold_trading_hours_enabled: settingsQuery.data.accumulation_gold_trading_hours_enabled,
      trading_timezone: settingsQuery.data.trading_timezone,
      dingtalk_enabled: settingsQuery.data.dingtalk_enabled,
      dingtalk_message_style: settingsQuery.data.dingtalk_message_style,
      default_alert_cooldown_seconds: String(settingsQuery.data.default_alert_cooldown_seconds),
      default_range_window_seconds: String(settingsQuery.data.default_range_window_seconds),
      default_range_steps: settingsQuery.data.default_range_steps,
      rise_color: settingsQuery.data.rise_color,
      fall_color: settingsQuery.data.fall_color,
      dingtalk_webhook: "",
      dingtalk_secret: ""
    });
  }, [settingsQuery.data]);

  const mutation = useMutation({
    mutationFn: () =>
      api.updateSettings({
        ...form,
        refresh_interval_seconds: Number(form.refresh_interval_seconds),
        history_retention_days: Number(form.history_retention_days),
        default_chart_interval_seconds: Number(form.default_chart_interval_seconds),
        market_visualization_window_hours: Number(form.market_visualization_window_hours),
        default_alert_cooldown_seconds: Number(form.default_alert_cooldown_seconds),
        default_range_window_seconds: Number(form.default_range_window_seconds),
        dingtalk_webhook: form.dingtalk_webhook || undefined,
        dingtalk_secret: form.dingtalk_secret || undefined
      }),
    onSuccess: () => queryClient.invalidateQueries()
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  function setValue(key: string, value: string | boolean) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  const settings = settingsQuery.data;
  const status = statusQuery.data;

  return (
    <div className="page">
      <PageHeader title="系统设置" subtitle="刷新、交易时间、钉钉机器人和默认提醒行为都在这里维护。" />

      <section className="status-strip">
        <div className={`status-dot ${status?.collector_status || "idle"}`} />
        <span>采集状态：{statusText(status?.collector_status || "idle")}</span>
        <span>{status?.trading_hours_description}</span>
      </section>

      <form className="settings-grid" onSubmit={submit}>
        <div className="panel">
          <div className="panel-toolbar">
            <div>
              <h2>行情采集</h2>
              <p>积存金非交易时间会自动暂停监控</p>
            </div>
          </div>
          <div className="form-grid">
            <label>
              刷新间隔
              <input value={String(form.refresh_interval_seconds || "")} onChange={(e) => setValue("refresh_interval_seconds", e.target.value)} />
            </label>
            <label>
              历史保留天数
              <input value={String(form.history_retention_days || "")} onChange={(e) => setValue("history_retention_days", e.target.value)} />
            </label>
            <label>
              可视化范围
              <input value={String(form.market_visualization_window_hours || "")} onChange={(e) => setValue("market_visualization_window_hours", e.target.value)} />
            </label>
            <label>
              默认图表周期
              <input value={String(form.default_chart_interval_seconds || "")} onChange={(e) => setValue("default_chart_interval_seconds", e.target.value)} />
            </label>
          </div>
          <label className="switch-line">
            <input
              type="checkbox"
              checked={Boolean(form.accumulation_gold_trading_hours_enabled)}
              onChange={(e) => setValue("accumulation_gold_trading_hours_enabled", e.target.checked)}
            />
            启用积存金交易时间控制
          </label>
          <label>
            交易时区
            <input value={String(form.trading_timezone || "")} onChange={(e) => setValue("trading_timezone", e.target.value)} />
          </label>
        </div>

        <div className="panel">
          <div className="panel-toolbar">
            <div>
              <h2>钉钉通知</h2>
              <p>敏感配置不会回显明文</p>
            </div>
          </div>
          <label className="switch-line">
            <input
              type="checkbox"
              checked={Boolean(form.dingtalk_enabled)}
              onChange={(e) => setValue("dingtalk_enabled", e.target.checked)}
            />
            启用钉钉通知
          </label>
          <label>
            机器人地址
            <input
              value={String(form.dingtalk_webhook || "")}
              onChange={(e) => setValue("dingtalk_webhook", e.target.value)}
              placeholder={settings?.dingtalk_webhook_masked || "不修改则留空"}
            />
          </label>
          <label>
            加签密钥
            <input
              value={String(form.dingtalk_secret || "")}
              onChange={(e) => setValue("dingtalk_secret", e.target.value)}
              placeholder={settings?.dingtalk_secret_configured ? "已配置，不修改则留空" : "尚未配置"}
            />
          </label>
          <label>
            通知风格
            <select value={String(form.dingtalk_message_style || "standard")} onChange={(e) => setValue("dingtalk_message_style", e.target.value)}>
              <option value="simple">简洁</option>
              <option value="standard">标准</option>
              <option value="detailed">详细</option>
            </select>
          </label>
        </div>

        <div className="panel wide">
          <div className="panel-toolbar">
            <div>
              <h2>提醒默认值</h2>
              <p>创建新规则时使用这些默认习惯</p>
            </div>
          </div>
          <div className="form-grid four">
            <label>
              默认冷却时间
              <input value={String(form.default_alert_cooldown_seconds || "")} onChange={(e) => setValue("default_alert_cooldown_seconds", e.target.value)} />
            </label>
            <label>
              默认窗口
              <input value={String(form.default_range_window_seconds || "")} onChange={(e) => setValue("default_range_window_seconds", e.target.value)} />
            </label>
            <label>
              上涨颜色
              <input value={String(form.rise_color || "")} onChange={(e) => setValue("rise_color", e.target.value)} />
            </label>
            <label>
              下跌颜色
              <input value={String(form.fall_color || "")} onChange={(e) => setValue("fall_color", e.target.value)} />
            </label>
          </div>
          <label>
            默认阶梯档位
            <input value={String(form.default_range_steps || "")} onChange={(e) => setValue("default_range_steps", e.target.value)} />
          </label>
          {mutation.error && <div className="form-error">{mutation.error.message}</div>}
          <button className="primary-button">
            <Save size={16} />
            保存设置
          </button>
        </div>
      </form>
    </div>
  );
}

