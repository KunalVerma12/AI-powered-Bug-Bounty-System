import { cn } from "../../lib/utils";

export function Badge({ className = "", children, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.07] px-3 py-1 text-xs font-bold text-slate-200 backdrop-blur-xl",
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
