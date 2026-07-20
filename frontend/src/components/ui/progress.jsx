import { cn } from "../../lib/utils";

export function Progress({ value = 0, className = "", indicatorClassName = "" }) {
  const width = Math.max(0, Math.min(100, Number(value) || 0));

  return (
    <div className={cn("h-2.5 overflow-hidden rounded-full bg-white/10", className)}>
      <div
        className={cn("h-full rounded-full bg-gradient-to-r from-cyan-300 via-indigo-400 to-fuchsia-400 transition-all duration-700", indicatorClassName)}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}
