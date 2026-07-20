import { motion } from "framer-motion";
import { AlertTriangle, BarChart3, Radar, ShieldAlert } from "lucide-react";

const statsMeta = [
  { key: "total_scans", label: "Total scans", icon: Radar, tone: "from-cyan-300/22 to-blue-500/8" },
  { key: "running_scans", label: "Running now", icon: BarChart3, tone: "from-emerald-300/18 to-cyan-500/8" },
  { key: "total_vulnerabilities", label: "Findings", icon: AlertTriangle, tone: "from-amber-300/18 to-fuchsia-500/8" },
  { key: "critical_vulnerabilities", label: "Critical", icon: ShieldAlert, tone: "from-rose-300/20 to-fuchsia-500/10" }
];

export function StatsGrid({ summary }) {
  return (
    <section className="space-y-3">
      <p className="eyebrow">Animated statistics</p>
      <div className="grid grid-cols-2 gap-4">
        {statsMeta.map(({ key, label, icon: Icon, tone }, index) => (
          <motion.article
            key={key}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            whileHover={{ y: -5, scale: 1.015 }}
            className={`editorial-card ig-outline overflow-hidden bg-gradient-to-br ${tone} px-5 py-5`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-400">{label}</p>
                <p className="mt-3 font-display text-3xl font-extrabold text-white">{summary[key]}</p>
              </div>
              <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/10 p-3 text-cyan-100 shadow-glow">
                <Icon size={18} />
              </div>
            </div>
            <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-indigo-300 to-fuchsia-300"
                initial={{ width: "8%" }}
                animate={{ width: `${Math.min(100, 18 + Number(summary[key] || 0) * 12)}%` }}
                transition={{ duration: 0.8, delay: 0.15 + index * 0.08 }}
              />
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
