import { ActivityList } from "../components/ActivityList";
import { SectionTitle } from "../components/ui/SectionTitle";

export function ActivityPage({ scans, onSelectScan, apiState, currentUser }) {
  return (
    <div className="space-y-4">
      <SectionTitle
        eyebrow="Activity"
        title="Scan history"
        description="Modern operation cards with status, findings, severity breakdown, confidence, and quick actions."
      />
      {scans.length ? (
        <ActivityList scans={scans} onSelectScan={onSelectScan} />
      ) : (
        <div className="glass-panel px-5 py-6 text-sm text-slate-300">
          {apiState === "disconnected"
            ? "Activity is empty because the FastAPI backend is not reachable."
            : !currentUser
            ? "Sign in to view only the scans that belong to your account."
            : "No scans have been run yet, so there is no activity history."}
        </div>
      )}
    </div>
  );
}
