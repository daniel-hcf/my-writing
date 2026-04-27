export const DIMENSIONS = [
  "人物塑造","对话描写","场景描写","叙事结构","情感表达","语言文采","细节描写",
];

export function charCount(text) {
  return [...(text || "")].length;
}

export function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

export function showToast(msg, type = "info") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.toggle("error", type === "error");
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3000);
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v != null) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

export function scoreClass(n) {
  if (n >= 8) return "score-high";
  if (n <= 5) return "score-low";
  return "";
}

export function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
