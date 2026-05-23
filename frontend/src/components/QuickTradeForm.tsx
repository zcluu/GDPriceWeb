import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowUpFromLine } from "lucide-react";
import { api } from "../api/endpoints";
import clsx from "clsx";

type Props = {
  currentPrice?: string | null;
};

export default function QuickTradeForm({ currentPrice }: Props) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [grams, setGrams] = useState("");
  const [price, setPrice] = useState(currentPrice || "");
  const [fee, setFee] = useState("0");
  const [note, setNote] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      api.createTrade({
        side,
        grams,
        price: price || currentPrice,
        fee,
        note
      }),
    onSuccess: () => {
      setGrams("");
      setNote("");
      queryClient.invalidateQueries();
    }
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <form className="quick-form" onSubmit={submit}>
      <div className="segmented">
        <button type="button" className={clsx(side === "BUY" && "active")} onClick={() => setSide("BUY")}>
          <ArrowDownToLine size={16} />
          买入
        </button>
        <button type="button" className={clsx(side === "SELL" && "active")} onClick={() => setSide("SELL")}>
          <ArrowUpFromLine size={16} />
          卖出
        </button>
      </div>
      <label>
        克重
        <input value={grams} onChange={(event) => setGrams(event.target.value)} placeholder="0.00" />
      </label>
      <label>
        单价
        <input
          value={price}
          onChange={(event) => setPrice(event.target.value)}
          placeholder={currentPrice || "当前金价"}
        />
      </label>
      <label>
        手续费
        <input value={fee} onChange={(event) => setFee(event.target.value)} placeholder="0.00" />
      </label>
      <label>
        备注
        <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="可选" />
      </label>
      {mutation.error && <div className="form-error">{mutation.error.message}</div>}
      <button className="primary-button full" disabled={mutation.isPending || !grams}>
        {mutation.isPending ? "正在记录" : side === "BUY" ? "记录买入" : "记录卖出"}
      </button>
    </form>
  );
}

