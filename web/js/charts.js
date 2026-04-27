import { DIMENSIONS } from "./utils.js";

const colors = [
  "#2f6feb", "#16a34a", "#dc2626", "#a855f7",
  "#f59e0b", "#0ea5e9", "#6b7280",
];

export function renderRadar(canvas, latest, average) {
  const labels = DIMENSIONS;
  const datasets = [];
  if (latest) {
    datasets.push({
      label: "最近一次",
      data: labels.map((d) => latest[d] ?? 0),
      backgroundColor: "rgba(47,111,235,0.2)",
      borderColor: "#2f6feb",
      borderWidth: 2,
      pointRadius: 3,
    });
  }
  if (average && Object.keys(average).length) {
    datasets.push({
      label: "全期均值",
      data: labels.map((d) => average[d] ?? 0),
      backgroundColor: "rgba(22,163,74,0.15)",
      borderColor: "#16a34a",
      borderWidth: 2,
      borderDash: [4, 4],
      pointRadius: 3,
    });
  }
  if (canvas._chart) canvas._chart.destroy();
  canvas._chart = new Chart(canvas, {
    type: "radar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: { min: 0, max: 10, ticks: { stepSize: 2, display: true } },
      },
      plugins: { legend: { position: "bottom" } },
    },
  });
}

export function renderLine(canvas, series) {
  const labels = series.map((s) => s.date);
  const datasets = DIMENSIONS.map((dim, i) => ({
    label: dim,
    data: series.map((s) => s.scores[dim] ?? null),
    borderColor: colors[i % colors.length],
    backgroundColor: colors[i % colors.length],
    spanGaps: true,
    tension: 0.25,
    pointRadius: 3,
  }));
  if (canvas._chart) canvas._chart.destroy();
  canvas._chart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { min: 0, max: 10 } },
      plugins: { legend: { position: "bottom" } },
    },
  });
}
