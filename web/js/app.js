import { api } from "./api.js";
import { showToast } from "./utils.js";
import { renderDaily } from "./views/daily.js";
import { renderHistory } from "./views/history.js";
import { renderSettings } from "./views/settings.js";
import { renderStats } from "./views/stats.js";

const views = {
  daily: renderDaily,
  history: renderHistory,
  stats: renderStats,
  settings: renderSettings,
};

const state = {
  ready: { text: false, image: false },
};

async function refreshConfig() {
  try {
    const cfg = await api.getConfig();
    state.ready = cfg.ready;
    return cfg;
  } catch (e) {
    showToast("无法读取配置：" + e.message, "error");
    return null;
  }
}

function setActiveTab(name) {
  document.querySelectorAll("#tabs .tab").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
}

async function navigate(name) {
  setActiveTab(name);
  const root = document.getElementById("view");
  root.innerHTML = "<div class='card'><div class='empty'>加载中...</div></div>";

  if (name !== "settings" && !state.ready.text) {
    showToast("请先在设置页配置文本模型", "error");
    name = "settings";
    setActiveTab(name);
  }

  try {
    await views[name](root, { state, navigate, refreshConfig });
  } catch (e) {
    root.innerHTML = `<div class='card'><div class='empty'>加载失败：${e.message}</div></div>`;
  }
}

document.querySelectorAll("#tabs .tab").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.tab));
});

(async function boot() {
  await refreshConfig();
  await navigate(state.ready.text ? "daily" : "settings");
})();
