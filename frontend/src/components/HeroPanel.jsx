import { motion } from "framer-motion";
import { Activity, ArrowUpRight, BrainCircuit, Radio, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { Badge } from "./ui/badge";
import { Card, CardContent } from "./ui/card";
import { Progress } from "./ui/progress";

function AnimatedNumber({ value, suffix = "" }) {
  return (
    <motion.span initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
      {value}
      {suffix}
    </motion.span>
  );
}

export function HeroPanel({ summary, apiState, activeScan }) {
  const isConnected = apiState === "connected";
  const posture = Math.max(8, Math.min(96, 100 - summary.critical_vulnerabilities * 12 - summary.total_vulnerabilities * 2));
  const activity = [
    ["Recon", activeScan?.status === "Running" ? "Watching repository surface" : "Ready"],
    ["Analysis", activeScan?.vulnerability_count ? `${activeScan.vulnerability_count} findings correlated` : "Signal baseline clean"],
    ["Posture", `${posture}% command confidence`]
  ];

  return (
    <section className="glass-panel scanline relative overflow-hidden px-4 py-5 sm:px-6 md:px-7 md:py-7">
      <div className="absolute inset-0 command-grid opacity-30" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/70 to-transparent" />
      <div className="relative grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(280px,320px)] xl:items-stretch">
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }} className="min-w-0 space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
              <span className={`h-2 w-2 rounded-full ${isConnected ? "animate-glowPulse bg-emerald-300" : "bg-amber-300"}`} />
              {isConnected ? "Live backend connected" : "Backend link pending"}
            </Badge>
            <Badge>
              <BrainCircuit size={14} />
              AI SOC control center
            </Badge>
          </div>

          <div>
            <p className="eyebrow">Autonomous security command</p>
            <h1 className="mt-3 max-w-[14ch] text-balance font-display text-[clamp(2rem,5.2vw,3.75rem)] font-bold leading-[1.04] text-white sm:max-w-[16ch] lg:max-w-[18ch]">
              Continuous repository defense, staged like a mission briefing.
            </h1>
            <p className="mt-4 max-w-[62ch] text-sm leading-7 text-slate-300 md:text-[0.96rem]">
              {isConnected
                ? "Recon, scanner telemetry, AI validation, remediation guidance, and executive posture are synchronized into one focused operations surface."
                : "Start the FastAPI service to replace standby telemetry with live scan activity and repository intelligence."}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["Scans", summary.total_scans, Activity],
              ["Findings", summary.total_vulnerabilities, ShieldCheck],
              ["Confidence", Math.round(summary.average_confidence * 100), Sparkles, "%"]
            ].map(([label, value, Icon, suffix], index) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.12 + index * 0.08 }}
                whileHover={{ y: -2, scale: 1.005 }}
                className="min-h-[116px] rounded-[20px] border border-white/10 bg-white/[0.06] p-4 backdrop-blur-xl"
              >
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-bold uppercase tracking-[0.18em]">{label}</span>
                  <Icon size={17} className="text-cyan-200" />
                </div>
                <p className="mt-3 font-display text-[clamp(1.6rem,3vw,2rem)] font-bold leading-none text-white">
                  <AnimatedNumber value={value} suffix={suffix || ""} />
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.1 }}>
          <Card className="h-full overflow-hidden border-cyan-300/15 bg-[#090d1b]/80">
            <div className="border-b border-white/10 bg-gradient-to-br from-cyan-400/14 via-indigo-500/12 to-fuchsia-500/12 p-5">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-100">Live posture</p>
                <Radio size={18} className="text-cyan-200" />
              </div>
              <div className="mt-5 flex items-end justify-between gap-4">
                <span className="font-display text-[clamp(3rem,6vw,3.75rem)] font-bold leading-none text-white">{isConnected ? posture : "--"}</span>
                <Badge className={isConnected ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : "border-amber-300/20 bg-amber-300/10 text-amber-100"}>
                  {isConnected ? `${summary.critical_vulnerabilities} critical` : "offline"}
                </Badge>
              </div>
              <Progress value={isConnected ? posture : 18} className="mt-5" />
            </div>
            <CardContent className="space-y-4 p-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Active operation</p>
                <p className="mt-2 truncate font-display text-[clamp(1.2rem,2vw,1.45rem)] font-bold leading-tight text-white">{activeScan?.repo_name || "No repository selected"}</p>
                <p className="mt-1 text-sm text-slate-400">{activeScan?.status || "Standby"} {activeScan?.progress ? `at ${activeScan.progress}%` : ""}</p>
              </div>
              <div className="accent-divider" />
              {activity.map(([label, detail], index) => (
                <motion.div key={label} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 + index * 0.08 }} className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/15 bg-cyan-300/10 text-cyan-100">
                    <Zap size={14} />
                  </span>
                  <div>
                    <p className="text-sm font-bold text-white">{label}</p>
                    <p className="text-xs text-slate-400">{detail}</p>
                  </div>
                </motion.div>
              ))}
              <Badge className="w-full justify-between border-white/10 py-2">
                Command state <ArrowUpRight size={14} />
              </Badge>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </section>
  );
}
