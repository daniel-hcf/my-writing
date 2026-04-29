import { api } from "../api.js";
import { GENERAL_TIPS, TIPS } from "../tips.js";
import { DIMENSIONS, charCount, el, escapeHtml, scoreClass, showToast } from "../utils.js";
import { renderRadar } from "../charts.js";

const MIN = 500;

export async function renderDaily(root, ctx) {
  root.innerHTML = "";
  let assignment;
  try {
    assignment = await api.getTodayAssignment();
  } catch (e) {
    root.appendChild(
      el("div", { class: "card" }, [
        el("h2", {}, "今日一练"),
        el("div", { class: "empty" }, "生成作业失败：" + e.message),
        el("button", { class: "btn", onclick: () => renderDaily(root, ctx) }, "重试"),
      ])
    );
    return;
  }
  // 今天已经提交过 → 直接展示评价，不再显示写作框
  if (assignment.submission) {
    renderResult(root, ctx, assignment, assignment.submission);
  } else {
    renderAssignment(root, ctx, assignment);
  }
}

function renderAssignment(root, ctx, a) {
  root.innerHTML = "";

  const focusTag = a.focusDimension
    ? el("span", { class: "focus-tag" }, "本次专项：" + a.focusDimension)
    : null;

  const changeBtn = el("button", { class: "btn secondary btn-sm" }, "换一道");
  changeBtn.addEventListener("click", async () => {
    changeBtn.disabled = true;
    changeBtn.textContent = "生成中...";
    try {
      const next = await api.newAssignment();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast("换题失败：" + e.message, "error");
      changeBtn.disabled = false;
      changeBtn.textContent = "换一道";
    }
  });

  const card = el("div", { class: "card" }, [
    el("h2", {}, [a.title || "今日写作练习", focusTag]),
    el("div", { class: "row", style: "margin-top:2px;" }, [
      el("div", { class: "muted" }, `日期：${a.date} · 类型：${a.type === "image" ? "看图写作" : "场景写作"}`),
      el("div", { class: "spacer" }),
      changeBtn,
    ]),
  ]);

  if (a.type === "image" && a.imageData) {
    card.appendChild(el("img", { class: "assignment-image", src: a.imageData, alt: "题图" }));
  }
  if (a.scenario) {
    card.appendChild(el("div", { class: "scenario-box", html: escapeHtml(a.scenario) }));
  }

  const ta = el("textarea", {
    rows: "16",
    placeholder: `请在此处写作，至少 ${MIN} 字...`,
  });
  const counter = el("div", { class: "char-count" }, `0 / ${MIN}`);
  const submitBtn = el("button", { class: "btn" }, "提交评分");
  submitBtn.disabled = true;

  ta.addEventListener("input", () => {
    const n = charCount(ta.value);
    counter.textContent = `${n} / ${MIN}`;
    counter.classList.toggle("ok", n >= MIN);
    submitBtn.disabled = n < MIN;
  });

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "正在评分...";
    try {
      const result = await api.submit(a.id, ta.value);
      renderResult(root, ctx, a, result);
    } catch (e) {
      showToast("评分失败：" + e.message, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "提交评分";
    }
  });

  // 写作区 + 技巧侧边栏
  const tips = TIPS[a.focusDimension] || GENERAL_TIPS;
  const tipsPanel = el("div", { class: "tips-panel" }, [
    el("h3", {}, a.focusDimension ? `本次专项：${a.focusDimension}` : "本次综合训练"),
    el("div", { class: "tips-focus" }, tips.focus),
    el("h3", {}, "写作技巧参考"),
    el("ul", {}, tips.skills.map((s) => el("li", {}, s))),
  ]);

  const writingCol = el("div", {}, [
    ta,
    counter,
    el("div", { class: "row", style: "margin-top:8px;" }, [
      el("div", { class: "spacer" }),
      submitBtn,
    ]),
  ]);

  card.appendChild(el("div", { class: "writing-layout" }, [writingCol, tipsPanel]));
  root.appendChild(card);
}

function renderResult(root, ctx, assignment, result) {
  root.innerHTML = "";

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "row" }, [
      el("span", {}, `📅 ${assignment.date} · ${assignment.title || "今日练习"}`),
      el("span", { class: "spacer" }),
      el("span", { class: "focus-tag", style: "background:#e6f4ea;color:#16a34a;" }, "✓ 已完成"),
    ]),
  ]));

  const scoresCard = el("div", { class: "card" }, [
    el("h2", {}, "本次评分"),
  ]);
  const grid = el("div", { class: "scores-grid" });
  for (const d of DIMENSIONS) {
    const s = result.scores[d] ?? null;
    const cls = s !== null ? scoreClass(s) : "";
    grid.appendChild(
      el("div", { class: `score-cell${cls ? ` ${cls}-bg` : ""}` }, [
        el("span", { class: "dim" }, d),
        el("span", { class: `val${cls ? ` ${cls}` : ""}` }, s !== null ? String(s) : "-"),
      ])
    );
  }
  scoresCard.appendChild(grid);
  if (result.overall) {
    scoresCard.appendChild(el("p", { class: "muted", style: "margin-top:12px;" }, result.overall));
  }
  root.appendChild(scoresCard);

  const radarCard = el("div", { class: "card" }, [el("h2", {}, "本次维度雷达图")]);
  const wrap = el("div", { class: "chart-wrap" });
  const canvas = el("canvas");
  wrap.appendChild(canvas);
  radarCard.appendChild(wrap);
  root.appendChild(radarCard);
  setTimeout(() => renderRadar(canvas, result.scores, null), 0);

  const fbCard = el("div", { class: "card" }, [el("h2", {}, "维度点评")]);
  for (const d of DIMENSIONS) {
    const f = result.feedback?.[d] || {};
    const det = el("details", { class: "dim-detail" }, [
      el("summary", {}, `${d} · ${result.scores[d] ?? "-"} 分`),
      el("div", { class: "feedback-block" }, [
        el("div", {}, [el("span", { class: "label" }, "优点："), f["优点"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "不足："), f["不足"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "建议："), f["建议"] || "—"]),
      ]),
    ]);
    fbCard.appendChild(det);
  }
  root.appendChild(fbCard);

  const practiceAgainBtn = el("button", { class: "btn" }, "再练一篇");
  practiceAgainBtn.addEventListener("click", async () => {
    practiceAgainBtn.disabled = true;
    practiceAgainBtn.textContent = "生成中...";
    try {
      const next = await api.newAssignment();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast("生成失败：" + e.message, "error");
      practiceAgainBtn.disabled = false;
      practiceAgainBtn.textContent = "再练一篇";
    }
  });

  const actions = el("div", { class: "card row" }, [
    practiceAgainBtn,
    el("div", { class: "spacer" }),
    el("button", {
      class: "btn secondary",
      onclick: () => ctx.navigate("history"),
    }, "查看历史"),
    el("button", {
      class: "btn secondary",
      onclick: () => ctx.navigate("stats"),
    }, "查看统计"),
  ]);
  root.appendChild(actions);
}
