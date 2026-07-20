import { motion } from "framer-motion";
import { BrainCircuit, FileSearch, Github, Radar, ShieldCheck, Sparkles, Wrench, Zap } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";

const presetMeta = {
  quick: "Fastest pass for focused app roots.",
  full: "Broad autonomous operation across code, config, dependencies, and secrets.",
  "config-only": "Target deployment, env, and settings files.",
  "dependency-only": "Focus manifests and lockfiles.",
  "secrets-only": "Focus credential-like files and sensitive config."
};

const presets = [
  ["quick", "Quick", Zap, "Fast"],
  ["full", "Full", Radar, "Deep"],
  ["config-only", "Config", ShieldCheck, "Hardening"],
  ["dependency-only", "Dependencies", FileSearch, "Supply"],
  ["secrets-only", "Secrets", BrainCircuit, "Leaks"]
];

const agents = [
  { name: "Recon Agent", description: "Maps repository structure and attack surface.", icon: Radar },
  { name: "Scanner Agent", description: "Runs static checks and evidence capture.", icon: FileSearch },
  { name: "AI Analyst", description: "Correlates risk, exploitability, and confidence.", icon: BrainCircuit },
  { name: "Fix Agent", description: "Drafts secure remediation paths.", icon: Wrench },
  { name: "Summary Agent", description: "Packages executive posture and next actions.", icon: ShieldCheck }
];

export function ScanForm({ repoUrl, setRepoUrl, scanPreset, setScanPreset, onSubmit, scanning, activeScan, disabled }) {
  const liveSteps = activeScan?.steps || [];
  const fallbackProgress = scanning ? [24, 42, 58, 34, 18] : [100, 100, 100, 100, 100];

  return (
    <section className="glass-panel overflow-hidden">
      <div className="border-b border-white/10 bg-gradient-to-r from-cyan-300/10 via-indigo-400/10 to-fuchsia-400/10 px-4 py-5 sm:px-6">
        <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
          <Sparkles size={14} />
          Launch autonomous security operation
        </Badge>
        <h2 className="mt-4 font-display text-[clamp(1.75rem,4vw,2.35rem)] font-bold leading-tight text-white">Stage a repository mission.</h2>
        <p className="mt-3 max-w-[62ch] text-sm leading-7 text-slate-300">
          Paste a repository URL, select the operating profile, and let the agent lane progress from reconnaissance to briefing without changing backend behavior.
        </p>
      </div>

      <div className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[0.95fr_1.05fr]">
        <form onSubmit={onSubmit} className="space-y-5">
          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-200">Repository URL</span>
            <div className="flex items-center gap-3 rounded-[22px] border border-cyan-300/20 bg-slate-950/55 px-4 py-4 shadow-glow transition focus-within:border-cyan-200/60">
              <Github size={19} className="text-cyan-200" />
              <input
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                placeholder="https://github.com/owner/repository"
                disabled={disabled}
                className="min-w-0 w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
              />
            </div>
          </label>

          <div>
            <span className="mb-3 block text-sm font-bold text-slate-200">Scan preset</span>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(128px,1fr))] gap-2.5">
              {presets.map(([id, label, Icon, eyebrow]) => (
                <button
                  key={id}
                  type="button"
                  disabled={disabled}
                  onClick={() => setScanPreset(id)}
                  className={`scan-preset-tile group min-h-[72px] overflow-hidden rounded-[18px] border px-3 py-3 text-left transition ${
                    scanPreset === id
                      ? "is-active border-cyan-300/50 bg-cyan-300/15 text-cyan-50 shadow-glow"
                      : "border-white/10 bg-white/[0.05] text-slate-300 hover:border-cyan-300/30 hover:bg-white/[0.08]"
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="rounded-xl border border-white/10 bg-white/[0.07] p-1.5 text-cyan-100">
                      <Icon size={15} />
                    </span>
                    <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500 group-hover:text-cyan-200">{eyebrow}</span>
                  </span>
                  <span className="mt-2 block truncate text-sm font-bold leading-none">{label}</span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs leading-6 text-slate-400">{presetMeta[scanPreset]}</p>
          </div>

          <Button type="submit" disabled={scanning || disabled} className="h-14 w-full rounded-[20px] text-sm">
            <Zap size={18} />
            {disabled ? "Sign in to scan" : scanning ? "Operation launching..." : "Launch operation"}
          </Button>
        </form>

        <div className="rounded-[22px] border border-white/10 bg-slate-950/45 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Live agent activity</p>
              <h3 className="mt-2 font-display text-[clamp(1.25rem,3vw,1.5rem)] font-bold leading-tight text-white">Staged scan progress</h3>
            </div>
            <Badge>{activeScan?.status || (scanning ? "Launching" : "Standby")}</Badge>
          </div>

          <div className="mt-5 grid gap-3">
            {agents.map(({ name, description, icon: Icon }, index) => {
              const matched = liveSteps.find((step) => step.name?.toLowerCase().includes(name.split(" ")[0].toLowerCase()));
              const progress = matched?.progress ?? (activeScan?.progress ? Math.min(100, Math.max(8, activeScan.progress - index * 12)) : fallbackProgress[index]);
              const state = progress >= 100 ? "Complete" : progress > 10 ? "Active" : "Queued";
              return (
                <motion.article
                  key={name}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.08 }}
                  whileHover={{ x: 3 }}
                  className="rounded-[18px] border border-white/10 bg-white/[0.055] px-4 py-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 gap-3">
                      <span className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-300/15 bg-cyan-300/10 text-cyan-100">
                        <Icon size={18} />
                      </span>
                      <div className="min-w-0">
                        <p className="font-bold text-white">{name}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-400">{matched?.summary || description}</p>
                      </div>
                    </div>
                    <Badge className={state === "Active" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : ""}>
                      {state === "Active" ? <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" /> : null}
                      {state}
                    </Badge>
                  </div>
                  <div className="mt-4 flex items-center gap-3">
                    <Progress value={progress} />
                    <span className="w-10 text-right text-xs font-bold text-slate-300">{Math.round(progress)}%</span>
                  </div>
                </motion.article>
              );
            })}
          </div>

        </div>
      </div>
    </section>
  );
}
