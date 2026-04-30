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
  getJournalAssignment: () => request("GET", "/api/assignments/journal"),
  getAssignment: (id) => request("GET", `/api/assignments/${id}`),

  submit: (assignmentId, content) => request("POST", "/api/submissions", { assignmentId, content }),
  listSubmissions: (limit = 50) => request("GET", `/api/submissions?limit=${limit}`),
  getSubmission: (id) => request("GET", `/api/submissions/${id}`),
  deleteSubmission: (id) => request("DELETE", `/api/submissions/${id}`),

  getStats: (mode = "all") => request("GET", `/api/stats?mode=${encodeURIComponent(mode)}`),
};
