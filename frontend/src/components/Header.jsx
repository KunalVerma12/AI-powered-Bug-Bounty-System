import { Bell, Moon, ShieldCheck, Sun } from "lucide-react";

export function Header({ isDark, onToggleDark }) {
  return (
    <header className="glass-panel sticky top-4 z-30 flex items-center justify-between px-5 py-4 md:px-6">
      <div className="flex items-center gap-4">
        <div className="ig-gradient flex h-12 w-12 items-center justify-center rounded-[18px] text-white shadow-glow">
          <ShieldCheck size={24} />
        </div>
        <div>
          <p className="eyebrow">Autonomous SOC</p>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-display text-xl font-bold text-white">Bug Bounty Hunter</h1>
            <span className="feature-pill hidden sm:inline-flex">Enterprise command center</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleDark}
          aria-label={isDark ? "Switch to white theme" : "Switch to dark theme"}
          title={isDark ? "Switch to white theme" : "Switch to dark theme"}
          className="rounded-full border border-white/10 bg-white/[0.06] p-3 text-slate-100 transition hover:bg-white/[0.11]"
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button
          type="button"
          className="rounded-full border border-white/10 bg-white/[0.06] p-3 text-slate-100 transition hover:bg-white/[0.11]"
        >
          <Bell size={18} />
        </button>
      </div>
    </header>
  );
}
