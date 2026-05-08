import { api } from "../api.js";
import { el, showToast } from "../utils.js";

const SAVE_DELAY_MS = 800;

export function hasDraftContent(assignment, textarea) {
  return Boolean((textarea?.value || "").trim() || (assignment.draftContent || "").trim());
}

export function confirmDiscardDraft(assignment, textarea) {
  if (!hasDraftContent(assignment, textarea)) return true;
  return window.confirm("当前内容还没有提交评分，换题会丢弃已暂存的文字。确定继续吗？");
}

export function createDraftController(assignment, textarea, onStatus) {
  let timer = null;
  let pending = null;
  let lastSaved = assignment.draftContent || "";

  async function saveNow() {
    clearTimeout(timer);
    timer = null;
    const content = textarea.value;
    onStatus("saving");
    try {
      pending = api.saveDraft(assignment.id, content);
      const saved = await pending;
      pending = null;
      lastSaved = saved.draftContent || "";
      assignment.draftContent = saved.draftContent || "";
      assignment.draftCharCount = saved.draftCharCount || 0;
      assignment.draftUpdatedAt = saved.draftUpdatedAt || null;
      onStatus("saved", saved);
      return saved;
    } catch (e) {
      pending = null;
      onStatus("error", e);
      throw e;
    }
  }

  function scheduleSave() {
    clearTimeout(timer);
    timer = null;
    if (textarea.value === lastSaved) {
      onStatus(lastSaved ? "saved" : "idle");
      return;
    }
    onStatus("dirty");
    timer = setTimeout(() => {
      saveNow().catch(() => {});
    }, SAVE_DELAY_MS);
  }

  async function flush() {
    if (timer || textarea.value !== lastSaved) {
      return saveNow();
    }
    return pending;
  }

  textarea.addEventListener("input", scheduleSave);

  return {
    saveNow,
    scheduleSave,
    flush,
  };
}

export function buildDraftControls(controller, statusText) {
  const saveBtn = el("button", { class: "btn secondary" }, "暂存");
  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    try {
      await controller.saveNow();
    } catch (e) {
      showToast(`暂存失败：${e.message}`, "error");
    } finally {
      saveBtn.disabled = false;
    }
  });
  return [statusText, saveBtn];
}

export function updateDraftStatus(statusText, state) {
  const labels = {
    idle: "",
    dirty: "未暂存",
    saving: "暂存中...",
    saved: "已暂存",
    error: "暂存失败",
  };
  statusText.textContent = labels[state] || "";
  statusText.classList.toggle("draft-error", state === "error");
}
