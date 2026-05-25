import { renderRadar } from "../charts.js";
import { DIMENSIONS, el, scoreClass } from "../utils.js";

export function buildTipsPanel(focusDimension, tips) {
  return el("div", { class: "tips-panel" }, [
    el("h3", {}, focusDimension ? `本次专项：${focusDimension}` : "本次综合训练"),
    el("div", { class: "tips-focus" }, tips.focus),
    el("h3", {}, "写作技巧参考"),
    el("ul", {}, tips.skills.map((item) => el("li", {}, item))),
  ]);
}

export function renderMarketSignals(result) {
  const items = [];
  if (result.marketScore !== null && result.marketScore !== undefined) {
    items.push(el("div", {}, [el("span", { class: "label" }, "市场追读："), `${result.marketScore} / 10`]));
  }
  if (result.trainingScore !== null && result.trainingScore !== undefined) {
    items.push(el("div", {}, [el("span", { class: "label" }, "练习完成："), `${result.trainingScore} / 10`]));
  }
  if (result.fatalProblem) {
    items.push(el("div", {}, [el("span", { class: "label" }, "最致命问题："), result.fatalProblem]));
  }
  if (result.bestPart) {
    items.push(el("div", {}, [el("span", { class: "label" }, "最佳部分："), result.bestPart]));
  }
  if (result.rewriteTask) {
    const task = result.rewriteTask;
    const taskText = [task.target, task.requirement, task.wordLimit].filter(Boolean).join("；");
    if (taskText) {
      items.push(el("div", {}, [el("span", { class: "label" }, "下一稿任务："), taskText]));
    }
  }
  return items.length ? el("div", { class: "feedback-block", style: "margin-top:12px;" }, items) : null;
}

export function renderScoredResult(root, assignment, result, footerActions = []) {
  root.innerHTML = "";

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "row" }, [
      el("span", {}, `📝 ${assignment.date} · ${assignment.title || "写作练习"}`),
      el("span", { class: "spacer" }),
      el("span", { class: "focus-tag", style: "background:#e6f4ea;color:#16a34a;" }, "已完成"),
    ]),
  ]));

  const scoresCard = el("div", { class: "card" }, [el("h2", {}, "本次评分")]);
  const grid = el("div", { class: "scores-grid" });
  for (const dim of DIMENSIONS) {
    const score = result.scores[dim] ?? null;
    const cls = score !== null ? scoreClass(score) : "";
    grid.appendChild(
      el("div", { class: `score-cell${cls ? ` ${cls}-bg` : ""}` }, [
        el("span", { class: "dim" }, dim),
        el("span", { class: `val${cls ? ` ${cls}` : ""}` }, score !== null ? String(score) : "-"),
      ])
    );
  }
  scoresCard.appendChild(grid);
  const marketSignals = renderMarketSignals(result);
  if (marketSignals) {
    scoresCard.appendChild(marketSignals);
  }
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
  for (const dim of DIMENSIONS) {
    const feedback = result.feedback?.[dim] || {};
    fbCard.appendChild(el("details", { class: "dim-detail" }, [
      el("summary", {}, `${dim} · ${result.scores[dim] ?? "-"}`),
      el("div", { class: "feedback-block" }, [
        el("div", {}, [el("span", { class: "label" }, "优点："), feedback["优点"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "不足："), feedback["不足"] || "—"]),
        el("div", {}, [el("span", { class: "label" }, "建议："), feedback["建议"] || "—"]),
      ]),
    ]));
  }
  root.appendChild(fbCard);

  if (footerActions.length) {
    root.appendChild(el("div", { class: "card row" }, footerActions));
  }
}
