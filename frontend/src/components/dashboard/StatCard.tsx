import { type ReactNode } from "react";

export function StatCard({
  label,
  value,
  note,
  icon,
  tone = "red",
}: {
  label: string;
  value: string | number;
  note: string;
  icon: ReactNode;
  tone?: "red" | "gold" | "green";
}) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className={`metric-icon ${tone}`}>{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
