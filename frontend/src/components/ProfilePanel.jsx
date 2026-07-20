import { motion } from "framer-motion";
import { Activity, BrainCircuit, LogOut, ShieldCheck, Target, UserCircle2 } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";

export function ProfilePanel({
  summary,
  currentUser,
  authMode,
  setAuthMode,
  authForm,
  setAuthForm,
  authError,
  authLoading,
  onAuthSubmit,
  onLogout
}) {
  if (!currentUser) {
    return (
      <section className="glass-panel px-6 py-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
            <UserCircle2 size={32} />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">Sign in to isolate your scans</h3>
            <p className="text-sm text-slate-400">Your scan history, dashboard counts, and vulnerability reports are tied to a user account.</p>
          </div>
        </div>

        <div className="mt-6 flex gap-2">
          {["login", "register"].map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setAuthMode(mode)}
              className={`rounded-full px-4 py-2 text-sm font-semibold ${authMode === mode ? "ig-gradient text-white" : "bg-white/[0.06] text-slate-300"}`}
            >
              {mode === "login" ? "Login" : "Register"}
            </button>
          ))}
        </div>

        <form onSubmit={onAuthSubmit} className="mt-6 space-y-4">
          {authMode === "register" ? (
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-slate-200">Username</span>
              <input
                value={authForm.username}
                onChange={(event) => setAuthForm((current) => ({ ...current, username: event.target.value }))}
                className="w-full rounded-[20px] border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
                placeholder="operator"
              />
            </label>
          ) : null}
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-200">Email</span>
            <input
              value={authForm.email}
              onChange={(event) => setAuthForm((current) => ({ ...current, email: event.target.value }))}
              className="w-full rounded-[20px] border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
              placeholder="you@example.com"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-200">Password</span>
            <input
              type="password"
              value={authForm.password}
              onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))}
              className="w-full rounded-[20px] border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
              placeholder="Minimum 8 characters"
            />
          </label>
          {authError ? <p className="text-sm text-rose-300">{authError}</p> : null}
          <Button type="submit" disabled={authLoading} className="w-full">
            {authLoading ? "Working..." : authMode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>
      </section>
    );
  }

  const stats = [
    ["Owned scans", summary.total_scans, Activity],
    ["Open findings", summary.total_vulnerabilities, Target],
    ["Critical risk", summary.critical_vulnerabilities, ShieldCheck],
    ["Avg confidence", `${Math.round(summary.average_confidence * 100)}%`, BrainCircuit]
  ];

  return (
    <section className="glass-panel mesh-panel ig-outline overflow-hidden">
      <div className="border-b border-white/10 px-6 py-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="ig-gradient flex h-16 w-16 items-center justify-center rounded-[22px] text-xl font-extrabold text-white shadow-glow">
              {(currentUser.username || currentUser.email).slice(0, 2).toUpperCase()}
            </div>
            <div>
              <Badge>Operator workspace</Badge>
              <h3 className="mt-2 font-display text-3xl font-bold text-white">{currentUser.username}</h3>
              <p className="text-sm text-slate-400">{currentUser.email}</p>
            </div>
          </div>
          <Button type="button" variant="outline" onClick={onLogout}>
            <LogOut size={16} />
            Logout
          </Button>
        </div>
      </div>

      <div className="grid gap-4 p-6 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(([label, value, Icon], index) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            whileHover={{ y: -4 }}
            className="rounded-[20px] border border-white/10 bg-white/[0.055] p-4"
          >
            <Icon size={18} className="text-cyan-200" />
            <p className="mt-4 font-display text-3xl font-bold text-white">{value}</p>
            <p className="mt-1 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{label}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-4 px-6 pb-6 md:grid-cols-2">
        <div className="rounded-[20px] border border-white/10 bg-slate-950/35 p-5">
          <p className="eyebrow">Scan ownership</p>
          <h4 className="mt-2 text-xl font-bold text-white">User-isolated autonomous triage</h4>
          <p className="mt-3 text-sm leading-7 text-slate-400">Dashboard visibility and activity history are scoped to this operator account.</p>
        </div>
        <div className="rounded-[20px] border border-white/10 bg-slate-950/35 p-5">
          <div className="flex items-center justify-between">
            <p className="eyebrow">Activity health</p>
            <span className="text-sm font-bold text-white">{Math.round(summary.average_confidence * 100)}%</span>
          </div>
          <Progress value={Math.round(summary.average_confidence * 100)} className="mt-4" />
          <p className="mt-3 text-sm text-slate-400">Average confidence across owned scan findings.</p>
        </div>
      </div>
    </section>
  );
}
