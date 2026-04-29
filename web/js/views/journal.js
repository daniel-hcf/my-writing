import { api } from "../api.js";
import { DIMENSIONS, charCount, el, escapeHtml, scoreClass, showToast } from "../utils.js";
import { renderRadar } from "../charts.js";

export async function renderJournal(root, ctx) {
  root.innerHTML = "";
  let assignment;
  try {
    assignment = await api.getJournalAssignment();
  } catch (e) {
    root.appendChild(
      el("div", { class: "card" }, [
        el("h2", {}, "每日随笔"),
        el("div", { class: "empty" }, "加载失败：" + e.message),
        el("button", { class: "btn", onclick: () => renderJournal(root, ctx) }, "重试"),
      ])
    );
    return;
  }

  if (assignment.submission) {
    renderJournalResult(root, ctx, assignment, assignment.submission);
  } else {
    renderJournalEditor(root, ctx, assignment);
  }
}

function renderJournalEditor(root, ctx, a) {
  root.innerHTML = "";

  const ta = el("textarea", {
    rows: "18",
    placeholder: "今天想写点什么？随心而写，不限主题、不限字数...",
  });
  const counter = el("div", { class: "char-count" }, "0 字");

  ta.addEventListener("input", () => {
    const n = charCount(ta.value);
    counter.textContent = `${n} 字`;
    submitBtn.disabled = n < 1;
  });

  const submitBtn = el("button", { class: "btn" }, "提交 AI 点评");
  submitBtn.disabled = true;

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "正在点评...";
    try {
      const result = await api.submit(a.id, ta.value);
      renderJournalResult(root, ctx, a, result);
    } catch (e) {
      showToast("点评失败：" + e.message, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "提交 AI 点评";
    }
  });

  const card = el("div", { class: "card" }, [
    el("h2", {}, "每日随笔"),
    el("div", { class: "muted" }, `${a.date} · 自由写作`),
    ta,
    el("div", { class: "row", style: "margin-top:8px;" }, [
      counter,
      el("div", { class: "spacer" }),
      submitBtn,
    ]),
  ]);

  root.appendChild(card);
}

function renderJournalResult(root, ctx, assignment, result) {
  root.innerHTML = "";

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "row" }, [
      el("span", {}, `📅 ${assignment.date} · 每日随笔`),
      el("span", { class: "spacer" }),
      el("span", { class: "focus-tag", style: "background:#e6f4ea;color:#16a34a;" }, "✓ 已完成"),
    ]),
  ]));

  const scoresCard = el("div", { class: "card" }, [el("h2", {}, "本次评分")]);
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

  const radarCard = el("div", { class: "card" }, [el("h2", {}, "维度雷达图")]);
  const wrap = el("div", { class: "chart-wrap" });
  const canvas = el("canvas");
  wrap.appendChild(canvas);
  radarCard.appendChild(wrap);
  root.appendChild(radarCard);
  setTimeout(() => renderRadar(canvas, result.scores, null), 0);

  const fbCard = el("div", { class: "card" }, [el("h2", {}, "维度点评")]);
  for (const d of DIMENSIONS) {
    const f = result.feedback?.[d] || {};
    fbCard.appendChild(
      el("details", { class: "dim-detail" }, [
        el("summary", {}, `${d} · ${result.scores[d] ?? "-"} 分`),
        el("div", { class: "feedback-block" }, [
          el("div", {}, [el("span", { class: "label" }, "优点："), f["优点"] || "—"]),
          el("div", {}, [el("span", { class: "label" }, "不足："), f["不足"] || "—"]),
          el("div", {}, [el("span", { class: "label" }, "建议："), f["建议"] || "—"]),
        ]),
      ])
    );
  }
  root.appendChild(fbCard);

  root.appendChild(
    el("div", { class: "card row" }, [
      el("button", { class: "btn secondary", onclick: () => ctx.navigate("history") }, "查看历史"),
      el("div", { class: "spacer" }),
      el("button", { class: "btn secondary", onclick: () => ctx.navigate("stats") }, "查看统计"),
    ])
  );
}
