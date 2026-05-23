import { request } from "./client";
import type {
  AlertEvent,
  AlertRule,
  Candle,
  LatestPrice,
  MarketSummary,
  MarketStatus,
  Portfolio,
  PriceTick,
  SettingsPayload,
  Trade
} from "./types";

export const api = {
  login: (password: string) =>
    request<{ access_token: string; token_type: string; expires_in_minutes: number }>(
      "/auth/login",
      { method: "POST", body: { password }, auth: false }
    ),
  me: () => request<{ display_name: string }>("/auth/me"),
  latest: () => request<LatestPrice>("/market/latest"),
  marketSummary: () => request<MarketSummary>("/market/summary"),
  status: () => request<MarketStatus>("/market/status"),
  ticks: (limit = 600) => request<PriceTick[]>(`/market/ticks?limit=${limit}`),
  candles: (interval = 300, limit = 600) =>
    request<Candle[]>(`/candles?interval=${interval}&limit=${limit}`),
  portfolio: () => request<Portfolio>("/trades/portfolio"),
  trades: () => request<Trade[]>("/trades"),
  createTrade: (body: unknown) => request<Trade>("/trades", { method: "POST", body }),
  deleteTrade: (id: number) => request<{ message: string }>(`/trades/${id}`, { method: "DELETE" }),
  rules: () => request<AlertRule[]>("/alerts/rules"),
  createRule: (body: unknown) => request<AlertRule>("/alerts/rules", { method: "POST", body }),
  updateRule: (id: number, body: unknown) =>
    request<AlertRule>(`/alerts/rules/${id}`, { method: "PUT", body }),
  deleteRule: (id: number) =>
    request<{ message: string }>(`/alerts/rules/${id}`, { method: "DELETE" }),
  events: () => request<AlertEvent[]>("/alerts/events"),
  testDingTalk: (message?: string) =>
    request<{ sent: boolean; error_message: string | null }>("/alerts/test-dingtalk", {
      method: "POST",
      body: { message }
    }),
  settings: () => request<SettingsPayload>("/settings"),
  updateSettings: (body: Partial<SettingsPayload> & Record<string, unknown>) =>
    request<SettingsPayload>("/settings", { method: "PUT", body })
};
