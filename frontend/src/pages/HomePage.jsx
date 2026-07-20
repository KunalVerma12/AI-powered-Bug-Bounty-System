import { useState } from "react";
import { motion } from "framer-motion";
import { Check, ChevronLeft, ChevronRight, Copy, FileSearch, GitBranch, RefreshCw, ShieldCheck, Sparkles, Target, TerminalSquare, Wrench } from "lucide-react";
import { HeroPanel } from "../components/HeroPanel";
import { SeverityChart } from "../components/SeverityChart";
import { StatsGrid } from "../components/StatsGrid";
import { VulnerabilityCard } from "../components/VulnerabilityCard";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { SectionTitle } from "../components/ui/SectionTitle";

function InfoSection({ title, children }) {
  return (
    <motion.article whileHover={{ y: -3 }} className="editorial-card px-5 py-5">
      <h3 className="font-display text-lg font-bold text-white">{title}</h3>
      <div className="mt-3 text-sm leading-7 text-slate-300">{children}</div>
    </motion.article>
  );
}

function BulletList({ items, emptyText }) {
  const values = items?.length ? items : [emptyText];
  return (
    <div className="space-y-3">
      {values.map((item) => (
        <div key={item} className="rounded-[18px] border border-white/10 bg-white/[0.055] px-4 py-3 text-sm leading-6 text-slate-300">
          {item}
        </div>
      ))}
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${
        active ? "ig-gradient text-white shadow-glow" : "border border-white/10 bg-white/[0.06] text-slate-300 hover:bg-white/[0.1]"
      }`}
    >
      {children}
    </button>
  );
}

function normalizeList(items, fallback) {
  return items?.length ? items.filter(Boolean) : [fallback];
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function buildRemediationPrompt({ activeScan, repoAnalysis, vulnerabilities, promptVersion }) {
  const repoName = activeScan?.repo_name || "the target repository";
  const techStack = normalizeList(repoAnalysis?.tech_stack, "Technology stack was not confidently identified. Inspect package manifests, lockfiles, framework config, and application entry points before editing.");
  const riskyFiles = uniqueValues(vulnerabilities.map((item) => item.file_path)).slice(0, 12);
  const attackSurfaces = uniqueValues(vulnerabilities.flatMap((item) => item.attack_surface_tags || []).concat(vulnerabilities.map((item) => item.tech_context))).slice(0, 10);
  const vulnerabilityLines = vulnerabilities.length
    ? vulnerabilities.slice(0, 12).map((item) => {
        const location = item.file_path ? `${item.file_path}:${item.line || "?"}` : "location unavailable";
        const confidence = Math.round((item.confidence || 0) * 100);
        return `- [${item.severity}] ${item.title} (${location})\n  Evidence: ${item.what_happened || item.description || "Scanner flagged a security-relevant implementation pattern."}\n  Fix direction: ${item.how_to_fix || item.fix_suggestion || "Implement the safest framework-native remediation and add a regression test."}\n  Confidence: ${confidence}%`;
      })
    : ["- No individual vulnerability records were attached. Perform a defensive review of authentication, input validation, secrets handling, dependency health, and authorization boundaries."];

  return `You are a senior application security engineer and AI coding assistant. Help remediate security issues in ${repoName}.

Repository overview:
- Repository: ${repoName}
- Project type: ${repoAnalysis?.project_type || "Unknown. Infer from the repository structure before making edits."}
- Summary: ${repoAnalysis?.overview_summary || repoAnalysis?.description || "No repository summary was generated. Start by reading the README, package manifests, routing layer, authentication code, and application entry points."}
- Current security posture: ${repoAnalysis?.security_posture || "Security posture was not fully classified. Treat externally reachable inputs, authentication, authorization, secrets, and dependency boundaries as high-priority review areas."}

Technologies detected:
${techStack.map((item) => `- ${item}`).join("\n")}

Vulnerabilities found:
${vulnerabilityLines.join("\n")}

Risky files and code areas to inspect first:
${normalizeList(riskyFiles, "No risky files were attached. Identify controllers/routes, auth middleware, config files, dependency manifests, and data-access layers.").map((item) => `- ${item}`).join("\n")}

Likely attack surfaces:
${normalizeList(attackSurfaces, "External inputs, authentication flows, authorization checks, secrets/configuration, dependency loading, and data persistence boundaries.").map((item) => `- ${item}`).join("\n")}

Architectural gaps:
${normalizeList(repoAnalysis?.risk_areas, "Look for missing trust boundaries, weak separation between request handling and sensitive operations, incomplete error handling, and insufficient centralized security controls.").map((item) => `- ${item}`).join("\n")}

Missing security protections:
${normalizeList(repoAnalysis?.missing_features, "Add or verify input validation, output encoding, authentication middleware, authorization checks, rate limiting, secure headers, secrets management, dependency scanning, audit logging, and regression tests.").map((item) => `- ${item}`).join("\n")}

Recommended improvements:
${normalizeList(repoAnalysis?.recommendations, "Prioritize framework-native fixes, remove unsafe patterns, upgrade risky dependencies, harden configuration defaults, and add tests that prove each vulnerability is no longer exploitable.").map((item) => `- ${item}`).join("\n")}

Requested implementation tasks:
1. Read the repository structure and confirm the framework, entry points, routing layer, auth middleware, config files, and dependency manifests.
2. Fix the listed vulnerabilities with minimal, idiomatic code changes. Do not mask scanner output with superficial guards.
3. Add validation at trust boundaries and prefer centralized middleware or shared helpers where the codebase already has that pattern.
4. Strengthen authentication and authorization checks before sensitive actions, admin paths, object access, or repository operations.
5. Harden secrets and configuration handling. Remove hardcoded secrets, unsafe defaults, verbose error leaks, and insecure debug behavior.
6. Review dependency risks in package manifests and lockfiles. Upgrade or replace vulnerable packages where practical.
7. Add focused regression tests or security tests for each fix, including negative cases for malicious input.
8. Return a concise patch summary listing changed files, risk reduced, tests added, and any remaining manual verification.

Constraints:
- Preserve existing architecture unless a security fix truly requires a small local refactor.
- Do not introduce unrelated features.
- Keep changes easy to review.
- Explain any uncertainty before editing high-risk code.

Prompt revision: ${promptVersion}`;
}

function AIPromptCard({ prompt, copied, onCopy, onRegenerate }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      className="editorial-card ig-outline overflow-hidden"
    >
      <div className="flex flex-col gap-4 border-b border-white/10 bg-gradient-to-r from-cyan-300/10 via-indigo-400/10 to-fuchsia-400/10 px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="rounded-2xl border border-cyan-300/15 bg-cyan-300/10 p-2.5 text-cyan-100">
              <TerminalSquare size={18} />
            </span>
            <div>
              <p className="eyebrow">AI remediation prompt</p>
              <h3 className="mt-1 font-display text-xl font-bold leading-tight text-white">Paste this into your coding AI</h3>
            </div>
          </div>
          <p className="mt-3 max-w-[68ch] text-sm leading-6 text-slate-300">
            One repository-aware prompt for ChatGPT, Cursor, Claude, or any coding assistant to begin practical security remediation.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button type="button" onClick={onCopy} className="h-10">
            {copied ? <Check size={15} /> : <Copy size={15} />}
            {copied ? "Copied" : "Copy Prompt"}
          </Button>
          <Button type="button" variant="outline" onClick={onRegenerate} className="h-10">
            <RefreshCw size={15} />
            Regenerate Prompt
          </Button>
        </div>
      </div>

      <div className="bg-slate-950/80 px-5 py-5">
        <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
          remediation.prompt
        </div>
        <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-[20px] border border-cyan-300/10 bg-[#070b16] p-4 font-mono text-[12.5px] leading-6 text-cyan-50 shadow-inner">
          <code>{prompt}</code>
        </pre>
      </div>
    </motion.article>
  );
}

export function HomePage({
  summary,
  vulnerabilities,
  selectedFindingIndex,
  onSelectVulnerability,
  onSelectFindingIndex,
  onNextFinding,
  onPreviousFinding,
  apiState,
  loading,
  activeScan,
  onExportReport
}) {
  const [viewTab, setViewTab] = useState("overview");
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("All");
  const [techFilter, setTechFilter] = useState("All");
  const [reviewFilter, setReviewFilter] = useState("All");
  const [sortBy, setSortBy] = useState("risk");
  const [promptVersion, setPromptVersion] = useState(1);
  const [promptCopied, setPromptCopied] = useState(false);
  const repoAnalysis = activeScan?.repo_analysis;
  const hasActiveScan = Boolean(activeScan);
  const techOptions = ["All", ...new Set(vulnerabilities.map((item) => item.tech_context).filter(Boolean))];
  const filteredVulnerabilities = vulnerabilities
    .filter((item) => (severityFilter === "All" ? true : item.severity === severityFilter))
    .filter((item) => (techFilter === "All" ? true : item.tech_context === techFilter))
    .filter((item) => (reviewFilter === "All" ? true : item.review_status === reviewFilter))
    .filter((item) =>
      search
        ? [item.title, item.what_happened, item.file_path, item.tech_context, item.tags.join(" ")]
            .join(" ")
            .toLowerCase()
            .includes(search.toLowerCase())
        : true
    )
    .sort((left, right) => {
      if (sortBy === "severity") {
        const order = { Critical: 4, High: 3, Medium: 2, Low: 1 };
        return (order[right.severity] || 0) - (order[left.severity] || 0);
      }
      if (sortBy === "confidence") {
        return (right.confidence || 0) - (left.confidence || 0);
      }
      return (right.cvss_score || 0) - (left.cvss_score || 0) || (right.exploitability_score || 0) - (left.exploitability_score || 0);
    });
  const selectedFinding = filteredVulnerabilities.find((item) => item.id === vulnerabilities[selectedFindingIndex]?.id) || filteredVulnerabilities[0] || null;
  const selectedFilteredIndex = selectedFinding ? filteredVulnerabilities.findIndex((item) => item.id === selectedFinding.id) : 0;
  const posture = Math.max(8, Math.min(96, 100 - summary.critical_vulnerabilities * 12 - summary.total_vulnerabilities * 2));
  const widgets = [
    ["Active scan", activeScan?.repo_name || "Standby", GitBranch],
    ["Posture meter", `${posture}%`, ShieldCheck],
    ["Priority", summary.critical_vulnerabilities ? `${summary.critical_vulnerabilities} critical` : "No critical", Target]
  ];
  const remediationPrompt = buildRemediationPrompt({ activeScan, repoAnalysis, vulnerabilities, promptVersion });

  async function handleCopyPrompt() {
    try {
      await navigator.clipboard.writeText(remediationPrompt);
      setPromptCopied(true);
      window.setTimeout(() => setPromptCopied(false), 1800);
    } catch (_error) {
      setPromptCopied(false);
    }
  }

  function handleRegeneratePrompt() {
    setPromptVersion((value) => value + 1);
    setPromptCopied(false);
  }

  return (
    <div className="space-y-6">
      <HeroPanel summary={summary} apiState={apiState} activeScan={activeScan} />

      <div className="grid gap-4 md:grid-cols-3">
        {widgets.map(([label, value, Icon], index) => (
          <motion.article
            key={label}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.07 }}
            whileHover={{ y: -4 }}
            className="editorial-card flex min-w-0 items-center justify-between gap-4 overflow-hidden px-5 py-4"
          >
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{label}</p>
              <p className="mt-2 truncate font-display text-xl font-bold text-white" title={String(value)}>{value}</p>
            </div>
            <div className="shrink-0 rounded-2xl border border-cyan-300/15 bg-cyan-300/10 p-3 text-cyan-100">
              <Icon size={18} />
            </div>
          </motion.article>
        ))}
      </div>

      <section className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <TabButton active={viewTab === "overview"} onClick={() => setViewTab("overview")}>
            Overview
          </TabButton>
          <TabButton active={viewTab === "findings"} onClick={() => setViewTab("findings")}>
            Findings
          </TabButton>
          <TabButton active={viewTab === "improvements"} onClick={() => setViewTab("improvements")}>
            Improvements
          </TabButton>
        </div>

        {viewTab === "overview" ? (
          <div className="space-y-6">
            {hasActiveScan ? (
              <section className="glass-panel mesh-panel ig-outline px-5 py-5">
                <SectionTitle
                  eyebrow="Repository briefing"
                  title={`About ${activeScan.repo_name}`}
                  description={repoAnalysis?.overview_summary || "A guided project briefing for the currently selected repository."}
                />

                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  <InfoSection title="1. Project description">
                    <p>{repoAnalysis?.description || "The scanner could not create a project description for this repository yet."}</p>
                    {repoAnalysis?.project_type ? (
                      <p className="mt-3">
                        <span className="font-semibold text-white">Project type:</span> {repoAnalysis.project_type}
                      </p>
                    ) : null}
                  </InfoSection>

                  <InfoSection title="2. Tech stack">
                    <BulletList
                      items={repoAnalysis?.tech_stack}
                      emptyText="The scanner did not confidently identify the tech stack for this repository."
                    />
                  </InfoSection>

                  <InfoSection title="3. Architecture overview">
                    <p>{repoAnalysis?.architecture || "Architecture notes are not available for this repository yet."}</p>
                  </InfoSection>

                  <InfoSection title="4. Security posture">
                    <p>{repoAnalysis?.security_posture || "Security posture analysis is not available for this repository yet."}</p>
                  </InfoSection>

                  <InfoSection title="5. Risk areas">
                    <BulletList items={repoAnalysis?.risk_areas} emptyText="No risk areas were highlighted for this repository." />
                  </InfoSection>

                  <InfoSection title="6. Trust boundaries">
                    <BulletList items={repoAnalysis?.trust_boundaries} emptyText="Trust boundary guidance was not generated for this repository." />
                  </InfoSection>

                  <InfoSection title="7. Top 3 things to fix first">
                    <BulletList items={repoAnalysis?.top_priorities} emptyText="No top-priority remediation list was generated for this repository." />
                  </InfoSection>
                </div>
              </section>
            ) : (
              <div className="editorial-card px-5 py-6 text-sm leading-6 text-slate-300">
                Start a scan or select one from Activity to see a repository-specific overview here.
              </div>
            )}

            <StatsGrid summary={summary} />
            <SeverityChart breakdown={summary.severity_breakdown} />
          </div>
        ) : null}

        {viewTab === "findings" ? (
          <section className="space-y-4">
            <SectionTitle
              eyebrow="Finding navigator"
              title="Browse every surfaced issue"
              description={
                vulnerabilities.length
                  ? `You have ${vulnerabilities.length} findings in this scan. Filter them by severity, tech surface, or review state, then open the full detail view when you want deeper evidence and remediation.`
                  : "Run a scan to populate the findings view."
              }
            />

            {hasActiveScan && vulnerabilities.length ? (
              <>
            <div className="editorial-card grid gap-3 px-5 py-5 md:grid-cols-2 xl:grid-cols-5">
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search findings"
                    className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
                  />
                  <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)} className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none">
                    {["All", "Critical", "High", "Medium", "Low"].map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                  <select value={techFilter} onChange={(event) => setTechFilter(event.target.value)} className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none">
                    {techOptions.map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                  <select value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)} className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none">
                    {["All", "Open", "Reviewed", "False Positive"].map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                  <select value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none">
                    <option value="risk">Sort by risk</option>
                    <option value="severity">Sort by severity</option>
                    <option value="confidence">Sort by confidence</option>
                  </select>
                </div>

                <div className="glass-panel mesh-panel ig-outline flex flex-wrap items-center justify-between gap-4 px-5 py-5">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.24em] text-slate-400">Current finding</p>
                    <h3 className="mt-2 text-2xl font-bold text-white">
                      Finding {selectedFilteredIndex + 1} of {filteredVulnerabilities.length}
                    </h3>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
                      {selectedFinding?.title || "No finding matches the current filters."}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const previous = filteredVulnerabilities[selectedFilteredIndex - 1];
                        if (previous) {
                          onSelectVulnerability(previous);
                        }
                      }}
                      disabled={selectedFilteredIndex === 0 || !selectedFinding}
                      className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm font-semibold text-slate-200 disabled:opacity-40"
                    >
                      <span className="inline-flex items-center gap-2">
                        <ChevronLeft size={16} />
                        Previous
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const next = filteredVulnerabilities[selectedFilteredIndex + 1];
                        if (next) {
                          onSelectVulnerability(next);
                        }
                      }}
                      disabled={selectedFilteredIndex >= filteredVulnerabilities.length - 1 || !selectedFinding}
                      className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm font-semibold text-slate-200 disabled:opacity-40"
                    >
                      <span className="inline-flex items-center gap-2">
                        Next
                        <ChevronRight size={16} />
                      </span>
                    </button>
                    {hasActiveScan ? (
                      <>
                        <button type="button" onClick={() => onExportReport("markdown")} className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm font-semibold text-slate-200">
                          Export MD
                        </button>
                        <button type="button" onClick={() => onExportReport("json")} className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm font-semibold text-slate-200">
                          Export JSON
                        </button>
                        <button type="button" onClick={() => onExportReport("pdf")} className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm font-semibold text-slate-200">
                          Export PDF
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {filteredVulnerabilities.map((vulnerability, index) => (
                    <button
                      key={vulnerability.id}
                      type="button"
                      onClick={() => onSelectVulnerability(vulnerability)}
                      className={`rounded-full px-4 py-2 text-sm font-semibold ${
                        vulnerability.id === selectedFinding?.id ? "ig-gradient text-white" : "border border-white/10 bg-white/[0.055] text-slate-300"
                      }`}
                    >
                      {index + 1}. {vulnerability.severity}
                    </button>
                  ))}
                </div>

                {selectedFinding ? <VulnerabilityCard vulnerability={selectedFinding} onSelect={onSelectVulnerability} /> : (
                  <div className="glass-panel px-5 py-6 text-sm text-slate-300">
                    No findings match the current filters. Try widening the search, severity, or tech-area selection.
                  </div>
                )}
              </>
            ) : (
              <div className="glass-panel px-5 py-6 text-sm text-slate-300">
                {loading
                  ? "Loading live findings from the backend."
                  : apiState === "disconnected"
                  ? "No findings can be shown because the frontend is not connected to the backend."
                  : !hasActiveScan
                  ? "Select a scan first to browse findings for that repository."
                  : "No major findings were surfaced for this repository. Good work. The scan did not identify any actionable vulnerabilities in this pass."}
              </div>
            )}
          </section>
        ) : null}

        {viewTab === "improvements" ? (
          <section className="space-y-4">
            {hasActiveScan ? (
              <section className="glass-panel ig-outline px-5 py-5">
                <SectionTitle
                  eyebrow="Security improvement roadmap"
                  title="What gets stronger next"
                  description={repoAnalysis?.improvements_summary || "Actionable architecture and implementation guidance for the currently selected repository."}
                />

                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  {[
                    ["Missing features", repoAnalysis?.missing_features, FileSearch, "No major missing controls were highlighted for this repository."],
                    ["Architectural gaps", repoAnalysis?.risk_areas, Target, "No architectural gaps were highlighted for this repository."],
                    ["Recommendations", repoAnalysis?.recommendations, Sparkles, "No follow-up recommendations were generated for this repository."],
                    ["Implementation guidance", repoAnalysis?.top_priorities, Wrench, "No implementation priority list was generated for this repository."]
                  ].map(([title, items, Icon, emptyText], index) => (
                    <motion.article
                      key={title}
                      initial={{ opacity: 0, y: 14 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.07 }}
                      whileHover={{ y: -5, scale: 1.01 }}
                      className="editorial-card px-5 py-5"
                    >
                      <div className="flex items-center gap-3">
                        <span className="rounded-2xl border border-cyan-300/15 bg-cyan-300/10 p-3 text-cyan-100">
                          <Icon size={18} />
                        </span>
                        <h3 className="font-display text-lg font-bold text-white">{title}</h3>
                      </div>
                      <div className="mt-4">
                        <BulletList items={items} emptyText={emptyText} />
                      </div>
                    </motion.article>
                  ))}
                </div>

                <div className="mt-4">
                  <AIPromptCard
                    prompt={remediationPrompt}
                    copied={promptCopied}
                    onCopy={handleCopyPrompt}
                    onRegenerate={handleRegeneratePrompt}
                  />
                </div>
              </section>
            ) : (
              <div className="glass-panel px-5 py-6 text-sm leading-6 text-slate-300">
                Improvements appear after a repository is scanned, so the guidance stays tied to the repo you are actually reviewing.
              </div>
            )}
          </section>
        ) : null}
      </section>
    </div>
  );
}
