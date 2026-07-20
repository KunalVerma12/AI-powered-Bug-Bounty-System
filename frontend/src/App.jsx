import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { AnimatePresence, motion } from "framer-motion";
import { fetchCurrentUser, loginUser, logoutUser, registerUser } from "./api/auth";
import { checkBackendHealth, exportScanReport, fetchDashboardSummary, fetchScan, fetchScans, scanRepo, updateFindingReviewStatus } from "./api/scans";
import { launchRepositoryScan } from "./api/workspace";
import { api, getStoredToken, setStoredToken } from "./api/client";
import { BottomNav } from "./components/BottomNav";
import { DetailModal } from "./components/DetailModal";
import { Header } from "./components/Header";
import { emptySummary } from "./data/fallback";
import { useDarkMode } from "./hooks/useDarkMode";
import { ActivityPage } from "./pages/ActivityPage";
import { AuthPage } from "./pages/AuthPage";
import { HomePage } from "./pages/HomePage";
import { ProfilePage } from "./pages/ProfilePage";
import { ScanPage } from "./pages/ScanPage";
import { WorkspacePage } from "./pages/WorkspacePage";

export default function App() {
  const { isDark, setIsDark } = useDarkMode();
  const [activeTab, setActiveTab] = useState("home");
  const [repoUrl, setRepoUrl] = useState("https://github.com/example/ai-security-demo");
  const [scanPreset, setScanPreset] = useState("full");
  const [summary, setSummary] = useState(emptySummary);
  const [scans, setScans] = useState([]);
  const [activeScan, setActiveScan] = useState(null);
  const [selectedVulnerability, setSelectedVulnerability] = useState(null);
  const [selectedFindingIndex, setSelectedFindingIndex] = useState(0);
  const [scanning, setScanning] = useState(false);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [apiState, setApiState] = useState("loading");
  const [scanError, setScanError] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ username: "", email: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [githubNotice, setGithubNotice] = useState("");
  const activeScanRef = useRef(null);
  const selectedVulnerabilityRef = useRef(null);

  useEffect(() => {
    activeScanRef.current = activeScan;
  }, [activeScan]);

  useEffect(() => {
    selectedVulnerabilityRef.current = selectedVulnerability;
  }, [selectedVulnerability]);

  useEffect(() => {
    const hashParams = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
    const params = new URLSearchParams(hashParams || window.location.search);
    const githubState = params.get("github");
    const token = params.get("token");
    const tab = params.get("tab");
    const message = params.get("message");
    const code = params.get("code");
    const state = params.get("state");

    if (code && state) {
      const callback = new URL("/auth/github/callback", api.defaults.baseURL);
      callback.searchParams.set("code", code);
      callback.searchParams.set("state", state);
      window.location.href = callback.toString();
      return;
    }

    if (!githubState && !token && !tab) {
      return;
    }

    if (token) {
      setStoredToken(token);
    }
    if (tab === "workspace" || githubState) {
      setActiveTab("workspace");
    }
    if (githubState === "connected") {
      setGithubNotice("GitHub connected successfully. Synchronizing repositories now.");
    }
    if (githubState === "error") {
      setGithubNotice(message || "GitHub connection failed. Please try again.");
    }

    window.history.replaceState({}, document.title, window.location.pathname);
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setLoadingDashboard(true);
      const health = await checkBackendHealth();
      if (health.status !== "ok") {
        throw new Error("Backend healthcheck failed");
      }

      if (!getStoredToken()) {
        setCurrentUser(null);
        setSummary(emptySummary);
        setScans([]);
        setActiveScan(null);
        setSelectedVulnerability(null);
        setSelectedFindingIndex(0);
        setScanError("");
        setApiState("connected");
        return;
      }

      const user = await fetchCurrentUser();
      setCurrentUser(user);

      const [summaryData, scansData] = await Promise.all([fetchDashboardSummary(), fetchScans()]);
      const currentActiveScan = activeScanRef.current;
      const currentSelectedVulnerability = selectedVulnerabilityRef.current;
      const targetScanId = (currentActiveScan ? scansData.find((scan) => scan.id === currentActiveScan.id)?.id : null) || scansData[0]?.id || null;
      const nextActiveScan = targetScanId ? await fetchScan(targetScanId) : null;
      const nextSelectedVulnerability =
        currentSelectedVulnerability && nextActiveScan
          ? nextActiveScan.vulnerabilities.find((item) => item.id === currentSelectedVulnerability.id) || null
          : null;
      const nextSelectedFindingIndex = nextSelectedVulnerability
        ? nextActiveScan.vulnerabilities.findIndex((item) => item.id === nextSelectedVulnerability.id)
        : 0;

      setSummary(summaryData);
      setScans(scansData);
      setActiveScan(nextActiveScan);
      setSelectedVulnerability(nextSelectedVulnerability);
      setSelectedFindingIndex(nextSelectedFindingIndex >= 0 ? nextSelectedFindingIndex : 0);
      setScanError("");
      setApiState("connected");
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        logoutUser();
        setCurrentUser(null);
        setSummary(emptySummary);
        setScans([]);
        setActiveScan(null);
        setSelectedVulnerability(null);
        setSelectedFindingIndex(0);
        setApiState("connected");
        return;
      }

      setSummary(emptySummary);
      setScans([]);
      setActiveScan(null);
      setSelectedVulnerability(null);
      setSelectedFindingIndex(0);
      setApiState("disconnected");
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const interval = window.setInterval(loadDashboard, activeScan?.status === "Running" || activeScan?.status === "Queued" ? 4000 : 10000);
    return () => window.clearInterval(interval);
  }, [loadDashboard, activeScan?.status]);

  async function handleScanSubmit(event) {
    event.preventDefault();
    if (!repoUrl) {
      return;
    }

    try {
      setScanning(true);
      setScanError("");
      if (!currentUser) {
        throw new Error("Please sign in before launching a repository scan.");
      }
      const scan = await scanRepo(repoUrl, scanPreset);
      setActiveScan(scan);
      setSelectedVulnerability(null);
      setSelectedFindingIndex(0);
      setScans((current) => [scan, ...current.filter((item) => item.id !== scan.id)]);
      setActiveTab("scan");
      setApiState("connected");
      await loadDashboard();
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        logoutUser();
        setCurrentUser(null);
        setScanError("Please sign in again before launching a repository scan.");
      } else if (axios.isAxiosError(error)) {
        setScanError(error.response?.data?.detail || error.message || "The repository scan failed.");
      } else if (error instanceof Error && error.message) {
        setScanError(error.message);
      } else {
        setScanError("The backend is unavailable, so the scan could not start.");
        setApiState("disconnected");
      }
    } finally {
      setScanning(false);
    }
  }

  async function handleWorkspaceScan(repoId, preset) {
    try {
      setScanning(true);
      setScanError("");
      const scan = await launchRepositoryScan(repoId, preset);
      setActiveScan(scan);
      setSelectedVulnerability(null);
      setSelectedFindingIndex(0);
      setScans((current) => [scan, ...current.filter((item) => item.id !== scan.id)]);
      setActiveTab("scan");
      await loadDashboard();
      return scan;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        setScanError(error.response?.data?.detail || "The repository scan failed.");
      } else {
        setScanError("The repository scan failed.");
      }
      throw error;
    } finally {
      setScanning(false);
    }
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    try {
      setAuthLoading(true);
      setAuthError("");
      const user =
        authMode === "login"
          ? await loginUser(authForm.email, authForm.password)
          : await registerUser(authForm.username, authForm.email, authForm.password);
      setCurrentUser(user);
      setAuthError("");
      setAuthForm({ username: "", email: "", password: "" });
      setActiveTab("home");
      await loadDashboard();
    } catch (error) {
      if (axios.isAxiosError(error)) {
        setAuthError(error.response?.data?.detail || "Authentication failed.");
      } else {
        setAuthError("Authentication failed.");
      }
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    logoutUser();
    setCurrentUser(null);
    setAuthError("");
    setScanError("");
    setSummary(emptySummary);
    setScans([]);
    setActiveScan(null);
    setSelectedVulnerability(null);
    setSelectedFindingIndex(0);
  }

  async function handleSelectScan(scanId) {
    try {
      const detail = await fetchScan(scanId);
      setActiveScan(detail);
      setSelectedVulnerability(null);
      setSelectedFindingIndex(0);
      setActiveTab("home");
    } catch (_error) {
      const local = scans.find((scan) => scan.id === scanId);
      if (local) {
        setActiveScan(local);
        setSelectedVulnerability(null);
        setSelectedFindingIndex(0);
        setActiveTab("home");
      }
    }
  }

  async function handleUpdateFindingStatus(findingId, reviewStatus) {
    if (!activeScan) {
      return;
    }
    try {
      const updatedScan = await updateFindingReviewStatus(activeScan.id, findingId, reviewStatus);
      setActiveScan(updatedScan);
      setScans((current) =>
        current.map((scan) =>
          scan.id === updatedScan.id
            ? {
                ...scan,
                status: updatedScan.status,
                vulnerability_count: updatedScan.vulnerability_count,
                critical_count: updatedScan.critical_count,
                progress: updatedScan.progress
              }
            : scan
        )
      );
      const updatedFinding = updatedScan.vulnerabilities.find((item) => item.id === findingId) || null;
      setSelectedVulnerability(updatedFinding);
    } catch (_error) {
      setScanError("We couldn't update the finding status right now.");
    }
  }

  async function handleExportReport(format) {
    if (!activeScan) {
      return;
    }
    try {
      const file = await exportScanReport(activeScan.id, format);
      const blob =
        format === "json"
          ? new Blob([JSON.stringify(file, null, 2)], { type: "application/json" })
          : file;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${activeScan.repo_name}-${activeScan.id}.${format === "markdown" ? "md" : format}`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (_error) {
      setScanError("We couldn't export the report for this scan.");
    }
  }

  function handleSelectFindingIndex(index) {
    if (!activeScan?.vulnerabilities[index]) {
      return;
    }
    setSelectedFindingIndex(index);
  }

  function handleOpenVulnerability(vulnerability) {
    const index = (activeScan?.vulnerabilities || []).findIndex((item) => item.id === vulnerability.id);
    setSelectedFindingIndex(index >= 0 ? index : 0);
    setSelectedVulnerability(vulnerability);
  }

  function handleNextFinding() {
    if (selectedFindingIndex >= (activeScan?.vulnerabilities.length || 0) - 1) {
      return;
    }
    const nextIndex = selectedFindingIndex + 1;
    setSelectedFindingIndex(nextIndex);
    if (selectedVulnerability) {
      setSelectedVulnerability(activeScan.vulnerabilities[nextIndex]);
    }
  }

  function handlePreviousFinding() {
    if (selectedFindingIndex <= 0) {
      return;
    }
    const previousIndex = selectedFindingIndex - 1;
    setSelectedFindingIndex(previousIndex);
    if (selectedVulnerability) {
      setSelectedVulnerability(activeScan.vulnerabilities[previousIndex]);
    }
  }

  useEffect(() => {
    const activeVulnerabilities = activeScan?.vulnerabilities || [];
    if (!activeVulnerabilities.length) {
      setSelectedVulnerability(null);
      setSelectedFindingIndex(0);
      return;
    }
    if (selectedFindingIndex >= activeVulnerabilities.length) {
      setSelectedFindingIndex(0);
      return;
    }
  }, [activeScan, selectedFindingIndex]);

  if (!currentUser) {
    return (
      <div className="min-h-screen">
        <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-4 py-4 sm:px-6 lg:px-8">
          <Header isDark={isDark} onToggleDark={() => setIsDark((value) => !value)} />
          <AuthPage
            authMode={authMode}
            setAuthMode={setAuthMode}
            authForm={authForm}
            setAuthForm={setAuthForm}
            authError={authError}
            authLoading={authLoading}
            onAuthSubmit={handleAuthSubmit}
            apiState={apiState}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-28 sm:pb-32">
      <div className="mx-auto flex min-h-screen w-full max-w-[1180px] flex-col gap-5 px-4 py-4 sm:gap-6 sm:px-6 lg:px-8">
        <Header isDark={isDark} onToggleDark={() => setIsDark((value) => !value)} />

        <main className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_330px] xl:grid-cols-[minmax(0,1fr)_350px]">
          <section className="min-w-0 space-y-6 pb-8">
            <AnimatePresence mode="wait">
              <motion.div key={activeTab} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
                {activeTab === "home" ? (
                  <HomePage
                    summary={summary}
                    vulnerabilities={activeScan?.vulnerabilities || []}
                    selectedFindingIndex={selectedFindingIndex}
                    onSelectVulnerability={handleOpenVulnerability}
                    onSelectFindingIndex={handleSelectFindingIndex}
                    onNextFinding={handleNextFinding}
                    onPreviousFinding={handlePreviousFinding}
                    apiState={apiState}
                    loading={loadingDashboard}
                    activeScan={activeScan}
                    onExportReport={handleExportReport}
                  />
                ) : null}
                {activeTab === "scan" ? (
                  <ScanPage
                    repoUrl={repoUrl}
                    setRepoUrl={setRepoUrl}
                    scanPreset={scanPreset}
                    setScanPreset={setScanPreset}
                    onSubmit={handleScanSubmit}
                    scanning={scanning}
                    activeScan={activeScan}
                    apiState={apiState}
                    scanError={scanError}
                    loadingDashboard={loadingDashboard}
                    currentUser={currentUser}
                  />
                ) : null}
                {activeTab === "workspace" ? (
                  <WorkspacePage notice={githubNotice} onDismissNotice={() => setGithubNotice("")} onLaunchRepositoryScan={handleWorkspaceScan} onSelectScan={handleSelectScan} />
                ) : null}
                {activeTab === "activity" ? <ActivityPage scans={scans} onSelectScan={handleSelectScan} apiState={apiState} currentUser={currentUser} /> : null}
                {activeTab === "profile" ? (
                  <ProfilePage
                    summary={summary}
                    currentUser={currentUser}
                    authMode={authMode}
                    setAuthMode={setAuthMode}
                    authForm={authForm}
                    setAuthForm={setAuthForm}
                    authError={authError}
                    authLoading={authLoading}
                    onAuthSubmit={handleAuthSubmit}
                    onLogout={handleLogout}
                  />
                ) : null}
              </motion.div>
            </AnimatePresence>
          </section>

          <aside className="hidden lg:block">
            <div className="glass-panel mesh-panel ig-outline sticky top-24 max-h-[calc(100vh-8rem)] overflow-hidden px-4 py-4">
              <div className="max-h-[calc(100vh-10rem)] space-y-4 overflow-y-auto pr-1">
                <div>
                  <p className="eyebrow">Active detail</p>
                  <h3 className="mt-2 truncate font-display text-[clamp(1.2rem,2vw,1.45rem)] font-bold leading-tight text-white" title={
                    apiState === "loading"
                      ? "Checking backend"
                      : apiState === "disconnected"
                      ? "Backend unavailable"
                      : activeScan?.repo_name || "No active scan"
                  }>
                    {apiState === "loading"
                      ? "Checking backend"
                      : apiState === "disconnected"
                      ? "Backend unavailable"
                      : activeScan?.repo_name || "No active scan"}
                  </h3>
                  <p className="mt-2 max-w-[34ch] text-sm leading-6 text-slate-400">
                    {apiState === "loading"
                      ? "Verifying the FastAPI service before loading live scan data."
                      : apiState === "disconnected"
                      ? "The frontend could not reach the FastAPI service, so no live scan data is being shown."
                      : !currentUser
                      ? "The backend is online. Sign in to load your isolated scan history and results."
                      : activeScan
                      ? `${activeScan.status} in ${activeScan.analysis_mode} mode with ${activeScan.vulnerability_count} findings surfaced in the latest scan.`
                      : "Launch or select a scan to inspect agent activity and vulnerabilities."}
                  </p>
                </div>

                {activeScan?.error_message ? (
                  <div className="rounded-[20px] border border-rose-500/20 bg-rose-500/10 px-4 py-4 text-sm leading-6 text-rose-100">
                    {activeScan.error_message}
                  </div>
                ) : null}

                {activeScan?.risk_assessment ? (
                  <div className="line-clamp-6 rounded-[20px] border border-white/10 bg-white/[0.055] px-4 py-4 text-sm leading-6 text-slate-300">
                    {activeScan.risk_assessment}
                  </div>
                ) : null}

                {activeScan?.timeline?.length ? (
                  <div className="space-y-4">
                    {activeScan.timeline.map((item, index) => (
                      <div key={`${item}-${index}`} className="relative flex gap-3 rounded-[18px] border border-white/10 bg-white/[0.045] px-3 py-3">
                        <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-300/10">
                          <span className="h-2 w-2 rounded-full bg-cyan-200" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Step {index + 1}</p>
                          <p className="mt-1 line-clamp-3 text-sm leading-6 text-slate-300">{item}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </aside>
        </main>
      </div>

      <BottomNav active={activeTab} onChange={setActiveTab} />
      <DetailModal
        vulnerability={selectedVulnerability}
        onClose={() => setSelectedVulnerability(null)}
        findingIndex={selectedFindingIndex}
        findingTotal={activeScan?.vulnerabilities.length || 0}
        onNext={handleNextFinding}
        onPrevious={handlePreviousFinding}
        onUpdateReviewStatus={handleUpdateFindingStatus}
      />
    </div>
  );
}
