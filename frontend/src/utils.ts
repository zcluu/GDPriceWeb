import dayjs from "dayjs";

export function fmtMoney(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (Number.isNaN(number)) return "-";
  return number.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

export function fmtTime(value: string | null | undefined) {
  if (!value) return "-";
  return dayjs(value).format("MM-DD HH:mm:ss");
}

export function statusText(status: string) {
  const map: Record<string, string> = {
    ok: "运行中",
    running: "运行中",
    paused: "非交易时间暂停",
    error: "接口异常",
    idle: "待启动",
    stopped: "已停止"
  };
  return map[status] || status;
}

export function trendClass(value: string | number | null | undefined) {
  const number = Number(value);
  if (Number.isNaN(number) || number === 0) return "neutral";
  return number > 0 ? "up" : "down";
}

export function sideText(side: string) {
  return side === "BUY" ? "买入" : "卖出";
}

export function intervalText(seconds: number) {
  if (seconds < 3600) return `${seconds / 60} 分钟`;
  return `${seconds / 3600} 小时`;
}

