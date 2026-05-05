export const DIMENSIONS = [
  "人物塑造",
  "对话描写",
  "场景描写",
  "叙事结构",
  "情感表达",
  "语言文采",
  "细节描写",
];

export const MODE_LABELS = {
  daily: "每日主练",
  image_practice: "看图写作",
  outline_practice: "故事小纲",
  journal: "每日随笔",
};

export function modeLabel(mode) {
  return MODE_LABELS[mode] || mode || "未知类型";
}

export function charCount(text) {
  return [...(text || "")].length;
}

export function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function showToast(msg, type = "info") {
  const node = document.getElementById("toast");
  node.textContent = msg;
  node.classList.toggle("error", type === "error");
  node.classList.add("show");
  clearTimeout(node._t);
  node._t = setTimeout(() => node.classList.remove("show"), 3000);
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else if (value != null) node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
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
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}
