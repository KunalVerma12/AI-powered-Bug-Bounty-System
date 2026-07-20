import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowUpRight, Eye, Github, GitPullRequest, KeyRound, Lock, Play, RefreshCw, Search, ShieldCheck, Sparkles, Star, Unlock, Zap } from "lucide-react";
import { disconnectGitHub, fetchWorkspace, startGitHubConnect } from "../api/workspace";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { SectionTitle } from "../components/ui/SectionTitle";

const presetActions = [
  ["full", "Full Scan"],
  ["quick", "Quick Scan"],
  ["dependency-only", "Dependency Scan"],
  ["secrets-only", "Secrets Scan"]
];

function formatDate(value) {
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value));
}

function WorkspaceSkeleton() {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="editorial-card min-h-[260px] animate-pulse p-5">
          <div className="h-5 w-2/3 rounded-full bg-white/10" />
          <div className="mt-4 h-3 w-full rounded-full bg-white/10" />
          <div className="mt-2 h-3 w-4/5 rounded-full bg-white/10" />
          <div className="mt-8 grid grid-cols-3 gap-3">
            <div className="h-16 rounded-2xl bg-white/10" />
            <div className="h-16 rounded-2xl bg-white/10" />
            <div className="h-16 rounded-2xl bg-white/10" />
          </div>
        </div>
      ))}
    </div>
  );
}

const analyticsTone = {
  "Connected repos": "from-cyan-300/18 via-sky-400/8 to-transparent text-cyan-100",
  "Repos scanned": "from-emerald-300/16 via-cyan-400/8 to-transparent text-emerald-100",
  "Risky repos": "from-rose-300/16 via-fuchsia-400/8 to-transparent text-rose-100",
  "Avg posture": "from-violet-300/18 via-indigo-400/8 to-transparent text-violet-100",
  Coverage: "from-blue-300/18 via-cyan-400/8 to-transparent text-blue-100"
};

function AnalyticsCard({ label, value, icon: Icon }) {
  const tone = analyticsTone[label] || analyticsTone["Connected repos"];
  return (
    <motion.article
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ type: "spring", stiffness: 280, damping: 22 }}
      className={`analytics-tile editorial-card relative flex min-h-[126px] flex-col justify-between overflow-hidden bg-gradient-to-br ${tone} px-5 py-4`}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <p className="max-w-[8.5rem] text-[11px] font-bold uppercase leading-5 tracking-[0.24em] text-slate-400">{label}</p>
        <span className="shrink-0 rounded-2xl border border-white/10 bg-white/[0.075] p-2.5 shadow-inner">
          <Icon size={18} />
        </span>
      </div>
      <div className="min-w-0 text-left">
        <p className="font-display text-[clamp(2rem,3vw,2.45rem)] font-bold leading-none text-white">{value || 0}</p>
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/10">
          <div className="h-full w-2/3 rounded-full bg-current opacity-70" />
        </div>
      </div>
    </motion.article>
  );
}

function RepositoryCard({ repo, onLaunchScan, launchingRepoId, onViewFindings }) {
  const launching = launchingRepoId === repo.id;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      className="editorial-card ig-outline flex min-h-[640px] flex-col overflow-hidden transition-shadow duration-300 hover:soft-glow"
    >
      <div className="border-b border-white/10 bg-gradient-to-br from-cyan-300/8 via-indigo-400/8 to-fuchsia-400/8 p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="grid min-w-0 gap-2">
              <h3 className="min-w-0 truncate font-display text-[clamp(1.05rem,2vw,1.25rem)] font-bold leading-tight text-white" title={repo.full_name}>
                {repo.full_name}
              </h3>
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <Badge>{repo.visibility}</Badge>
                {repo.private ? <Lock size={15} className="shrink-0 text-amber-200" /> : <Unlock size={15} className="shrink-0 text-emerald-200" />}
              </div>
            </div>
            <p className="mt-2 line-clamp-2 min-h-[44px] text-sm leading-6 text-slate-300">
              {repo.description || "No repository description. Review README, routes, config, dependency manifests, and auth boundaries during profiling."}
            </p>
          </div>
          <a href={repo.html_url} target="_blank" rel="noreferrer" className="shrink-0 rounded-full border border-white/10 bg-white/[0.06] p-2 text-slate-200 hover:bg-white/[0.1]">
            <ArrowUpRight size={17} />
          </a>
        </div>

        <div className="mt-4 flex min-w-0 flex-wrap gap-2">
          <Badge>{repo.primary_language || "Unknown"}</Badge>
          <Badge><Star size={13} />{repo.stars}</Badge>
          <Badge>Updated {formatDate(repo.updated_at)}</Badge>
          {repo.latest_scan_status ? <Badge>{repo.latest_scan_status}</Badge> : null}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-5">
        <p className="line-clamp-3 min-h-[72px] text-sm leading-6 text-slate-300">{repo.ai_summary}</p>

        <div className="grid grid-cols-3 gap-3">
          {[
            ["Posture", `${repo.security_posture}%`],
            ["Findings", repo.findings_count],
            ["Attack", `${repo.attack_surface_score}%`]
          ].map(([label, value]) => (
            <div key={label} className="flex min-h-[78px] flex-col justify-center rounded-2xl border border-white/10 bg-white/[0.05] p-3 text-center">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</p>
              <p className="mt-2 truncate font-display text-xl font-bold text-white">{value}</p>
            </div>
          ))}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
            <span>Security posture</span>
            <span>{repo.scan_count} scans</span>
          </div>
          <Progress value={repo.security_posture} />
        </div>

        <div className="min-h-[142px] rounded-[18px] border border-white/10 bg-slate-950/35 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-100">AI repository profile</p>
          <div className="mt-3 grid gap-2 text-xs leading-5 text-slate-400">
            <p className="line-clamp-2">{repo.profile.auth_quality}</p>
            <p className="line-clamp-2">{repo.profile.config_exposure_risk}</p>
            <p className="line-clamp-2">{repo.profile.dependency_risk}</p>
          </div>
        </div>

        <div className="mt-auto grid gap-2 sm:grid-cols-2">
          {presetActions.map(([preset, label]) => (
            <Button key={preset} type="button" variant={preset === "full" ? "default" : "outline"} disabled={launching} onClick={() => onLaunchScan(repo, preset)} className="h-11">
              {launching && preset === "full" ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
              {label}
            </Button>
          ))}
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          <Button type="button" variant="ghost" disabled={!repo.latest_scan_id} onClick={() => onViewFindings(repo.latest_scan_id)} className="h-10 w-full">
            <Eye size={15} />
            View Findings
          </Button>
          <a href={repo.html_url} target="_blank" rel="noreferrer" className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-[16px] border border-white/10 bg-white/[0.06] px-4 text-sm font-bold text-slate-100 transition hover:bg-white/[0.11]">
            <Github size={15} />
            Open Repository
          </a>
        </div>
      </div>
    </motion.article>
  );
}

export function WorkspacePage({ notice, onDismissNotice, onLaunchRepositoryScan, onSelectScan }) {
  const [workspace, setWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [launchingRepoId, setLaunchingRepoId] = useState("");

  async function load(refresh = false) {
    try {
      setError("");
      refresh ? setRefreshing(true) : setLoading(true);
      const data = await fetchWorkspace(refresh);
      setWorkspace(data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Workspace could not be loaded.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    load(false);
  }, []);

  async function handleConnectGitHub() {
    try {
      setError("");
      const start = await startGitHubConnect();
      window.location.href = start.auth_url;
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "GitHub OAuth could not be started.");
    }
  }

  async function handleDisconnectGitHub() {
    try {
      await disconnectGitHub();
      await load(false);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "GitHub could not be disconnected.");
    }
  }

  async function handleLaunch(repo, preset) {
    try {
      setLaunchingRepoId(repo.id);
      await onLaunchRepositoryScan(repo.id, preset);
      await load(false);
    } finally {
      setLaunchingRepoId("");
    }
  }

  const repositories = useMemo(() => {
    const values = workspace?.repositories || [];
    if (!query.trim()) {
      return values;
    }
    const normalized = query.toLowerCase();
    return values.filter((repo) => [repo.full_name, repo.description, repo.primary_language, repo.visibility].join(" ").toLowerCase().includes(normalized));
  }, [query, workspace?.repositories]);

  const connection = workspace?.connection;
  const analytics = workspace?.analytics;

  return (
    <div className="space-y-6">
      <SectionTitle
        eyebrow="GitHub Workspace"
        title="Connected repository security"
        description="Browse GitHub repositories, profile their security posture, and launch autonomous scans without pasting URLs."
      />

      {error ? (
        <div className="glass-panel border border-rose-500/25 px-5 py-4 text-sm text-rose-100">{error}</div>
      ) : null}

      {notice ? (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel flex flex-col gap-3 border border-emerald-300/20 px-5 py-4 text-sm leading-6 text-emerald-100 sm:flex-row sm:items-center sm:justify-between"
        >
          <span>{notice}</span>
          <button type="button" onClick={onDismissNotice} className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-200">
            Dismiss
          </button>
        </motion.div>
      ) : null}

      <section className="glass-panel ig-outline overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-white/10 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <div className="ig-gradient flex h-14 w-14 shrink-0 items-center justify-center rounded-[20px] text-white shadow-glow">
              <Github size={26} />
            </div>
            <div className="min-w-0">
              <p className="eyebrow">GitHub connection</p>
              <h3 className="mt-1 truncate font-display text-[clamp(1.35rem,3vw,1.65rem)] font-bold leading-tight text-white">
                {connection?.connected ? `Connected as ${connection.username}` : "Connect your GitHub account"}
              </h3>
              <p className="mt-1 max-w-[62ch] text-sm leading-6 text-slate-400">
                {connection?.connected ? "Repository sync, scan launch, and posture analytics are enabled." : "OAuth is required before repositories can be listed."}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-wrap gap-2">
            {connection?.connected ? (
              <>
                {connection.avatar_url ? <img src={connection.avatar_url} alt="" className="h-11 w-11 rounded-full border border-white/10" /> : null}
                <Button type="button" variant="outline" onClick={() => load(true)} disabled={refreshing}>
                  <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
                  Sync Repos
                </Button>
                <Button type="button" variant="ghost" onClick={handleDisconnectGitHub}>
                  Disconnect
                </Button>
              </>
            ) : (
              <Button type="button" onClick={handleConnectGitHub} disabled={!connection?.configured}>
                <KeyRound size={16} />
                {connection?.configured === false ? "OAuth Not Configured" : "Connect GitHub"}
              </Button>
            )}
          </div>
        </div>

        {connection?.configured === false ? (
          <div className="border-t border-white/10 bg-amber-300/8 px-5 py-4 text-sm leading-6 text-amber-100">
            GitHub OAuth needs real credentials before redirecting. Add <span className="font-mono text-amber-50">GITHUB_CLIENT_ID</span>,{" "}
            <span className="font-mono text-amber-50">GITHUB_CLIENT_SECRET</span>, and{" "}
            <span className="font-mono text-amber-50">GITHUB_REDIRECT_URI=http://127.0.0.1:8000/github/callback</span> to your backend environment,
            then restart FastAPI.
          </div>
        ) : null}

        {connection?.connected ? (
          <div className="grid auto-rows-fr gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
            <AnalyticsCard label="Connected repos" value={analytics?.total_connected_repos} icon={Github} />
            <AnalyticsCard label="Repos scanned" value={analytics?.repos_scanned} icon={ShieldCheck} />
            <AnalyticsCard label="Risky repos" value={analytics?.risky_repos} icon={AlertTriangle} />
            <AnalyticsCard label="Avg posture" value={`${analytics?.average_posture || 0}%`} icon={Sparkles} />
            <AnalyticsCard label="Coverage" value={`${analytics?.scan_coverage || 0}%`} icon={GitPullRequest} />
          </div>
        ) : null}
      </section>

      {loading ? <WorkspaceSkeleton /> : null}

      {!loading && connection?.connected ? (
        <>
          <div className="editorial-card flex items-center gap-3 px-4 py-3">
            <Search size={18} className="shrink-0 text-cyan-200" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search repositories by name, language, visibility, or description"
              className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
            />
            <Badge className="shrink-0">{repositories.length} repos</Badge>
          </div>

          <div className="grid items-stretch gap-5 xl:grid-cols-2">
            {repositories.map((repo) => (
              <RepositoryCard
                key={repo.id}
                repo={repo}
                launchingRepoId={launchingRepoId}
                onLaunchScan={handleLaunch}
                onViewFindings={onSelectScan}
              />
            ))}
          </div>

          {!repositories.length ? (
            <div className="glass-panel px-5 py-8 text-sm text-slate-300">No repositories matched the current search.</div>
          ) : null}
        </>
      ) : null}

      {!loading && !connection?.connected ? (
        <div className="glass-panel px-5 py-8 text-sm leading-7 text-slate-300">
          Connect GitHub to turn this dashboard into a repository workspace with live repo cards, scan controls, posture analytics, and AI repository profiling.
        </div>
      ) : null}
    </div>
  );
}
