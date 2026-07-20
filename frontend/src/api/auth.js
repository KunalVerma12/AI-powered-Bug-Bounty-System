import { api, clearStoredToken, setStoredToken } from "./client";

export async function registerUser(username, email, password) {
  const response = await api.post("/auth/register", { username, email, password });
  setStoredToken(response.data.access_token);
  return response.data.user;
}

export async function loginUser(email, password) {
  const response = await api.post("/auth/login", { email, password });
  setStoredToken(response.data.access_token);
  return response.data.user;
}

export async function fetchCurrentUser() {
  const response = await api.get("/auth/me");
  return response.data;
}

export function logoutUser() {
  clearStoredToken();
}
