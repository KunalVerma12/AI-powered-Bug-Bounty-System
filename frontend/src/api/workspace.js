import { api } from "./client";
import { normalizeScan } from "./scans";

export async function fetchWorkspace(refresh = false) {
  const response = await api.get("/workspace", { params: { refresh } });
  return response.data;
}

export async function fetchGitHubStatus() {
  const response = await api.get("/github/status");
  return response.data;
}

export async function startGitHubConnect() {
  const response = await api.post("/auth/github/login");
  return response.data;
}

export async function disconnectGitHub() {
  const response = await api.delete("/github/disconnect");
  return response.data;
}

export async function launchRepositoryScan(repoId, preset = "full") {
  const response = await api.post(`/workspace/repositories/${encodeURIComponent(repoId)}/scan`, { preset });
  return normalizeScan(response.data);
}
