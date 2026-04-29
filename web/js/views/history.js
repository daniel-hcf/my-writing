import { api } from "../api.js";
import { DIMENSIONS, el, escapeHtml, scoreClass, showToast } from "../utils.js";

export async function renderHistory(root) {
  root.innerHTML = "";
  const list = await api.listSubmissions(100);

  const card = el("div", { class: "card" }, [el("h2", {}, "历史记录")]);
  if (!list.length) {
    card.appendChild(el("div", { class: "empty" }, "还没有写作记录，去「今日一练」开始第一篇吧。"));
    root.appendChild(card);
    return;
  }
  const ul = el("ul", { class: "history-list" });
  for (const s of list) {
    const typeLabel = s.assignmentType === "image" ? "看图"
      : s.assignmentType === "journal" ? "随笔" : "场景";
    const li = el("li", {
      onclick: () => showDetail(root, s.id),
    }, [
      el("div", { class: "row" }, [
        el("strong", {}, s.date),
        el("span", { class: "muted" }, ` · ${typeLabel}`),
        el("span", { class: "spacer" }),
        el("span", {}, `总分 ${s.totalScore}`),
      ]),
      el("div", { class: "muted", style: "font-size:13px;" }, s.assignmentTitle || ""),
    ]);
    ul.appendChild(li);
  }
  card.appendChild(ul);
  root.appendChild(card);
}

async function showDetail(root, sid) {
  const detail = await api.getSubmission(sid);
  let assignment = null;
  try { assignment = await api.getAssignment(detail.assignmentId); } catch {}

  root.innerHTML = "";
  const back = el("button", {
    class: "btn secondary",
    onclick: () => renderHistory(root),
  }, "← 返回列表");

  const delBtn = el("button", { class: "btn danger btn-sm" }, "删除记录");
  delBtn.addEventListener("click", async () => {
    if (!confirm("确定删除这条记录？删除后可重新提交。")) return;
    delBtn.disabled = true;
    try {
      await api.deleteSubmission(sid);
      renderHistory(root);
    } catch (e) {
      showToast("删除失败：" + e.message, "error");
      delBtn.disabled = false;
    }
  });

  root.appendChild(el("div", { class: "card row" }, [back, el("div", { class: "spacer" }), delBtn]));

  if (assignment) {
    const card = el("div", { class: "card" }, [
      el("h2", {}, assignment.title || "作业"),
      el("div", { class: "muted" },
        `日期：${assignment.date} · 类型：${assignment.type === "image" ? "看图写作" : "场景写作"}`),
    ]);
    if (assignment.type === "image" && assignment.imageData) {
      card.appendChild(el("img", { class: "assignment-image", src: assignment.imageData }));
    }
    if (assignment.scenario) {
      card.appendChild(el("div", { class: "scenario-box", html: escapeHtml(assignment.scenario) }));
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
  for (const d of DIMENSIONS) {
    const s = detail.scores[d] ?? null;
    const cls = s !== null ? scoreClass(s) : "";
    grid.appendChild(el("div", { class: `score-cell${cls ? ` ${cls}-bg` : ""}` }, [
      el("span", { class: "dim" }, d),
      el("span", { class: `val${cls ? ` ${cls}` : ""}` }, s !== null ? String(s) : "-"),
    ]));
  }
  scoreCard.appendChild(grid);
  if (detail.overall) {
    scoreCard.appendChild(el("p", { class: "muted", style: "margin-top:12px;" }, detail.overall));
  }
  root.appendChild(scoreCard);

  const fbCard = el("div", { class: "card" }, [el("h2", {}, "维度点评")]);
  for (const d of DIMENSIONS) {
    const f = detail.feedback?.[d] || {};
    fbCard.appendChild(el("details", { class: "dim-detail" }, [
      el("summary", {}, `${d} · ${detail.scores[d] ?? "-"} 分`),
      el("div", { class: "feedback-block" }, [
        el("div", {}, [el("span", { class: "label" }, "优点："), f["优点"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "不足："), f["不足"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "建议："), f["建议"] || "—"]),
      ]),
    ]));
  }
  root.appendChild(fbCard);
}
