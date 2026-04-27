import { api } from "../api.js";
import { renderLine, renderRadar } from "../charts.js";
import { el } from "../utils.js";

export async function renderStats(root) {
  root.innerHTML = "";
  const data = await api.getStats();
  const series = data.series || [];

  if (!series.length) {
    root.appendChild(el("div", { class: "card" }, [
      el("h2", {}, "统计"),
      el("div", { class: "empty" }, "还没有数据，先写一篇吧。"),
    ]));
    return;
  }

  const radarCard = el("div", { class: "card" }, [el("h2", {}, "雷达图：最近一次 vs 全期均值")]);
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
    lineCard.appendChild(el("div", { class: "muted", style: "margin-top:8px;" }, "数据≥2 条后趋势会更清晰。"));
  }
  root.appendChild(lineCard);

  setTimeout(() => {
    renderRadar(radarCanvas, data.latest, data.average);
    renderLine(lineCanvas, series);
  }, 0);
}
