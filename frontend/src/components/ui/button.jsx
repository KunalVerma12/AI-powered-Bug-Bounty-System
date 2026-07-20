import { cn } from "../../lib/utils";

const variants = {
  default: "border-transparent bg-cyan-400 text-slate-950 shadow-glow hover:bg-cyan-300",
  ghost: "border-white/10 bg-white/[0.06] text-slate-100 hover:bg-white/[0.11]",
  outline: "border-white/10 bg-transparent text-slate-200 hover:border-cyan-300/40 hover:bg-cyan-300/10",
  destructive: "border-rose-400/20 bg-rose-500/15 text-rose-100 hover:bg-rose-500/25"
};

export function Button({ className = "", variant = "default", children, ...props }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[16px] border px-4 py-2.5 text-sm font-bold transition duration-300 disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant] || variants.default,
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
