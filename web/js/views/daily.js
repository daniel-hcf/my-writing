import { api } from "../api.js";
import { charCount, el, modeLabel, showToast } from "../utils.js";
import { buildDraftControls, confirmDiscardDraft, createDraftController, updateDraftStatus } from "./draft_common.js";
import { buildTipsPanel, renderScoredResult } from "./practice_common.js";

const MIN = 300;
const TARGET = "300~800";
const STORY_SEED_TIPS = {
  focus: "把一句故事种子扩写成一场有钩子、有压迫、有高级爽点和追读余味的网文片段。",
  skills: [
    "开头先给读者一个必须继续看的钩子：信息差、规则漏洞、身份错位、危机或资源诱惑。",
    "中段让压迫持续推进，不要让主角太早脱困，也不要只停在解释设定。",
    "反击前先铺出读者期待，让主角有可见的筹码、判断、误导或主动设局。",
    "结尾兑现一个爽点后，再留一个局中局、新变化或新威胁制造追读。",
  ],
};

export async function renderDaily(root, ctx) {
  root.innerHTML = "";
  let assignment;
  try {
    assignment = await api.getTodayAssignment();
  } catch (e) {
    root.appendChild(el("div", { class: "card" }, [
      el("h2", {}, "每日主练"),
      el("div", { class: "empty" }, `生成作业失败：${e.message}`),
      el("button", { class: "btn", onclick: () => renderDaily(root, ctx) }, "重试"),
    ]));
    return;
  }

  if (assignment.needsGeneration) {
    renderGenerationPrompt(root, ctx);
  } else if (assignment.submission) {
    renderResult(root, ctx, assignment, assignment.submission);
  } else {
    renderAssignment(root, ctx, assignment);
  }
}

function renderGenerationPrompt(root, ctx) {
  root.innerHTML = "";

  const input = el("input", {
    type: "text",
    placeholder: "都市异能、修仙宗门、无限流副本、末世基地",
    style: "min-width: min(100%, 420px);",
  });
  const generateBtn = el("button", { class: "btn" }, "生成节奏题");
  const skipBtn = el("button", { class: "btn secondary" }, "随机题材");

  const generate = async (useInput = true) => {
    const intent = useInput ? input.value.trim() : "";
    generateBtn.disabled = true;
    skipBtn.disabled = true;
    generateBtn.textContent = "正在生成...";
    try {
      const next = await api.newAssignment(intent);
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`生成题目失败：${e.message}`, "error");
      generateBtn.disabled = false;
      skipBtn.disabled = false;
      generateBtn.textContent = "生成节奏题";
    }
  };

  generateBtn.addEventListener("click", () => generate(true));
  skipBtn.addEventListener("click", () => generate(false));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") generate(true);
  });

  root.appendChild(el("div", { class: "card" }, [
    el("h2", {}, "每日主练"),
    el("p", { class: "muted" }, "今天想用什么题材/场景练高级网文节奏？"),
    input,
    el("div", { class: "row", style: "margin-top:12px;" }, [
      generateBtn,
      skipBtn,
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
    if (!confirmDiscardDraft(assignment, textarea)) return;
    renderGenerationPrompt(root, ctx);
  });

  const card = el("div", { class: "card" }, [
    el("h2", {}, [assignment.title || "今日故事种子", focusTag]),
    el("div", { class: "row", style: "margin-top:2px;" }, [
      el("div", { class: "muted" }, `日期：${assignment.date} · 类型：${modeLabel(assignment.type)}`),
      el("div", { class: "spacer" }),
      changeBtn,
    ]),
  ]);
  if (assignment.scenario) {
    card.appendChild(el("div", { class: "scenario-box" }, [
      el("strong", {}, "故事种子："),
      el("span", {}, assignment.scenario),
    ]));
  }

  const textarea = el("textarea", {
    rows: "16",
    placeholder: `请把故事种子扩写成一场完整小说片段，目标 ${TARGET} 字，至少 ${MIN} 字...`,
  });
  textarea.value = assignment.draftContent || "";

  const counter = el("div", { class: "char-count" });
  const submitBtn = el("button", { class: "btn" }, "提交评分");
  const updateCount = () => {
    const count = charCount(textarea.value);
    counter.textContent = `${count} / ${MIN}（目标 ${TARGET}）`;
    counter.classList.toggle("ok", count >= MIN);
    submitBtn.disabled = count < MIN;
  };
  textarea.addEventListener("input", updateCount);
  updateCount();

  const draftStatus = el("div", { class: "draft-status muted" });
  const draftController = createDraftController(assignment, textarea, (state) => updateDraftStatus(draftStatus, state));
  if (assignment.draftContent) updateDraftStatus(draftStatus, "saved");

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "正在评分...";
    try {
      await draftController.flush();
      const result = await api.submit(assignment.id, textarea.value);
      api.deleteDraft(assignment.id).catch(() => {});
      renderResult(root, ctx, assignment, result);
    } catch (e) {
      showToast(`评分失败：${e.message}`, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "提交评分";
    }
  });

  const tips = assignment.focusDimension
    ? {
        ...STORY_SEED_TIPS,
        focus: `${STORY_SEED_TIPS.focus} 本次额外留意「${assignment.focusDimension}」。`,
      }
    : STORY_SEED_TIPS;
  const writingCol = el("div", {}, [
    textarea,
    counter,
    el("div", { class: "row", style: "margin-top:8px;" }, [
      ...buildDraftControls(draftController, draftStatus),
      el("div", { class: "spacer" }),
      submitBtn,
    ]),
  ]);

  card.appendChild(el("div", { class: "writing-layout" }, [writingCol, buildTipsPanel(assignment.focusDimension, tips)]));
  root.appendChild(card);
}

function renderResult(root, ctx, assignment, result) {
  const repeatBtn = el("button", { class: "btn" }, "再写同一题");
  repeatBtn.addEventListener("click", async () => {
    repeatBtn.disabled = true;
    repeatBtn.textContent = "正在准备...";
    try {
      const next = await api.repeatDailyAssignment(assignment.id);
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`创建练习失败：${e.message}`, "error");
      repeatBtn.disabled = false;
      repeatBtn.textContent = "再写同一题";
    }
  });

  const newPromptBtn = el("button", { class: "btn secondary" }, "换题材再练节奏");
  newPromptBtn.addEventListener("click", () => renderGenerationPrompt(root, ctx));

  renderScoredResult(root, assignment, result, [
    repeatBtn,
    newPromptBtn,
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("outline_practice") }, "去写故事小纲"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("image_practice") }, "去看图写作"),
    el("div", { class: "spacer" }),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("history") }, "查看历史"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("stats") }, "查看统计"),
  ]);
}
