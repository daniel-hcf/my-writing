import { api } from "../api.js";
import { el, showToast } from "../utils.js";

const TEXT_PRESETS = [
  { label: "── Anthropic ──", disabled: true },
  { label: "Claude Sonnet 4.6（推荐）", provider: "anthropic", baseUrl: "https://api.anthropic.com", model: "claude-sonnet-4-6" },
  { label: "Claude Opus 4.7（顶配）", provider: "anthropic", baseUrl: "https://api.anthropic.com", model: "claude-opus-4-7" },
  { label: "Claude Haiku 4.5（经济）", provider: "anthropic", baseUrl: "https://api.anthropic.com", model: "claude-haiku-4-5-20251001" },
  { label: "── OpenRouter（一个Key走所有） ──", disabled: true },
  { label: "Claude Sonnet 4.6 via OpenRouter", provider: "openai", baseUrl: "https://openrouter.ai/api/v1", model: "anthropic/claude-sonnet-4-6" },
  { label: "Claude Opus 4.7 via OpenRouter", provider: "openai", baseUrl: "https://openrouter.ai/api/v1", model: "anthropic/claude-opus-4-7" },
  { label: "GPT-5 via OpenRouter", provider: "openai", baseUrl: "https://openrouter.ai/api/v1", model: "openai/gpt-5" },
  { label: "GPT-5 Mini via OpenRouter", provider: "openai", baseUrl: "https://openrouter.ai/api/v1", model: "openai/gpt-5-mini" },
  { label: "── OpenAI 直连 ──", disabled: true },
  { label: "GPT-5", provider: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-5" },
  { label: "GPT-5 Mini", provider: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-5-mini" },
  { label: "GPT-4o", provider: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-4o" },
  { label: "GPT-4o Mini（经济）", provider: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  { label: "── DeepSeek ──", disabled: true },
  { label: "DeepSeek Chat V3", provider: "openai", baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { label: "DeepSeek Reasoner（思考链）", provider: "openai", baseUrl: "https://api.deepseek.com/v1", model: "deepseek-reasoner" },
  { label: "── 通义千问 ──", disabled: true },
  { label: "Qwen Plus", provider: "openai", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus" },
  { label: "Qwen Max", provider: "openai", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-max" },
  { label: "Qwen Turbo（经济）", provider: "openai", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-turbo" },
  { label: "── Kimi ──", disabled: true },
  { label: "Kimi Latest（长上下文）", provider: "openai", baseUrl: "https://api.moonshot.cn/v1", model: "moonshot-v1-32k" },
  { label: "── 智谱 GLM ──", disabled: true },
  { label: "GLM-4-Flash（免费）", provider: "openai", baseUrl: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-flash" },
  { label: "GLM-4-Plus", provider: "openai", baseUrl: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-plus" },
  { label: "── Ollama 本地 ──", disabled: true },
  { label: "Qwen2.5 7B（本地）", provider: "ollama", baseUrl: "http://localhost:11434", model: "qwen2.5:7b" },
  { label: "Qwen2.5 14B（本地）", provider: "ollama", baseUrl: "http://localhost:11434", model: "qwen2.5:14b" },
  { label: "DeepSeek R1 8B（本地）", provider: "ollama", baseUrl: "http://localhost:11434", model: "deepseek-r1:8b" },
];

const IMAGE_PRESETS = [
  { label: "── SiliconFlow ──", disabled: true },
  { label: "FLUX.1-schnell（免费）", provider: "openai", baseUrl: "https://api.siliconflow.cn/v1", model: "black-forest-labs/FLUX.1-schnell" },
  { label: "FLUX.1-dev（更高质量）", provider: "openai", baseUrl: "https://api.siliconflow.cn/v1", model: "black-forest-labs/FLUX.1-dev" },
  { label: "Stable Diffusion 3.5 Large", provider: "openai", baseUrl: "https://api.siliconflow.cn/v1", model: "stabilityai/stable-diffusion-3-5-large" },
  { label: "── OpenAI 直连 ──", disabled: true },
  { label: "gpt-image-1", provider: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-image-1" },
  { label: "gpt-image-2", provider: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-image-2" },
];

export async function renderSettings(root, ctx) {
  root.innerHTML = "";
  const cfg = await api.getConfig();

  root.appendChild(buildSection({
    title: "文本模型（出题与评分）",
    target: "text",
    cfg: cfg.text,
    presets: TEXT_PRESETS,
    defaults: cfg.defaults.text,
    refresh: ctx.refreshConfig,
  }));

  root.appendChild(buildSection({
    title: "图片模型（看图写作）",
    target: "image",
    cfg: cfg.image,
    presets: IMAGE_PRESETS,
    defaults: cfg.defaults.image,
    refresh: ctx.refreshConfig,
  }));

  root.appendChild(await buildEditorialSection());

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "muted" }, [
      "Ollama 无需 API Key。",
      el("br"),
      "SiliconFlow FLUX.1-schnell 免费，注册即可用。",
      el("br"),
      "OpenRouter 一个账号接入所有家，Base URL 填 https://openrouter.ai/api/v1。",
    ]),
  ]));
}

async function buildEditorialSection() {
  const [packs, sources, smtp, schedule] = await Promise.all([
    api.listEditorialPacks(),
    api.listRSSSources(),
    api.getSMTPConfig(),
    api.getEditorialSchedule(),
  ]);

  const reloadEditorialSettings = () => renderSettings(document.getElementById("view"), { refreshConfig: async () => {} });
  const sourceList = el("div", { class: "source-list" });
  renderSourceList(sourceList, sources, reloadEditorialSettings);

  const packButtons = packs.map((pack) => {
    const btn = el("button", { class: "btn secondary btn-sm" }, `导入${pack.name}`);
    btn.title = pack.sources.map((source) => `${source.name} · ${source.url}`).join("\n");
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "导入中...";
      try {
        const result = await api.importEditorialPack(pack.id);
        showToast(`已导入 ${result.imported} 个源，跳过 ${result.skipped} 个重复源`);
        reloadEditorialSettings();
      } catch (e) {
        showToast(`导入失败：${e.message}`, "error");
      }
    });
    return btn;
  });

  const smtpHost = el("input", { type: "text", value: smtp.host || "", placeholder: "smtp.example.com" });
  const smtpPort = el("input", { type: "number", value: smtp.port || 465 });
  const smtpUser = el("input", { type: "text", value: smtp.username || "", placeholder: "邮箱账号" });
  const smtpPassword = el("input", { type: "password", value: smtp.password || "", placeholder: "授权码/应用专用密码" });
  const smtpFrom = el("input", { type: "text", value: smtp.fromEmail || "", placeholder: "发件人邮箱" });
  const smtpTo = el("input", { type: "text", value: smtp.toEmail || "", placeholder: "收件人邮箱" });
  const useTls = el("input", { type: "checkbox" });
  useTls.checked = smtp.useTls !== false;
  const sendTime = el("input", { type: "time", value: schedule.sendTime || "08:00" });
  const autoSend = el("input", { type: "checkbox" });
  autoSend.checked = schedule.autoSend !== false;
  const newSourceName = el("input", { type: "text", placeholder: "源名称" });
  const newSourceUrl = el("input", { type: "text", placeholder: "RSS URL" });
  const newSourceChannel = el("select", {}, [
    el("option", { value: "social" }, "当前社会热点"),
    el("option", { value: "story" }, "故事素材雷达"),
  ]);
  const addSourceBtn = el("button", { class: "btn secondary btn-sm" }, "新增RSS源");
  addSourceBtn.addEventListener("click", async () => {
    try {
      await api.createRSSSource({
        name: newSourceName.value.trim(),
        url: newSourceUrl.value.trim(),
        channel: newSourceChannel.value,
        enabled: true,
      });
      showToast("RSS 源已新增");
      reloadEditorialSettings();
    } catch (e) {
      showToast(`新增失败：${e.message}`, "error");
    }
  });

  const saveBtn = el("button", { class: "btn" }, "保存编辑部设置");
  saveBtn.addEventListener("click", async () => {
    try {
      await api.putSMTPConfig({
        host: smtpHost.value.trim(),
        port: Number(smtpPort.value || 465),
        username: smtpUser.value.trim(),
        password: smtpPassword.value,
        fromEmail: smtpFrom.value.trim(),
        toEmail: smtpTo.value.trim(),
        useTls: useTls.checked,
      });
      await api.putEditorialSchedule({ sendTime: sendTime.value || "08:00", autoSend: autoSend.checked });
      showToast("编辑部设置已保存");
    } catch (e) {
      showToast(`保存失败：${e.message}`, "error");
    }
  });

  const testBtn = el("button", { class: "btn secondary" }, "测试SMTP");
  testBtn.addEventListener("click", async () => {
    try {
      await api.putSMTPConfig({
        host: smtpHost.value.trim(),
        port: Number(smtpPort.value || 465),
        username: smtpUser.value.trim(),
        password: smtpPassword.value,
        fromEmail: smtpFrom.value.trim(),
        toEmail: smtpTo.value.trim(),
        useTls: useTls.checked,
      });
      await api.testSMTPConfig();
      showToast("SMTP 连接成功");
    } catch (e) {
      showToast(`SMTP 测试失败：${e.message}`, "error");
    }
  });

  return el("div", { class: "card" }, [
    el("h2", {}, "AI 编辑部"),
    el("div", { class: "muted" }, "一键导入推荐 RSS 源，配置个人邮箱 SMTP，每天自动发送双频道素材简报。"),
    el("div", { class: "field" }, [el("label", {}, "推荐源包（鼠标悬停可预览源列表）"), el("div", { class: "row" }, packButtons)]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "手动新增源"), newSourceName]),
      el("div", { class: "field" }, [el("label", {}, "RSS URL"), newSourceUrl]),
    ]),
    el("div", { class: "row" }, [newSourceChannel, addSourceBtn]),
    sourceList,
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "发送时间"), sendTime]),
      el("label", { class: "check-row" }, [autoSend, " 自动发送，错过后下次启动补发"]),
    ]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "SMTP 主机"), smtpHost]),
      el("div", { class: "field" }, [el("label", {}, "端口"), smtpPort]),
    ]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "账号"), smtpUser]),
      el("div", { class: "field" }, [el("label", {}, "授权码/密码"), smtpPassword]),
    ]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "发件人"), smtpFrom]),
      el("div", { class: "field" }, [el("label", {}, "收件人"), smtpTo]),
    ]),
    el("label", { class: "check-row" }, [useTls, " 使用 SSL/TLS（多数个人邮箱建议开启）"]),
    el("div", { class: "row" }, [saveBtn, testBtn]),
  ]);
}

function renderSourceList(root, sources, reload) {
  root.innerHTML = "";
  if (!sources.length) {
    root.appendChild(el("div", { class: "empty" }, "还没有 RSS 源。可以先导入推荐源包。"));
    return;
  }
  const rows = sources.slice(0, 20).map((source) => {
    const toggleBtn = el("button", { class: "btn secondary btn-sm" }, source.enabled ? "停用" : "启用");
    toggleBtn.addEventListener("click", async () => {
      try {
        await api.updateRSSSource(source.id, { enabled: !source.enabled });
        reload();
      } catch (e) {
        showToast(`更新失败：${e.message}`, "error");
      }
    });
    const deleteBtn = el("button", { class: "btn secondary btn-sm" }, "删除");
    deleteBtn.addEventListener("click", async () => {
      if (!confirm(`删除 RSS 源「${source.name}」？已入库素材不会被删除。`)) return;
      try {
        await api.deleteRSSSource(source.id);
        reload();
      } catch (e) {
        showToast(`删除失败：${e.message}`, "error");
      }
    });
    const editBtn = el("button", { class: "btn secondary btn-sm" }, "编辑");
    editBtn.addEventListener("click", async () => {
      const name = prompt("RSS 源名称", source.name);
      if (name == null) return;
      const url = prompt("RSS URL", source.url);
      if (url == null) return;
      try {
        await api.updateRSSSource(source.id, { name: name.trim(), url: url.trim(), channel: source.channel, enabled: source.enabled });
        reload();
      } catch (e) {
        showToast(`编辑失败：${e.message}`, "error");
      }
    });
    return el("div", { class: "source-row" }, [
      el("div", {}, [
        el("strong", {}, source.name),
        el("div", { class: "muted" }, `${source.channelLabel} · ${source.url}`),
      ]),
      el("div", { class: "row" }, [
        el("span", { class: source.enabled ? "focus-tag" : "focus-tag muted" }, source.enabled ? "启用" : "停用"),
        editBtn,
        toggleBtn,
        deleteBtn,
      ]),
    ]);
  });
  root.appendChild(el("div", { class: "field" }, [
    el("label", {}, `RSS 源（显示前 ${Math.min(20, sources.length)} 个，共 ${sources.length} 个）`),
    ...rows,
  ]));
}

function buildSection({ title, target, cfg, presets, defaults, refresh }) {
  const provSel = el("select");
  for (const p of ["anthropic", "openai", "ollama"]) {
    const opt = el("option", { value: p }, p);
    if (cfg.provider === p) opt.selected = true;
    provSel.appendChild(opt);
  }

  const apiKeyInput = el("input", {
    type: "password",
    value: cfg.apiKey || "",
    placeholder: "API Key（Ollama 无需填写）",
  });
  const baseUrlInput = el("input", {
    type: "text",
    value: cfg.baseUrl || defaults.baseUrl,
    placeholder: defaults.baseUrl,
  });
  const modelInput = el("input", {
    type: "text",
    value: cfg.model || defaults.model,
    placeholder: defaults.model,
  });

  // 快捷选择下拉
  const presetSel = el("select");
  presetSel.appendChild(el("option", { value: "" }, "── 快捷选择服务商 ──"));
  presets.forEach((p, i) => {
    const opt = el("option", { value: String(i) }, p.label);
    if (p.disabled) opt.disabled = true;
    presetSel.appendChild(opt);
  });
  presetSel.addEventListener("change", () => {
    const idx = parseInt(presetSel.value);
    if (isNaN(idx)) return;
    const p = presets[idx];
    if (!p || p.disabled) return;
    provSel.value = p.provider;
    baseUrlInput.value = p.baseUrl;
    modelInput.value = p.model;
    presetSel.value = "";
  });

  const saveBtn = el("button", { class: "btn" }, "保存");
  const testBtn = el("button", { class: "btn secondary" }, "测试连接");

  async function currentPayload() {
    const current = await api.getConfig();
    const next = { text: { ...current.text }, image: { ...current.image } };
    next[target] = {
      provider: provSel.value,
      apiKey: apiKeyInput.value,
      baseUrl: baseUrlInput.value.trim(),
      model: modelInput.value.trim(),
    };
    return next;
  }

  saveBtn.addEventListener("click", async () => {
    try {
      await api.putConfig(await currentPayload());
      await refresh();
      showToast("已保存");
    } catch (e) {
      showToast("保存失败：" + e.message, "error");
    }
  });

  testBtn.addEventListener("click", async () => {
    testBtn.disabled = true;
    testBtn.textContent = "测试中...";
    try {
      await api.putConfig(await currentPayload());
      await api.testProvider(target);
      showToast("连接成功 ✓");
      await refresh();
    } catch (e) {
      showToast("失败：" + e.message, "error");
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = "测试连接";
    }
  });

  return el("div", { class: "card" }, [
    el("h2", {}, title),
    el("div", { class: "field" }, [el("label", {}, "快捷选择"), presetSel]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "Provider"), provSel]),
      el("div", { class: "field" }, [el("label", {}, "API Key"), apiKeyInput]),
    ]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "Base URL"), baseUrlInput]),
      el("div", { class: "field" }, [el("label", {}, "Model"), modelInput]),
    ]),
    el("div", { class: "row" }, [saveBtn, testBtn]),
  ]);
}
