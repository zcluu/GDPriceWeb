export type LatestPrice = {
  price: string | null;
  source: string | null;
  fetched_at: string | null;
  collector_status: string;
  failed_count: number;
  last_error: string | null;
};

export type MarketStatus = {
  collector_status: string;
  failed_count: number;
  last_error: string | null;
  last_success_at: string | null;
  next_trading_start_at: string | null;
  refresh_interval_seconds: number;
  visualization_window_hours: number;
  trading_hours_description: string;
};

export type MarketSummary = {
  current_price: string | null;
  previous_price: string | null;
  change_amount: string | null;
  change_percent: string | null;
  today_high: string | null;
  today_low: string | null;
  fetched_at: string | null;
};

export type PriceTick = {
  id: number;
  source: string;
  price: string;
  fetched_at: string;
  created_at: string;
};

export type Candle = {
  id: number;
  interval_seconds: number;
  bucket_start: string;
  open: string;
  high: string;
  low: string;
  close: string;
  count: number;
  updated_at: string;
};

export type Trade = {
  id: number;
  side: "BUY" | "SELL";
  price: string;
  grams: string;
  fee: string;
  traded_at: string;
  note: string | null;
  realized_pnl: string | null;
};

export type Portfolio = {
  holding_grams: string;
  cost_amount: string;
  average_price: string;
  current_price: string | null;
  market_value: string;
  floating_pnl: string;
  floating_pnl_percent: string;
  realized_pnl: string;
};

export type AlertRule = {
  id: number;
  name: string;
  type: string;
  target_price: string | null;
  target_percent: string | null;
  target_amount: string | null;
  window_seconds: number | null;
  step_thresholds: Array<Record<string, unknown>> | null;
  reset_threshold_amount: string | null;
  trigger_mode: string | null;
  notification_style: string;
  cooldown_seconds: number;
  enabled: boolean;
  last_triggered_at: string | null;
  state: Record<string, unknown> | null;
};

export type AlertEvent = {
  id: number;
  rule_id: number | null;
  rule_name: string;
  event_type: string;
  price: string | null;
  window_high: string | null;
  window_low: string | null;
  window_range: string | null;
  triggered_level: number | null;
  message: string;
  sent: boolean;
  sent_at: string | null;
  created_at: string;
};

export type SettingsPayload = {
  refresh_interval_seconds: number;
  history_retention_days: number;
  default_chart_interval_seconds: number;
  market_visualization_window_hours: number;
  accumulation_gold_trading_hours_enabled: boolean;
  trading_timezone: string;
  dingtalk_enabled: boolean;
  dingtalk_webhook_masked: string | null;
  dingtalk_secret_configured: boolean;
  dingtalk_message_style: string;
  default_alert_cooldown_seconds: number;
  default_range_window_seconds: number;
  default_range_steps: string;
  rise_color: string;
  fall_color: string;
};
