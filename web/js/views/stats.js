import { api } from "../api.js";
import { renderLine, renderRadar } from "../charts.js";
import { el, modeLabel } from "../utils.js";

const MODES = [
  { value: "all", label: "全部练习" },
  { value: "daily", label: "每日一练" },
  { value: "image_practice", label: "看图写作" },
];

export async function renderStats(root) {
  await renderStatsMode(root, "all");
}

async function renderStatsMode(root, mode) {
  root.innerHTML = "";
  const data = await api.getStats(mode);
  const series = data.series || [];

  const filterBar = el("div", { class: "card row segmented-row" }, [
    el("span", { class: "muted" }, "统计范围"),
    el("div", { class: "segmented" }, MODES.map((item) => {
      const btn = el("button", {
        class: `segmented-btn${item.value === mode ? " active" : ""}`,
        onclick: () => renderStatsMode(root, item.value),
      }, item.label);
      return btn;
    })),
  ]);
  root.appendChild(filterBar);

  if (!series.length) {
    const scopeLabel = mode === "all" ? "当前统计范围" : modeLabel(mode);
    root.appendChild(el("div", { class: "card" }, [
      el("h2", {}, "统计"),
      el("div", { class: "empty" }, `${scopeLabel} 还没有数据，先写一篇吧。`),
    ]));
    return;
  }

  const radarCard = el("div", { class: "card" }, [
    el("h2", {}, `雷达图：最近一次 vs ${mode === "all" ? "全部练习" : modeLabel(mode)}`),
  ]);
  const radarWrap = el("div", { class: "chart-wrap" });
  const radarCanvas = el("canvas");
  radarWrap.appendChild(radarCanvas);
  radarCard.appendChild(radarWrap);
  root.appendChild(radarCard);

  const lineCard = el("div", { class: "card" }, [el("h2", {}, "各维度分数趋势")]);
  const lineWrap = el("div", { class: "chart-wrap" });
  const lineCanvas = el("canvas");
  lineWrap.appendChild(lineCanvas);
  lineCard.appendChild(lineWrap);
  if (series.length < 2) {
    lineCard.appendChild(el("div", { class: "muted", style: "margin-top:8px;" }, "数据至少 2 条后趋势会更清晰。"));
  }
  root.appendChild(lineCard);

  setTimeout(() => {
    renderRadar(radarCanvas, data.latest, data.average);
    renderLine(lineCanvas, series);
  }, 0);
}
