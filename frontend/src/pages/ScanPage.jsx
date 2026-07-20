import { SectionTitle } from "../components/ui/SectionTitle";
import { ScanForm } from "../components/ScanForm";

export function ScanPage({ repoUrl, setRepoUrl, scanPreset, setScanPreset, onSubmit, scanning, activeScan, apiState, scanError, loadingDashboard, currentUser }) {
  return (
    <div className="space-y-4">
      <SectionTitle
        eyebrow="Scanner"
        title="Launch autonomous security operation"
        description="Choose an operating profile and watch each agent advance through reconnaissance, analysis, fixes, and briefing."
      />
      {apiState === "disconnected" ? (
        <div className="glass-panel border border-amber-500/30 px-5 py-4 text-sm text-amber-200">
          The frontend cannot reach the backend right now. Start the FastAPI server before launching a scan.
        </div>
      ) : null}
      {apiState === "connected" && !currentUser ? (
        <div className="glass-panel border border-rose-500/30 px-5 py-4 text-sm text-rose-200">
          Sign in first. New scans are now owned by the authenticated user and hidden from other accounts.
        </div>
      ) : null}
      {apiState === "loading" || loadingDashboard ? (
        <div className="glass-panel border border-sky-500/30 px-5 py-4 text-sm text-sky-200">
          Checking backend connection and fetching the latest scan state.
        </div>
      ) : null}
      {scanError ? (
        <div className="glass-panel border border-rose-500/30 px-5 py-4 text-sm text-rose-200">
          {scanError}
        </div>
      ) : null}
      <ScanForm
        repoUrl={repoUrl}
        setRepoUrl={setRepoUrl}
        scanPreset={scanPreset}
        setScanPreset={setScanPreset}
        onSubmit={onSubmit}
        scanning={scanning}
        activeScan={activeScan}
        disabled={!currentUser}
      />
    </div>
  );
}
