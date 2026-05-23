import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api } from "../api/endpoints";
import PageHeader from "../components/PageHeader";
import MetricCard from "../components/MetricCard";
import QuickTradeForm from "../components/QuickTradeForm";
import { fmtMoney, fmtTime, sideText, trendClass } from "../utils";

export default function TradesPage() {
  const queryClient = useQueryClient();
  const tradesQuery = useQuery({ queryKey: ["trades"], queryFn: api.trades });
  const portfolioQuery = useQuery({ queryKey: ["portfolio"], queryFn: api.portfolio });
  const latestQuery = useQuery({ queryKey: ["latest"], queryFn: api.latest });
  const deleteMutation = useMutation({
    mutationFn: api.deleteTrade,
    onSuccess: () => queryClient.invalidateQueries()
  });

  const trades = tradesQuery.data || [];
  const portfolio = portfolioQuery.data;

  return (
    <div className="page">
      <PageHeader title="交易记录" subtitle="维护买入、卖出流水，系统会自动重算均价和盈亏。" />

      <section className="metric-grid">
        <MetricCard label="持仓克重" value={`${fmtMoney(portfolio?.holding_grams)} 克`} />
        <MetricCard label="持仓均价" value={`${fmtMoney(portfolio?.average_price)} 元/克`} />
        <MetricCard
          label="浮动盈亏"
          value={`${fmtMoney(portfolio?.floating_pnl)} 元`}
          tone={trendClass(portfolio?.floating_pnl) as "up" | "down" | "normal"}
        />
        <MetricCard
          label="已实现盈亏"
          value={`${fmtMoney(portfolio?.realized_pnl)} 元`}
          tone={trendClass(portfolio?.realized_pnl) as "up" | "down" | "normal"}
        />
      </section>

      <section className="two-column">
        <div className="panel">
          <div className="panel-toolbar">
            <div>
              <h2>新增交易</h2>
              <p>默认使用当前实时金价，可手动覆盖。</p>
            </div>
          </div>
          <QuickTradeForm currentPrice={latestQuery.data?.price} />
        </div>
        <div className="panel wide">
          <div className="panel-toolbar">
            <div>
              <h2>流水明细</h2>
              <p>按交易时间倒序排列</p>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>类型</th>
                  <th>时间</th>
                  <th>克重</th>
                  <th>单价</th>
                  <th>手续费</th>
                  <th>备注</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.id}>
                    <td>
                      <span className={`pill ${trade.side === "BUY" ? "buy" : "sell"}`}>{sideText(trade.side)}</span>
                    </td>
                    <td>{fmtTime(trade.traded_at)}</td>
                    <td>{fmtMoney(trade.grams)} 克</td>
                    <td>{fmtMoney(trade.price)} 元</td>
                    <td>{fmtMoney(trade.fee)} 元</td>
                    <td>{trade.note || "-"}</td>
                    <td>
                      <button className="icon-button" onClick={() => deleteMutation.mutate(trade.id)} title="删除">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

