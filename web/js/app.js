import { api, clearToken } from "./api.js";
import { showToast } from "./utils.js";
import { checkAuth, showAuthScreen } from "./auth.js";
import { renderDaily } from "./views/daily.js";
import { renderHistory } from "./views/history.js";
import { renderImagePractice } from "./views/image_practice.js";
import { renderJournal } from "./views/journal.js";
import { renderSettings } from "./views/settings.js";
import { renderStats } from "./views/stats.js";

const views = {
  daily: renderDaily,
  image_practice: renderImagePractice,
  journal: renderJournal,
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
    showToast(`无法读取配置：${e.message}`, "error");
    return null;
  }
}

function setActiveTab(name) {
  document.querySelectorAll("#tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
}

function resolveNavigationTarget(name) {
  if (name === "settings") return "settings";
  if (!state.ready.text) {
    showToast("请先在设置页配置文本模型", "error");
    return "settings";
  }
  if (name === "image_practice" && !state.ready.image) {
    showToast("请先在设置页配置图片模型", "error");
    return "settings";
  }
  return name;
}

async function navigate(name) {
  const target = resolveNavigationTarget(name);
  setActiveTab(target);
  const root = document.getElementById("view");
  root.innerHTML = "<div class='card'><div class='empty'>加载中...</div></div>";

  try {
    await views[target](root, { state, navigate, refreshConfig });
  } catch (e) {
    root.innerHTML = `<div class='card'><div class='empty'>加载失败：${e.message}</div></div>`;
  }
}

document.querySelectorAll("#tabs .tab").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.tab));
});

document.getElementById("logout-btn")?.addEventListener("click", () => {
  clearToken();
  location.reload();
});

window.addEventListener("unhandledrejection", (e) => {
  if (e.reason?.message === "UNAUTHORIZED") {
    showToast("登录已过期，请重新登录", "error");
    clearToken();
    setTimeout(() => location.reload(), 1500);
  }
});

async function startApp() {
  await refreshConfig();
  await navigate(state.ready.text ? "daily" : "settings");
}

(async function boot() {
  try {
    const authed = await checkAuth();
    if (!authed) {
      await showAuthScreen(startApp);
      return;
    }
    await startApp();
  } catch (e) {
    console.error("启动失败", e);
    showToast("连接服务失败，请刷新重试", "error");
  }
})();
