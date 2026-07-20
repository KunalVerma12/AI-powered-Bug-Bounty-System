import { motion } from "framer-motion";
import { AlertTriangle, Bot, ChevronLeft, ChevronRight, Code2, FileWarning, Link2, ShieldAlert, Sparkles, Wrench, X } from "lucide-react";
import { SeverityBadge } from "./ui/SeverityBadge";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

function BriefingSection({ icon: Icon, title, children, accent = "text-cyan-100" }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-[20px] border border-white/10 bg-white/[0.055] px-5 py-5"
    >
      <div className={`flex items-center gap-2 text-sm font-bold ${accent}`}>
        <Icon size={16} />
        {title}
      </div>
      <div className="mt-3 text-sm leading-7 text-slate-300">{children}</div>
    </motion.article>
  );
}

export function DetailModal({ vulnerability, onClose, findingIndex = 0, findingTotal = 0, onNext, onPrevious, onUpdateReviewStatus }) {
  if (!vulnerability) {
    return null;
  }

  const impact =
    vulnerability.impact ||
    vulnerability.attack_impact ||
    `${vulnerability.severity} severity exposure in ${vulnerability.file_path || "the analyzed code path"} could let an attacker move from a small implementation weakness into a practical exploit path if the affected flow is reachable.`;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/75 p-3 backdrop-blur-md md:items-center md:p-6">
      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.98 }}
        className="glass-panel max-h-[92vh] w-full max-w-5xl overflow-y-auto"
      >
        <div className="sticky top-0 z-10 border-b border-white/10 bg-[#090d1b]/90 px-5 py-4 backdrop-blur-2xl md:px-7">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
                  <Sparkles size={14} />
                  AI security briefing
                </Badge>
                <Badge>{vulnerability.repo_name}</Badge>
              </div>
              <h3 className="font-display mt-3 max-w-3xl text-2xl font-bold leading-tight text-white md:text-4xl">{vulnerability.title}</h3>
              {findingTotal > 1 ? (
                <p className="mt-2 text-sm font-semibold text-slate-400">
                  Finding {findingIndex + 1} of {findingTotal}
                </p>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              {findingTotal > 1 ? (
                <>
                  <Button type="button" variant="ghost" onClick={onPrevious} disabled={findingIndex === 0} className="hidden sm:inline-flex">
                    <ChevronLeft size={16} />
                    Prev
                  </Button>
                  <Button type="button" variant="ghost" onClick={onNext} disabled={findingIndex >= findingTotal - 1} className="hidden sm:inline-flex">
                    Next
                    <ChevronRight size={16} />
                  </Button>
                </>
              ) : null}
              <Button type="button" variant="ghost" onClick={onClose} aria-label="Close">
                <X size={17} />
              </Button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 px-5 py-5 md:px-7 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <SeverityBadge severity={vulnerability.severity} />
              <Badge>{vulnerability.tool}</Badge>
              {vulnerability.tech_context ? <Badge>{vulnerability.tech_context}</Badge> : null}
              <Badge>{vulnerability.cwe}</Badge>
              <Badge>{Math.round((vulnerability.confidence || 0) * 100)}% confidence</Badge>
              <Badge>{vulnerability.review_status}</Badge>
            </div>

            <BriefingSection icon={AlertTriangle} title="What happened">
              {vulnerability.what_happened || vulnerability.description || "The scanner found a security-relevant implementation pattern that needs human review."}
            </BriefingSection>

            <BriefingSection icon={ShieldAlert} title="Why it matters" accent="text-amber-100">
              {vulnerability.why_it_matters || "This weakness can erode an important trust boundary, especially when the affected path handles external input, secrets, permissions, or user-controlled data."}
            </BriefingSection>

            <BriefingSection icon={FileWarning} title="Attack impact" accent="text-rose-100">
              {impact}
            </BriefingSection>

            <BriefingSection icon={Wrench} title="How to fix" accent="text-emerald-100">
              {vulnerability.how_to_fix || "Tighten the affected code path, validate assumptions close to the boundary, and add a regression test that proves the risky input no longer reaches the sink."}
            </BriefingSection>

            <BriefingSection icon={Code2} title="Example secure implementation">
              {vulnerability.example_fix ? (
                <pre className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/80 p-4 text-sm text-slate-100">
                  <code>{vulnerability.example_fix}</code>
                </pre>
              ) : (
                "No generated patch snippet is available yet. Use the remediation guidance above as the implementation target."
              )}
            </BriefingSection>

            <BriefingSection icon={Bot} title="AI explanation">
              <p>{vulnerability.ai_analysis || vulnerability.false_positive_hint || "The AI analyst did not add a separate explanation for this finding."}</p>
              {vulnerability.cwe_link ? (
                <a href={vulnerability.cwe_link} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-cyan-200">
                  <Link2 size={16} />
                  Open CWE reference
                </a>
              ) : null}
            </BriefingSection>

            <BriefingSection icon={Code2} title="Scanner evidence">
              <p className="mb-3">
                Located in <span className="font-semibold text-white">{vulnerability.file_path}:{vulnerability.line}</span>
                {vulnerability.analysis_source ? ` via ${vulnerability.analysis_source}` : ""}.
              </p>
              <pre className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/80 p-4 text-sm text-slate-100">
                <code>{vulnerability.snippet || "No source snippet was attached to this finding."}</code>
              </pre>
            </BriefingSection>
          </div>

          <aside className="space-y-4">
            <div className="rounded-[22px] border border-white/10 bg-slate-950/45 p-5">
              <p className="eyebrow">Risk telemetry</p>
              <div className="mt-4 space-y-3">
                {[
                  ["CVSS", vulnerability.cvss_score?.toFixed?.(1) || vulnerability.cvss_score || "n/a"],
                  ["Exploitability", `${Math.round((vulnerability.exploitability_score || 0) * 100)}%`],
                  ["Owner", vulnerability.component_owner || "Application Team"],
                  ["AI analyzed", vulnerability.ai_analyzed ? "Yes" : "No"]
                ].map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between border-b border-white/10 pb-3 last:border-0 last:pb-0">
                    <span className="text-sm text-slate-400">{label}</span>
                    <span className="text-sm font-bold text-white">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[22px] border border-white/10 bg-slate-950/45 p-5">
              <p className="eyebrow">Review actions</p>
              <div className="mt-4 grid gap-2">
                <Button type="button" variant="outline" onClick={() => onUpdateReviewStatus?.(vulnerability.id, "Reviewed")}>
                  Mark reviewed
                </Button>
                <Button type="button" variant="outline" onClick={() => onUpdateReviewStatus?.(vulnerability.id, "False Positive")}>
                  Mark false positive
                </Button>
                <Button type="button" variant="outline" onClick={() => onUpdateReviewStatus?.(vulnerability.id, "Open")}>
                  Reopen
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </motion.div>
    </div>
  );
}
