import type { ReactNode } from "react";
import clsx from "clsx";

type Props = {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "normal" | "up" | "down" | "warning";
};

export default function MetricCard({ label, value, hint, tone = "normal" }: Props) {
  return (
    <div className={clsx("metric-card", tone)}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}

