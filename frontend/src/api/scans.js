import { api } from "./client";

function titleCaseStatus(status) {
  if (!status) {
    return "Unknown";
  }
  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
}

function normalizeFinding(finding, repoName) {
  return {
    id: finding.id,
    title: finding.title,
    severity: finding.severity,
    description: finding.description,
    file_path: finding.file,
    line: finding.line,
    tool: finding.tool,
    cwe: finding.cwe || finding.tool,
    repo_name: repoName,
    ai_analysis: finding.explanation,
    fix_suggestion: finding.fix,
    snippet: finding.snippet,
    confidence: finding.confidence ?? 0,
    cvss_score: finding.cvss_score ?? 0,
    exploitability_score: finding.exploitability_score ?? 0,
    tags: finding.tags || [finding.tool],
    tech_context: finding.tech_context || "",
    component_owner: finding.component_owner || "",
    false_positive_hint: finding.false_positive_hint || "",
    cwe_link: finding.cwe_link || "",
    attack_surface_tags: finding.attack_surface_tags || [],
    review_status: finding.review_status || "Open",
    ai_analyzed: Boolean(finding.ai_analyzed),
    analysis_source: finding.analysis_source || "multi-agent",
    what_happened: finding.what_happened || finding.description,
    why_it_matters: finding.why_it_matters || finding.explanation,
    how_to_fix: finding.how_to_fix || finding.fix,
    example_fix: finding.example_fix || ""
  };
}

export function normalizeScan(scan) {
  const summary = scan.summary || {};
  return {
    id: scan.scan_id,
    scan_id: scan.scan_id,
    repo_url: scan.repo,
    repo_name: scan.repo_name,
    preset: scan.preset || "full",
    status: titleCaseStatus(scan.status),
    created_at: scan.scanned_at,
    updated_at: scan.scanned_at,
    progress: scan.progress ?? (scan.status.toLowerCase() === "completed" ? 100 : 60),
    steps: scan.agent_steps || [],
    vulnerability_count: summary.total ?? 0,
    critical_count: summary.critical ?? 0,
    high_count: summary.high ?? 0,
    medium_count: summary.medium ?? 0,
    low_count: summary.low ?? 0,
    vulnerabilities: scan.vulnerabilities.map((finding) => normalizeFinding(finding, scan.repo_name)),
    timeline: scan.timeline || [],
    summary,
    recon: scan.recon || { languages: [], frameworks: [], entry_points: [], sensitive_files: [], architecture_summary: "" },
    repo_analysis: scan.repo_analysis || {
      overview_summary: "",
      description: "",
      project_type: "",
      tech_stack: [],
      architecture: "",
      security_posture: "",
      improvements_summary: "",
      risk_areas: [],
      missing_features: [],
      recommendations: []
    },
    analysis_mode: scan.analysis_mode || "local",
    risk_assessment: scan.risk_assessment || "",
    error_message: scan.error_message || ""
  };
}

export function normalizeHistoryItem(scan) {
  const summary = scan.summary || {};
  return {
    id: scan.scan_id,
    scan_id: scan.scan_id,
    repo_url: scan.repo,
    repo_name: scan.repo_name,
    preset: scan.preset || "full",
    status: titleCaseStatus(scan.status),
    created_at: scan.scanned_at,
    updated_at: scan.scanned_at,
    progress: scan.progress ?? (scan.status.toLowerCase() === "completed" ? 100 : 0),
    vulnerability_count: summary.total ?? 0,
    critical_count: summary.critical ?? 0,
    high_count: summary.high ?? 0,
    medium_count: summary.medium ?? 0,
    low_count: summary.low ?? 0,
    summary,
    analysis_mode: scan.analysis_mode || "local",
    error_message: scan.error_message || ""
  };
}

export async function checkBackendHealth() {
  const response = await api.get("/health");
  return response.data;
}

export async function scanRepo(repoUrl, preset = "full") {
  const response = await api.post("/scan", { repo_url: repoUrl, preset });
  return normalizeScan(response.data);
}

export async function fetchDashboardSummary() {
  const response = await api.get("/dashboard/summary");
  return response.data;
}

export async function fetchScans() {
  const response = await api.get("/results");
  return response.data.map(normalizeHistoryItem);
}

export async function fetchScan(scanId) {
  const response = await api.get(`/results/${scanId}`);
  return normalizeScan(response.data);
}

export async function updateFindingReviewStatus(scanId, findingId, reviewStatus) {
  const response = await api.patch(`/results/${scanId}/findings/${findingId}`, { review_status: reviewStatus });
  return normalizeScan(response.data);
}

export async function exportScanReport(scanId, format) {
  const response = await api.get(`/results/${scanId}/report`, {
    params: { format },
    responseType: format === "json" ? "json" : "blob"
  });
  return response.data;
}
