import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Clock3, ExternalLink, ShieldAlert } from "lucide-react";
import { formatDate, statusTone } from "../lib/utils";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";

function getSeverityCounts(scan) {
  const counts = {
    Critical: 0,
    High: 0,
    Medium: 0,
    Low: 0
  };

  if (Array.isArray(scan.vulnerabilities) && scan.vulnerabilities.length) {
    scan.vulnerabilities.forEach((finding) => {
      if (counts[finding.severity] !== undefined) {
        counts[finding.severity] += 1;
      }
    });
    return counts;
  }

  const summary = scan.summary || {};
  return {
    Critical: Number(summary.critical ?? scan.critical_count ?? 0),
    High: Number(summary.high ?? scan.high_count ?? 0),
    Medium: Number(summary.medium ?? scan.medium_count ?? 0),
    Low: Number(summary.low ?? scan.low_count ?? 0)
  };
}

function getFindingTotal(scan, counts) {
  if (Array.isArray(scan.vulnerabilities) && scan.vulnerabilities.length) {
    return scan.vulnerabilities.length;
  }
  return Number(scan.summary?.total ?? scan.vulnerability_count ?? Object.values(counts).reduce((total, value) => total + value, 0));
}

export function ActivityList({ scans, onSelectScan }) {
  const [expanded, setExpanded] = useState(scans[0]?.id || null);

  return (
    <div className="grid gap-4">
      {scans.map((scan, index) => {
        const isExpanded = expanded === scan.id;
        const severityCounts = getSeverityCounts(scan);
        const findingTotal = getFindingTotal(scan, severityCounts);
        const confidence = Math.round((scan.average_confidence ?? scan.confidence ?? (findingTotal ? 0.82 : 0)) * 100);
        const severityItems = [
          ["Critical", severityCounts.Critical, "bg-rose-400"],
          ["High", severityCounts.High, "bg-orange-300"],
          ["Medium", severityCounts.Medium, "bg-amber-300"],
          ["Low", severityCounts.Low, "bg-emerald-300"]
        ];

        return (
          <motion.article
            key={scan.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06 }}
            whileHover={{ y: -2 }}
            className="editorial-card ig-outline overflow-hidden transition-shadow duration-300 hover:shadow-glow"
          >
            <button type="button" onClick={() => setExpanded(isExpanded ? null : scan.id)} className="w-full p-4 text-left sm:p-5">
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)] xl:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="max-w-full truncate font-display text-[clamp(1rem,2vw,1.25rem)] font-bold leading-snug text-white">{scan.repo_name}</h3>
                    <Badge>{scan.preset} preset</Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span className="inline-flex items-center gap-1.5"><Clock3 size={13} />{formatDate(scan.created_at)}</span>
                    <span className={statusTone(scan.status)}>{scan.status}</span>
                    <span>{findingTotal} findings</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {severityItems.map(([label, value, tone]) => (
                    <div key={label} className="flex min-h-[72px] flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.05] px-3 py-2.5">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className={`h-2 w-2 shrink-0 rounded-full ${tone}`} />
                        <span className="truncate text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{label}</span>
                      </div>
                      <p className="font-display text-xl font-bold leading-none text-white">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <Progress value={scan.status === "Running" || scan.status === "Queued" ? scan.progress : confidence} />
                <ChevronDown size={18} className={`text-slate-400 transition ${isExpanded ? "rotate-180" : ""}`} />
              </div>
            </button>

            {isExpanded ? (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="border-t border-white/10 p-4 sm:p-5">
                <div className="grid items-stretch gap-3 md:grid-cols-[1fr_1fr_auto]">
                  <div className="min-h-[104px] rounded-[18px] border border-white/10 bg-white/[0.045] p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Confidence score</p>
                    <p className="mt-2 font-display text-3xl font-bold text-white">{confidence}%</p>
                  </div>
                  <div className="min-h-[104px] rounded-[18px] border border-white/10 bg-white/[0.045] p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Operation status</p>
                    <p className={`mt-2 text-lg font-bold ${statusTone(scan.status)}`}>{scan.status}</p>
                  </div>
                  <div className="flex min-h-[104px] items-center">
                    <Button type="button" onClick={() => onSelectScan(scan.id)} className="h-12 w-full whitespace-nowrap md:w-auto">
                      <ExternalLink size={16} />
                      Open scan
                    </Button>
                  </div>
                </div>
                {scan.error_message ? (
                  <div className="mt-4 flex gap-2 rounded-[18px] border border-rose-400/20 bg-rose-500/10 p-4 text-sm text-rose-100">
                    <ShieldAlert size={17} />
                    {scan.error_message}
                  </div>
                ) : null}
              </motion.div>
            ) : null}
          </motion.article>
        );
      })}
    </div>
  );
}
