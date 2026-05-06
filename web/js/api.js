const TOKEN_KEY = "auth_token";

export function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) opts.headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) opts.body = JSON.stringify(body);

  const response = await fetch(path, opts);
  let data = null;
  try {
    data = await response.json();
  } catch {}

  if (response.status === 401) {
    clearToken();
    throw new Error("UNAUTHORIZED");
  }
  if (!response.ok) {
    const msg = (data && (data.detail || data.message)) || response.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  authStatus: () => request("GET", "/api/auth/status"),
  login: (password) => request("POST", "/api/auth/login", { password }),
  setup: (password) => request("POST", "/api/auth/setup", { password }),

  getConfig: () => request("GET", "/api/config"),
  putConfig: (cfg) => request("PUT", "/api/config", cfg),
  testProvider: (target) => request("POST", "/api/ai/test", { target }),

  getTodayAssignment: () => request("GET", "/api/assignments/today"),
  newAssignment: () => request("POST", "/api/assignments/new"),
  getTodayImagePractice: () => request("GET", "/api/assignments/image-practice/today"),
  newImagePractice: () => request("POST", "/api/assignments/image-practice/new"),
  getTodayOutlinePractice: () => request("GET", "/api/assignments/outline-practice/today"),
  newOutlinePractice: () => request("POST", "/api/assignments/outline-practice/new"),
  getJournalAssignment: () => request("GET", "/api/assignments/journal"),
  getAssignment: (id) => request("GET", `/api/assignments/${id}`),

  submit: (assignmentId, content) => request("POST", "/api/submissions", { assignmentId, content }),
  listSubmissions: (limit = 50) => request("GET", `/api/submissions?limit=${limit}`),
  getSubmission: (id) => request("GET", `/api/submissions/${id}`),
  deleteSubmission: (id) => request("DELETE", `/api/submissions/${id}`),

  getStats: (mode = "all") => request("GET", `/api/stats?mode=${encodeURIComponent(mode)}`),

  listEditorialPacks: () => request("GET", "/api/editorial/packs"),
  importEditorialPack: (packId) => request("POST", `/api/editorial/packs/${encodeURIComponent(packId)}/import`),
  listRSSSources: () => request("GET", "/api/editorial/sources"),
  createRSSSource: (payload) => request("POST", "/api/editorial/sources", payload),
  updateRSSSource: (id, payload) => request("PUT", `/api/editorial/sources/${id}`, payload),
  deleteRSSSource: (id) => request("DELETE", `/api/editorial/sources/${id}`),
  fetchEditorialSources: () => request("POST", "/api/editorial/fetch"),
  listMaterials: (channel = "", limit = 100) =>
    request("GET", `/api/editorial/materials?limit=${limit}${channel ? `&channel=${encodeURIComponent(channel)}` : ""}`),
  getMaterial: (id) => request("GET", `/api/editorial/materials/${id}`),
  deepDiveMaterial: (id) => request("POST", `/api/editorial/materials/${id}/deep-dive`),
  storyIdeasMaterial: (id) => request("POST", `/api/editorial/materials/${id}/story-ideas`),
  listBriefs: (limit = 30) => request("GET", `/api/editorial/briefs?limit=${limit}`),
  generateTodayBrief: () => request("POST", "/api/editorial/briefs/today/generate"),
  sendBrief: (id) => request("POST", `/api/editorial/briefs/${id}/send`),
  getSMTPConfig: () => request("GET", "/api/editorial/smtp"),
  putSMTPConfig: (payload) => request("PUT", "/api/editorial/smtp", payload),
  testSMTPConfig: () => request("POST", "/api/editorial/smtp/test"),
  getEditorialSchedule: () => request("GET", "/api/editorial/schedule"),
  putEditorialSchedule: (payload) => request("PUT", "/api/editorial/schedule", payload),
};
