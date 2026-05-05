import { api } from "../api.js";
import { charCount, el, modeLabel, showToast } from "../utils.js";
import { buildTipsPanel, renderScoredResult } from "./practice_common.js";

const MIN = 100;
const TARGET = "100~200";
const OUTLINE_TIPS = {
  focus: "根据标题和冲突引子写故事小纲，重点看目标、阻碍、升级和开放结尾是否成立。",
  skills: [
    "先写清主角想要什么，再安排一个具体阻碍",
    "冲突要升级：新信息、新代价或关系变化至少出现一种",
    "结尾保持开放，但要让读者看到故事下一步的压力",
    "故事小纲不追求文采，优先追求因果清楚和可扩写",
  ],
};

export async function renderOutlinePractice(root, ctx) {
  root.innerHTML = "";
  let assignment;
  try {
    assignment = await api.getTodayOutlinePractice();
  } catch (e) {
    root.appendChild(el("div", { class: "card" }, [
      el("h2", {}, "故事小纲"),
      el("div", { class: "empty" }, `生成故事小纲题失败：${e.message}`),
      el("button", { class: "btn", onclick: () => renderOutlinePractice(root, ctx) }, "重试"),
    ]));
    return;
  }

  if (!assignment.id) {
    renderCadence(root, ctx, assignment);
  } else if (assignment.submission) {
    renderResult(root, ctx, assignment, assignment.submission);
  } else {
    renderAssignment(root, ctx, assignment);
  }
}

function renderCadence(root, ctx, status) {
  root.innerHTML = "";
  const daysText = status.daysUntilDue > 0
    ? `下一次自动故事小纲：${status.nextAvailableDate}，还差 ${status.daysUntilDue} 天。`
    : "今天可以写一次故事小纲。";

  const startBtn = el("button", { class: "btn" }, "现在练一题");
  startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    startBtn.textContent = "生成中...";
    try {
      const next = await api.newOutlinePractice();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`生成失败：${e.message}`, "error");
      startBtn.disabled = false;
      startBtn.textContent = "现在练一题";
    }
  });

  root.appendChild(el("div", { class: "card" }, [
    el("h2", {}, "故事小纲"),
    el("div", { class: "muted" }, "每 3 天自动出现一次，用来训练故事结构和冲突设计。"),
    el("div", { class: "empty" }, daysText),
    el("div", { class: "row" }, [
      el("div", { class: "spacer" }),
      startBtn,
    ]),
  ]));
}

function renderAssignment(root, ctx, assignment) {
  root.innerHTML = "";

  const focusTag = assignment.focusDimension
    ? el("span", { class: "focus-tag" }, `本次专项：${assignment.focusDimension}`)
    : null;

  const changeBtn = el("button", { class: "btn secondary btn-sm" }, "换一题");
  changeBtn.addEventListener("click", async () => {
    changeBtn.disabled = true;
    changeBtn.textContent = "生成中...";
    try {
      const next = await api.newOutlinePractice();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`换题失败：${e.message}`, "error");
      changeBtn.disabled = false;
      changeBtn.textContent = "换一题";
    }
  });

  const card = el("div", { class: "card" }, [
    el("h2", {}, [assignment.title || "故事结构与冲突练习", focusTag]),
    el("div", { class: "row", style: "margin-top:2px;" }, [
      el("div", { class: "muted" }, `日期：${assignment.date} · 类型：${modeLabel(assignment.type)}`),
      el("div", { class: "spacer" }),
      changeBtn,
    ]),
  ]);

  if (assignment.scenario) {
    card.appendChild(el("div", { class: "scenario-box" }, [
      el("strong", {}, "冲突引子："),
      el("span", {}, assignment.scenario),
    ]));
  }

  const textarea = el("textarea", {
    rows: "12",
    placeholder: `请根据标题和冲突引子写一版故事小纲，目标 ${TARGET} 字，至少 ${MIN} 字。重点写清目标、阻碍、冲突升级和开放结尾...`,
  });
  const counter = el("div", { class: "char-count" }, `0 / ${MIN}（目标 ${TARGET}）`);
  const submitBtn = el("button", { class: "btn" }, "提交评分");
  submitBtn.disabled = true;

  textarea.addEventListener("input", () => {
    const count = charCount(textarea.value);
    counter.textContent = `${count} / ${MIN}（目标 ${TARGET}）`;
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

  const tips = assignment.focusDimension
    ? {
        ...OUTLINE_TIPS,
        focus: `${OUTLINE_TIPS.focus} 本次额外留意「${assignment.focusDimension}」。`,
      }
    : OUTLINE_TIPS;

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
  const nextBtn = el("button", { class: "btn" }, "再练一题");
  nextBtn.addEventListener("click", async () => {
    nextBtn.disabled = true;
    nextBtn.textContent = "生成中...";
    try {
      const next = await api.newOutlinePractice();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`生成失败：${e.message}`, "error");
      nextBtn.disabled = false;
      nextBtn.textContent = "再练一题";
    }
  });

  renderScoredResult(root, assignment, result, [
    nextBtn,
    el("div", { class: "spacer" }),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("daily") }, "回每日主练"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("history") }, "查看历史"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("stats") }, "查看统计"),
  ]);
}
