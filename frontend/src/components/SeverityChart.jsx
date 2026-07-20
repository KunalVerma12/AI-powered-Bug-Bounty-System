import { motion } from "framer-motion";
import { Gauge } from "lucide-react";
import { Progress } from "./ui/progress";

const tones = {
  Low: "from-emerald-300 to-cyan-300",
  Medium: "from-amber-300 to-orange-300",
  High: "from-orange-300 to-rose-300",
  Critical: "from-rose-400 to-fuchsia-400"
};

export function SeverityChart({ breakdown }) {
  const entries = Object.entries(breakdown);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <section className="editorial-card ig-outline px-5 py-5">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Severity overview</p>
          <h3 className="mt-2 text-xl font-bold text-white">Exposure distribution</h3>
          <p className="mt-1 text-sm text-slate-400">Account-level vulnerability posture by operational priority.</p>
        </div>
        <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/10 p-3 text-cyan-100">
          <Gauge size={20} />
        </div>
      </div>
      <div className="space-y-4">
        {entries.map(([label, value], index) => (
          <motion.div key={label} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.08 }}>
            <div className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-200">
              <span>{label}</span>
              <span>{value}</span>
            </div>
            <Progress value={(value / max) * 100} indicatorClassName={`bg-gradient-to-r ${tones[label]}`} />
          </motion.div>
        ))}
      </div>
    </section>
  );
}
