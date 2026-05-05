import { api } from "../api.js";
import { DIMENSIONS, el, escapeHtml, modeLabel, scoreClass, showToast } from "../utils.js";

const GROUP_ORDER = ["daily", "outline_practice", "image_practice", "journal"];

export async function renderHistory(root) {
  root.innerHTML = "";
  const list = await api.listSubmissions(100);

  const card = el("div", { class: "card" }, [el("h2", {}, "历史记录")]);
  if (!list.length) {
    card.appendChild(el("div", { class: "empty" }, "还没有写作记录，先去开始第一篇吧。"));
    root.appendChild(card);
    return;
  }

  const groups = new Map(GROUP_ORDER.map((mode) => [mode, []]));
  for (const item of list) {
    if (!groups.has(item.assignmentType)) groups.set(item.assignmentType, []);
    groups.get(item.assignmentType).push(item);
  }

  for (const mode of GROUP_ORDER) {
    const items = groups.get(mode) || [];
    if (!items.length) continue;
    card.appendChild(el("div", { class: "history-group-title" }, modeLabel(mode)));
    const ul = el("ul", { class: "history-list" });
    for (const item of items) {
      ul.appendChild(el("li", { onclick: () => showDetail(root, item.id) }, [
        el("div", { class: "row" }, [
          el("strong", {}, item.date),
          el("span", { class: "muted" }, ` · ${modeLabel(item.assignmentType)}`),
          el("span", { class: "spacer" }),
          el("span", {}, `总分 ${item.totalScore}`),
        ]),
        el("div", { class: "muted", style: "font-size:13px;" }, item.assignmentTitle || ""),
      ]));
    }
    card.appendChild(ul);
  }

  root.appendChild(card);
}

async function showDetail(root, sid) {
  const detail = await api.getSubmission(sid);
  let assignment = null;
  try {
    assignment = await api.getAssignment(detail.assignmentId);
  } catch {}

  root.innerHTML = "";
  const back = el("button", {
    class: "btn secondary",
    onclick: () => renderHistory(root),
  }, "返回列表");

  const delBtn = el("button", { class: "btn danger btn-sm" }, "删除记录");
  delBtn.addEventListener("click", async () => {
    if (!confirm("确定删除这条记录？删除后可重新提交。")) return;
    delBtn.disabled = true;
    try {
      await api.deleteSubmission(sid);
      renderHistory(root);
    } catch (e) {
      showToast(`删除失败：${e.message}`, "error");
      delBtn.disabled = false;
    }
  });

  root.appendChild(el("div", { class: "card row" }, [back, el("div", { class: "spacer" }), delBtn]));

  if (assignment) {
    const card = el("div", { class: "card" }, [
      el("h2", {}, assignment.title || "作业"),
      el("div", { class: "muted" }, `日期：${assignment.date} · 类型：${modeLabel(assignment.type)}`),
    ]);
    if (assignment.type === "image_practice" && assignment.imageData) {
      card.appendChild(el("img", { class: "assignment-image", src: assignment.imageData, alt: "题图" }));
    }
    if (assignment.scenario) {
      const label = assignment.type === "daily"
        ? "故事种子："
        : assignment.type === "outline_practice"
          ? "冲突引子："
          : "";
      card.appendChild(el("div", { class: "scenario-box" }, [
        label ? el("strong", {}, label) : null,
        el("span", {}, assignment.scenario),
      ]));
    }
    root.appendChild(card);
  }

  root.appendChild(el("div", { class: "card" }, [
    el("h2", {}, "我的作品"),
    el("div", { class: "muted" }, `字数：${detail.charCount}`),
    el("div", { class: "scenario-box", html: escapeHtml(detail.content) }),
  ]));

  const scoreCard = el("div", { class: "card" }, [el("h2", {}, "评分")]);
  const grid = el("div", { class: "scores-grid" });
  for (const dim of DIMENSIONS) {
    const score = detail.scores[dim] ?? null;
    const cls = score !== null ? scoreClass(score) : "";
    grid.appendChild(el("div", { class: `score-cell${cls ? ` ${cls}-bg` : ""}` }, [
      el("span", { class: "dim" }, dim),
      el("span", { class: `val${cls ? ` ${cls}` : ""}` }, score !== null ? String(score) : "-"),
    ]));
  }
  scoreCard.appendChild(grid);
  if (detail.overall) {
    scoreCard.appendChild(el("p", { class: "muted", style: "margin-top:12px;" }, detail.overall));
  }
  root.appendChild(scoreCard);

  const fbCard = el("div", { class: "card" }, [el("h2", {}, "维度点评")]);
  for (const dim of DIMENSIONS) {
    const feedback = detail.feedback?.[dim] || {};
    fbCard.appendChild(el("details", { class: "dim-detail" }, [
      el("summary", {}, `${dim} · ${detail.scores[dim] ?? "-"}`),
      el("div", { class: "feedback-block" }, [
        el("div", {}, [el("span", { class: "label" }, "优点："), feedback["优点"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "不足："), feedback["不足"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "建议："), feedback["建议"] || "—"]),
      ]),
    ]));
  }
  root.appendChild(fbCard);
}
