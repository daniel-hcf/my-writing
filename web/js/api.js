async function request(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  let data = null;
  try { data = await r.json(); } catch {}
  if (!r.ok) {
    const msg = (data && (data.detail || data.message)) || r.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  getConfig: () => request("GET", "/api/config"),
  putConfig: (cfg) => request("PUT", "/api/config", cfg),
  testProvider: (target) => request("POST", "/api/ai/test", { target }),

  getTodayAssignment: () => request("GET", "/api/assignments/today"),
  newAssignment: () => request("POST", "/api/assignments/new"),
  getAssignment: (id) => request("GET", `/api/assignments/${id}`),

  submit: (assignmentId, content) =>
    request("POST", "/api/submissions", { assignmentId, content }),
  listSubmissions: (limit = 50) => request("GET", `/api/submissions?limit=${limit}`),
  getSubmission: (id) => request("GET", `/api/submissions/${id}`),

  getStats: () => request("GET", "/api/stats"),
};
