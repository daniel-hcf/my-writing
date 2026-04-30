import { api } from "../api.js";
import { GENERAL_TIPS, TIPS } from "../tips.js";
import { charCount, el, escapeHtml, modeLabel, showToast } from "../utils.js";
import { buildTipsPanel, renderScoredResult } from "./practice_common.js";

const MIN = 500;

export async function renderImagePractice(root, ctx) {
  root.innerHTML = "";
  let assignment;
  try {
    assignment = await api.getTodayImagePractice();
  } catch (e) {
    root.appendChild(el("div", { class: "card" }, [
      el("h2", {}, "看图写作"),
      el("div", { class: "empty" }, `生成图片题失败：${e.message}`),
      el("button", { class: "btn", onclick: () => renderImagePractice(root, ctx) }, "重试"),
    ]));
    return;
  }

  if (assignment.submission) {
    renderResult(root, ctx, assignment, assignment.submission);
  } else {
    renderAssignment(root, ctx, assignment);
  }
}

function renderAssignment(root, ctx, assignment) {
  root.innerHTML = "";

  const focusTag = assignment.focusDimension
    ? el("span", { class: "focus-tag" }, `本次专项：${assignment.focusDimension}`)
    : null;

  const refreshBtn = el("button", { class: "btn secondary btn-sm" }, "换一张");
  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    refreshBtn.textContent = "生成中...";
    try {
      const next = await api.newImagePractice();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`换图失败：${e.message}`, "error");
      refreshBtn.disabled = false;
      refreshBtn.textContent = "换一张";
    }
  });

  const card = el("div", { class: "card" }, [
    el("h2", {}, [assignment.title || "看图写作练习", focusTag]),
    el("div", { class: "row", style: "margin-top:2px;" }, [
      el("div", { class: "muted" }, `日期：${assignment.date} · 类型：${modeLabel(assignment.type)}`),
      el("div", { class: "spacer" }),
      refreshBtn,
    ]),
  ]);
  if (assignment.imageData) {
    card.appendChild(el("img", { class: "assignment-image", src: assignment.imageData, alt: "题图" }));
  }
  if (assignment.scenario) {
    card.appendChild(el("div", { class: "scenario-box", html: escapeHtml(assignment.scenario) }));
  }

  const textarea = el("textarea", {
    rows: "16",
    placeholder: `请围绕题图写作，至少 ${MIN} 字...`,
  });
  const counter = el("div", { class: "char-count" }, `0 / ${MIN}`);
  const submitBtn = el("button", { class: "btn" }, "提交评分");
  submitBtn.disabled = true;

  textarea.addEventListener("input", () => {
    const count = charCount(textarea.value);
    counter.textContent = `${count} / ${MIN}`;
    counter.classList.toggle("ok", count >= MIN);
    submitBtn.disabled = count < MIN;
  });

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "正在评分...";
    try {
      const result = await api.submit(assignment.id, textarea.value);
      renderResult(root, ctx, assignment, result);
    } catch (e) {
      showToast(`评分失败：${e.message}`, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "提交评分";
    }
  });

  const tips = TIPS[assignment.focusDimension] || GENERAL_TIPS;
  const writingCol = el("div", {}, [
    textarea,
    counter,
    el("div", { class: "row", style: "margin-top:8px;" }, [
      el("div", { class: "spacer" }),
      submitBtn,
    ]),
  ]);

  card.appendChild(el("div", { class: "writing-layout" }, [writingCol, buildTipsPanel(assignment.focusDimension, tips)]));
  root.appendChild(card);
}

function renderResult(root, ctx, assignment, result) {
  const nextBtn = el("button", { class: "btn" }, "再来一张");
  nextBtn.addEventListener("click", async () => {
    nextBtn.disabled = true;
    nextBtn.textContent = "生成中...";
    try {
      const next = await api.newImagePractice();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`生成失败：${e.message}`, "error");
      nextBtn.disabled = false;
      nextBtn.textContent = "再来一张";
    }
  });

  renderScoredResult(root, assignment, result, [
    nextBtn,
    el("div", { class: "spacer" }),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("history") }, "查看历史"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("stats") }, "查看统计"),
  ]);
}
