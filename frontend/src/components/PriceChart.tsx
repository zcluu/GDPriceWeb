import ReactECharts from "echarts-for-react";
import dayjs from "dayjs";
import type { AlertEvent, Candle, PriceTick, Trade } from "../api/types";
import { fmtMoney } from "../utils";

type Props = {
  ticks: PriceTick[];
  candles: Candle[];
  trades: Trade[];
  events: AlertEvent[];
  mode: "line" | "candle";
};

function movingAverage(values: number[], period: number) {
  return values.map((_, index) => {
    if (index < period - 1) return null;
    const total = values.slice(index - period + 1, index + 1).reduce((sum, value) => sum + value, 0);
    return Number((total / period).toFixed(2));
  });
}

export default function PriceChart({ ticks, candles, trades, events, mode }: Props) {
  const sortedTicks = [...ticks].reverse();
  const sortedCandles = [...candles].reverse();
  const candleAxis = sortedCandles.map((item) => dayjs(item.bucket_start).format("MM-DD HH:mm"));
  const candleValues = sortedCandles.map((item) => [
    Number(item.open),
    Number(item.close),
    Number(item.low),
    Number(item.high)
  ]);
  const closeValues = sortedCandles.map((item) => Number(item.close));
  const averageLines = [
    { name: "5段均线", period: 5, color: "#2f8a91" },
    { name: "10段均线", period: 10, color: "#b8872e" },
    { name: "20段均线", period: 20, color: "#315d91" }
  ];
  const tickTimes = new Set(sortedTicks.map((tick) => dayjs(tick.fetched_at).format("MM-DD HH:mm")));
  const buyMarks = trades
    .filter((trade) => trade.side === "BUY")
    .map((trade) => ({
      name: "买入",
      coord: [dayjs(trade.traded_at).format("MM-DD HH:mm"), Number(trade.price)],
      value: `买入 ${fmtMoney(trade.grams)} 克`
    }));
  const sellMarks = trades
    .filter((trade) => trade.side === "SELL")
    .map((trade) => ({
      name: "卖出",
      coord: [dayjs(trade.traded_at).format("MM-DD HH:mm"), Number(trade.price)],
      value: `卖出 ${fmtMoney(trade.grams)} 克`
    }));
  const eventMarks = events
    .filter((event) => event.price)
    .map((event) => {
      const exactTime = dayjs(event.created_at).format("MM-DD HH:mm");
      const nearestTick = sortedTicks.reduce<PriceTick | null>((nearest, tick) => {
        if (!nearest) return tick;
        const tickDiff = Math.abs(dayjs(tick.fetched_at).valueOf() - dayjs(event.created_at).valueOf());
        const nearestDiff = Math.abs(dayjs(nearest.fetched_at).valueOf() - dayjs(event.created_at).valueOf());
        return tickDiff < nearestDiff ? tick : nearest;
      }, null);
      const xValue = tickTimes.has(exactTime)
        ? exactTime
        : nearestTick
          ? dayjs(nearestTick.fetched_at).format("MM-DD HH:mm")
          : exactTime;
      return {
        name: "异动",
        coord: [xValue, Number(event.price)],
        value: event.triggered_level ? `${event.rule_name} ${event.triggered_level} 档` : event.rule_name,
        itemStyle: { color: event.event_type === "RANGE_STEP_AMOUNT" ? "#c63d3d" : "#b8872e" }
      };
    });

  const option =
    mode === "line"
      ? {
          grid: { left: 52, right: 24, top: 28, bottom: 58 },
          tooltip: { trigger: "axis" },
          xAxis: {
            type: "category",
            data: sortedTicks.map((tick) => dayjs(tick.fetched_at).format("MM-DD HH:mm")),
            boundaryGap: false,
            axisLine: { lineStyle: { color: "#d5dfd9" } },
            axisLabel: { color: "#68766d" }
          },
          yAxis: {
            type: "value",
            scale: true,
            axisLabel: { color: "#68766d" },
            splitLine: { lineStyle: { color: "#e7efea" } }
          },
          dataZoom: [{ type: "inside" }, { type: "slider", height: 22, bottom: 18 }],
          series: [
            {
              name: "金价",
              type: "line",
              smooth: true,
              symbol: "none",
              data: sortedTicks.map((tick) => Number(tick.price)),
              lineStyle: { color: "#2f8a91", width: 2 },
              areaStyle: { color: "rgba(47, 138, 145, .12)" },
              markPoint: {
                symbolSize: (value: unknown, params: { name?: string }) => (params.name === "异动" ? 62 : 54),
                label: { formatter: "{b}" },
                data: [...buyMarks, ...sellMarks, ...eventMarks]
              }
            }
          ]
        }
      : {
          legend: {
            top: 2,
            left: 8,
            itemWidth: 14,
            itemHeight: 8,
            textStyle: { color: "#68766d", fontSize: 12 }
          },
          grid: { left: 52, right: 24, top: 44, bottom: 58 },
          tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
          xAxis: {
            type: "category",
            data: candleAxis,
            axisLine: { lineStyle: { color: "#d5dfd9" } },
            axisLabel: { color: "#68766d" }
          },
          yAxis: {
            type: "value",
            scale: true,
            axisLabel: { color: "#68766d" },
            splitLine: { lineStyle: { color: "#e7efea" } }
          },
          dataZoom: [{ type: "inside" }, { type: "slider", height: 22, bottom: 18 }],
          series: [
            {
              name: "分钟线",
              type: "candlestick",
              data: candleValues,
              itemStyle: {
                color: "#b53232",
                color0: "#247b55",
                borderColor: "#b53232",
                borderColor0: "#247b55"
              }
            },
            ...averageLines.map((line) => ({
              name: line.name,
              type: "line",
              data: movingAverage(closeValues, line.period),
              smooth: true,
              symbol: "none",
              connectNulls: false,
              lineStyle: { color: line.color, width: 1.6 },
              emphasis: { focus: "series" }
            }))
          ]
        };

  if (!ticks.length && !candles.length) {
    return (
      <div className="empty-chart">
        <strong>暂无行情数据</strong>
        <span>后台采集到第一条价格后，这里会显示最近 48 小时走势。</span>
      </div>
    );
  }

  return <ReactECharts option={option} notMerge lazyUpdate className="price-chart" />;
}
