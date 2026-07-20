import { motion } from "framer-motion";
import { Radio, Shield, Sparkles } from "lucide-react";
import { Badge } from "../components/ui/badge";

export function AuthPage({
  authMode,
  setAuthMode,
  authForm,
  setAuthForm,
  authError,
  authLoading,
  onAuthSubmit,
  apiState
}) {
  const isRegister = authMode === "register";

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid w-full gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.section initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="glass-panel scanline overflow-hidden px-6 py-8 sm:px-8">
          <div className="flex items-center gap-4">
            <div className="ig-gradient flex h-16 w-16 items-center justify-center rounded-[24px] text-white shadow-glow">
              <Shield size={30} />
            </div>
            <div>
              <p className="eyebrow">Autonomous SOC</p>
              <h1 className="font-display text-4xl font-bold text-white">Bug Bounty Hunter</h1>
            </div>
          </div>

          <div className="mt-8 max-w-2xl space-y-5">
            <div>
              <p className="eyebrow">AI security workspace</p>
              <h2 className="mt-3 max-w-[15ch] text-balance font-display text-[clamp(2.35rem,6vw,3.9rem)] font-bold leading-[1.04] text-white">
                A darker, cleaner command desk for repo intelligence.
              </h2>
            </div>
            <p className="max-w-[58ch] text-base leading-8 text-slate-300">
              Sign in first, then step into a personal triage space where scanners, context, and remediation guidance feel less like raw tooling and more like a thoughtful engineering review.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <motion.div whileHover={{ y: -4 }} className="editorial-card px-5 py-5">
                <p className="text-sm font-bold text-white">Human-style repo briefings</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Get overview, findings, and improvements explained the way a senior engineer would walk a teammate through them.
                </p>
              </motion.div>
              <motion.div whileHover={{ y: -4 }} className="editorial-card px-5 py-5">
                <p className="text-sm font-bold text-white">User-isolated scan history</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Every scan, severity count, and remediation note stays attached to your account once you get inside.
                </p>
              </motion.div>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="feature-pill">Scan presets</span>
              <span className="feature-pill">AI rewrites</span>
              <span className="feature-pill">Tech-context tags</span>
              <span className="feature-pill">Exportable reports</span>
            </div>
          </div>
        </motion.section>

        <motion.section initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="glass-panel px-6 py-8 sm:px-8">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Access</p>
              <h2 className="font-display mt-2 text-[clamp(1.75rem,3vw,2rem)] font-bold leading-tight text-white">
                {isRegister ? "Create your workspace" : "Sign in to continue"}
              </h2>
            </div>
            <Badge className={apiState === "disconnected" ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"}>
              <Radio size={13} />
              {apiState === "disconnected" ? "Backend offline" : "Backend ready"}
            </Badge>
          </div>

          <div className="mt-6 flex gap-2">
            <button
              type="button"
              onClick={() => setAuthMode("login")}
              className={`rounded-full px-4 py-2 text-sm font-semibold ${!isRegister ? "ig-gradient text-white" : "border border-white/10 bg-white/[0.06] text-slate-300"}`}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => setAuthMode("register")}
              className={`rounded-full px-4 py-2 text-sm font-semibold ${isRegister ? "ig-gradient text-white" : "border border-white/10 bg-white/[0.06] text-slate-300"}`}
            >
              Register
            </button>
          </div>

          <form onSubmit={onAuthSubmit} className="mt-6 space-y-4">
            {isRegister ? (
              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-slate-200">Username</span>
                <input
                  value={authForm.username}
                  onChange={(event) => setAuthForm((current) => ({ ...current, username: event.target.value }))}
                  className="w-full rounded-[20px] border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
                  placeholder="kunaldev"
                />
                <span className="mt-2 block text-xs text-slate-400">Optional. If you skip this, we will use the first part of your email.</span>
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

            <button
              type="submit"
              disabled={authLoading || apiState === "disconnected"}
              className="ig-gradient flex w-full items-center justify-center gap-2 rounded-[24px] px-5 py-4 text-sm font-bold text-white disabled:opacity-70"
            >
              <Sparkles size={16} />
              {authLoading ? "Working..." : isRegister ? "Create account and enter app" : "Sign in and enter app"}
            </button>
          </form>
        </motion.section>
      </div>
    </div>
  );
}
