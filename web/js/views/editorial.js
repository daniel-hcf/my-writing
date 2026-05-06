import { api } from "../api.js";
import { el, escapeHtml, showToast } from "../utils.js";

const CHANNELS = {
  all: "全部",
  social: "当前社会热点",
  story: "故事素材雷达",
};

export async function renderEditorial(root) {
  root.innerHTML = "";
  const detailMatch = location.hash.match(/^#\/materials\/(\d+)/);
  if (detailMatch) {
    await renderMaterialDetail(root, Number(detailMatch[1]));
    return;
  }
  await renderDashboard(root);
}

async function renderDashboard(root) {
  root.innerHTML = "";
  const [materials, briefs] = await Promise.all([api.listMaterials("", 80), api.listBriefs(10)]);
  const selected = { channel: "all" };

  const listNode = el("div");
  const tabs = el("div", { class: "row material-tabs" });
  for (const [channel, label] of Object.entries(CHANNELS)) {
    const btn = el("button", { class: `btn btn-sm ${channel === "all" ? "" : "secondary"}` }, label);
    btn.addEventListener("click", () => {
      selected.channel = channel;
      Array.from(tabs.children).forEach((node) => node.classList.add("secondary"));
      btn.classList.remove("secondary");
      renderMaterialList(listNode, materials, selected.channel);
    });
    tabs.appendChild(btn);
  }

  const fetchBtn = el("button", { class: "btn secondary" }, "立即抓取RSS");
  fetchBtn.addEventListener("click", async () => {
    fetchBtn.disabled = true;
    fetchBtn.textContent = "抓取中...";
    try {
      const result = await api.fetchEditorialSources();
      showToast(`抓取完成：新增 ${result.inserted} 条素材`);
      await renderDashboard(root);
    } catch (e) {
      showToast(`抓取失败：${e.message}`, "error");
    }
  });

  const briefBtn = el("button", { class: "btn" }, "重新生成今日简报");
  briefBtn.addEventListener("click", async () => {
    briefBtn.disabled = true;
    briefBtn.textContent = "生成中...";
    try {
      const brief = await api.generateTodayBrief();
      showToast(`今日简报已重新生成：${formatDateTime(brief.createdAt)}`);
      await renderDashboard(root);
    } catch (e) {
      showToast(`生成失败：${e.message}`, "error");
      briefBtn.disabled = false;
      briefBtn.textContent = "重新生成今日简报";
    }
  });

  const card = el("div", { class: "card" }, [
    el("h2", {}, "素材简报"),
    el("div", { class: "muted" }, "每天从 RSS 收集两类素材：当前社会热点，以及可转化成小说的故事素材。"),
    el("div", { class: "row", style: "margin-top:12px;" }, [fetchBtn, briefBtn]),
    tabs,
    listNode,
  ]);
  root.appendChild(card);
  renderMaterialList(listNode, materials, selected.channel);

  root.appendChild(renderBriefs(briefs));
}

function renderMaterialList(root, materials, channel) {
  const filtered = channel === "all" ? materials : materials.filter((item) => item.channel === channel);
  root.innerHTML = "";
  if (!filtered.length) {
    root.appendChild(el("div", { class: "empty" }, "还没有素材。可以先去设置页导入推荐源包，再立即抓取 RSS。"));
    return;
  }
  filtered.forEach((item) => {
    const node = el("article", { class: "material-item" }, [
      el("div", { class: "row" }, [
        el("strong", {}, item.title),
        el("div", { class: "spacer" }),
        el("span", { class: "focus-tag" }, item.channelLabel),
      ]),
      el("div", { class: "muted" }, `${item.sourceName || "未知来源"}${item.aiCategory ? ` · ${item.aiCategory}` : ""}`),
      el("p", {}, item.displaySummary || item.aiSummary || item.summary || "暂无摘要"),
      item.aiReason ? el("p", { class: "muted" }, `入选理由：${item.aiReason}`) : null,
      item.fictionFit || item.fictionAngle
        ? el("p", { class: "fiction-note" }, `小说素材适配度：${item.fictionFit || "未判断"}${item.fictionAngle ? ` · ${item.fictionAngle}` : ""}`)
        : null,
      el("div", { class: "row" }, [
        el("button", { class: "btn btn-sm", onclick: () => openMaterial(item.id) }, "深读"),
        el("a", { class: "btn secondary btn-sm", href: item.url, target: "_blank" }, "原文"),
      ]),
    ]);
    root.appendChild(node);
  });
}

function renderBriefs(briefs) {
  const body = el("div");
  if (!briefs.length) {
    body.appendChild(el("div", { class: "empty" }, "还没有历史简报。"));
  } else {
    briefs.forEach((brief) => {
      const sendBtn = el("button", { class: "btn secondary btn-sm" }, brief.status === "sent" ? "重新发送" : "发送邮件");
      sendBtn.addEventListener("click", async () => {
        const originalText = sendBtn.textContent;
        sendBtn.disabled = true;
        sendBtn.textContent = brief.status === "sent" ? "重新发送中..." : "发送中...";
        try {
          await api.sendBrief(brief.id);
          showToast(brief.status === "sent" ? "邮件已重新发送" : "邮件已发送");
          location.reload();
        } catch (e) {
          showToast(`发送失败：${e.message}`, "error");
          sendBtn.disabled = false;
          sendBtn.textContent = originalText;
        }
      });
      body.appendChild(el("div", { class: "brief-row" }, [
        el("div", {}, [
          el("strong", {}, brief.subject || brief.date),
          el("div", { class: "muted" }, [
            `状态：${brief.status}${brief.error ? ` · ${brief.error}` : ""}`,
            el("br"),
            `生成于：${formatDateTime(brief.createdAt)}${brief.sentAt ? ` · 发送于：${formatDateTime(brief.sentAt)}` : ""}`,
          ]),
        ]),
        sendBtn,
      ]));
    });
  }
  return el("div", { class: "card" }, [el("h2", {}, "历史简报"), body]);
}

function formatDateTime(value) {
  if (!value) return "未知";
  return value.replace("T", " ").slice(0, 19);
}

async function renderMaterialDetail(root, id) {
  const item = await api.getMaterial(id);
  const deepNode = el("div");
  const ideasNode = el("div");
  renderJsonBlock(deepNode, item.deepDive, "还没有深挖结果。");
  renderJsonBlock(ideasNode, item.storyIdeas, "还没有写作灵感。");

  const deepBtn = el("button", { class: "btn" }, "深挖这条");
  deepBtn.addEventListener("click", async () => {
    deepBtn.disabled = true;
    deepBtn.textContent = "深挖中...";
    try {
      const data = await api.deepDiveMaterial(id);
      renderJsonBlock(deepNode, data, "还没有深挖结果。");
    } catch (e) {
      showToast(`深挖失败：${e.message}`, "error");
    } finally {
      deepBtn.disabled = false;
      deepBtn.textContent = "深挖这条";
    }
  });

  const ideasBtn = el("button", { class: "btn secondary" }, "转成写作灵感");
  ideasBtn.addEventListener("click", async () => {
    ideasBtn.disabled = true;
    ideasBtn.textContent = "生成中...";
    try {
      const data = await api.storyIdeasMaterial(id);
      renderJsonBlock(ideasNode, data, "还没有写作灵感。");
    } catch (e) {
      showToast(`生成失败：${e.message}`, "error");
    } finally {
      ideasBtn.disabled = false;
      ideasBtn.textContent = "转成写作灵感";
    }
  });

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "row" }, [
      el("button", { class: "btn secondary btn-sm", onclick: () => openMaterialList() }, "返回素材库"),
      el("div", { class: "spacer" }),
      el("a", { class: "btn secondary btn-sm", href: item.url, target: "_blank" }, "查看原文"),
    ]),
    el("h2", {}, item.title),
    el("div", { class: "muted" }, `${item.channelLabel} · ${item.sourceName || "未知来源"}`),
    el("div", { class: "scenario-box", html: escapeHtml(item.aiSummary || item.displaySummary || item.summary || "暂无摘要") }),
    item.aiReason ? el("p", {}, `入选理由：${item.aiReason}`) : null,
    item.fictionFit || item.fictionAngle
      ? el("div", { class: "scenario-box" }, `小说素材适配度：${item.fictionFit || "未判断"}${item.fictionAngle ? ` · ${item.fictionAngle}` : ""}`)
      : null,
    el("div", { class: "row" }, [deepBtn, ideasBtn]),
    el("h3", {}, "AI 深读"),
    deepNode,
    el("h3", {}, "写作灵感"),
    ideasNode,
  ]));
}

function renderJsonBlock(root, data, emptyText) {
  root.innerHTML = "";
  if (!data) {
    root.appendChild(el("div", { class: "empty" }, emptyText));
    return;
  }
  for (const [key, value] of Object.entries(data)) {
    const content = Array.isArray(value) ? value.map((item) => `• ${item}`).join("\n") : String(value);
    root.appendChild(el("div", { class: "ai-block" }, [
      el("strong", {}, key),
      el("pre", {}, content),
    ]));
  }
}

function openMaterial(id) {
  location.hash = `#/materials/${id}`;
  location.reload();
}

function openMaterialList() {
  location.hash = "";
  location.reload();
}
