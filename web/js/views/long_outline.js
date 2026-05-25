import { api } from "../api.js";
import { charCount, el, escapeHtml, showToast } from "../utils.js";

const STORAGE_KEY = "long_outline_current_project";
const VIEW_KEY = "long_outline_view";
const CHAPTER_KEY = "long_outline_chapter";

const GUIDE_STEPS = [
  { id: "core", label: "作品核心" },
  { id: "characters", label: "轻量人物" },
  { id: "volume", label: "第一卷目标" },
  { id: "beats", label: "三段推进" },
  { id: "chapters", label: "前10章章节纲" },
  { id: "check", label: "自检" },
];

export async function renderLongOutline(root, ctx) {
  const currentId = localStorage.getItem(STORAGE_KEY);
  if (currentId) {
    try {
      const project = await api.getOutlineProject(currentId);
      renderProject(root, ctx, project, localStorage.getItem(VIEW_KEY) || "guide");
      return;
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  await renderProjectList(root, ctx);
}

async function renderProjectList(root, ctx) {
  root.innerHTML = "";
  const projects = await api.listOutlineProjects();
  const titleInput = el("input", { type: "text", placeholder: "作品名" });
  const genreInput = el("input", { type: "text", placeholder: "题材 / 标签" });
  const premiseInput = el("input", { type: "text", placeholder: "一句话卖点" });
  const createBtn = el("button", { class: "btn" }, "新建作品");
  createBtn.addEventListener("click", async () => {
    const title = titleInput.value.trim();
    if (!title) {
      showToast("请先填写作品名", "error");
      return;
    }
    createBtn.disabled = true;
    try {
      const project = await api.createOutlineProject({
        title,
        genre: genreInput.value,
        premise: premiseInput.value,
      });
      localStorage.setItem(STORAGE_KEY, project.id);
      renderProject(root, ctx, project, "guide");
    } catch (e) {
      showToast(`创建失败：${e.message}`, "error");
      createBtn.disabled = false;
    }
  });

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "row" }, [
      el("h2", {}, "长篇大纲"),
      el("div", { class: "spacer" }),
      el("span", { class: "muted" }, "作品列表"),
    ]),
    el("div", { class: "field-row" }, [
      el("div", { class: "field" }, [el("label", {}, "作品名"), titleInput]),
      el("div", { class: "field" }, [el("label", {}, "题材 / 标签"), genreInput]),
    ]),
    el("div", { class: "field" }, [el("label", {}, "一句话卖点"), premiseInput]),
    el("div", { class: "row" }, [el("div", { class: "spacer" }), createBtn]),
  ]));

  if (!projects.length) {
    root.appendChild(el("div", { class: "card" }, [
      el("div", { class: "empty" }, "还没有长篇项目，先新建一个作品。"),
    ]));
    return;
  }

  const grid = el("div", { class: "outline-project-grid" });
  for (const project of projects) {
    grid.appendChild(renderProjectCard(root, ctx, project));
  }
  root.appendChild(grid);
}

function renderProjectCard(root, ctx, project) {
  const openBtn = el("button", { class: "btn btn-sm" }, "继续写");
  openBtn.addEventListener("click", async () => {
    const full = await api.getOutlineProject(project.id);
    localStorage.setItem(STORAGE_KEY, project.id);
    renderProject(root, ctx, full, localStorage.getItem(VIEW_KEY) || "guide");
  });

  const renameBtn = el("button", { class: "btn secondary btn-sm" }, "重命名");
  renameBtn.addEventListener("click", async () => {
    const title = window.prompt("新的作品名", project.title);
    if (!title || !title.trim()) return;
    await api.updateOutlineProject(project.id, { title: title.trim() });
    await renderProjectList(root, ctx);
  });

  const deleteBtn = el("button", { class: "btn danger btn-sm" }, "删除");
  deleteBtn.addEventListener("click", async () => {
    if (!window.confirm(`确定删除《${project.title}》吗？`)) return;
    await api.deleteOutlineProject(project.id);
    if (String(project.id) === localStorage.getItem(STORAGE_KEY)) {
      localStorage.removeItem(STORAGE_KEY);
    }
    await renderProjectList(root, ctx);
  });

  const progress = project.progress || {};
  return el("div", { class: "card outline-project-card" }, [
    el("h2", {}, project.title),
    el("div", { class: "muted" }, project.genre || "未填写题材"),
    el("p", {}, project.premise || "还没有一句话卖点"),
    el("div", { class: "outline-progress" }, [
      el("div", { class: "outline-progress-bar", style: `width:${progress.percent || 0}%` }),
    ]),
    el("div", { class: "muted" }, `进度 ${progress.percent || 0}% / 前10章 ${progress.completedChapters || 0}章完成`),
    el("div", { class: "muted" }, `最近编辑：${project.updatedAt || "-"}`),
    el("div", { class: "row", style: "margin-top:12px;" }, [openBtn, renameBtn, el("div", { class: "spacer" }), deleteBtn]),
  ]);
}

function renderProject(root, ctx, project, view) {
  localStorage.setItem(STORAGE_KEY, project.id);
  localStorage.setItem(VIEW_KEY, view);
  root.innerHTML = "";
  root.appendChild(renderProjectHeader(root, ctx, project, view));
  if (view === "overview") renderOverview(root, ctx, project);
  else if (view === "write") renderChapterWriting(root, ctx, project);
  else renderGuide(root, ctx, project);
}

function renderProjectHeader(root, ctx, project, view) {
  const backBtn = el("button", { class: "btn secondary btn-sm" }, "返回作品列表");
  backBtn.addEventListener("click", async () => {
    localStorage.removeItem(STORAGE_KEY);
    await renderProjectList(root, ctx);
  });
  const tabs = [
    ["guide", "引导填写"],
    ["overview", "大纲总览"],
    ["write", "章节开写"],
  ].map(([value, label]) => {
    const btn = el("button", { class: `segmented-btn${view === value ? " active" : ""}` }, label);
    btn.addEventListener("click", () => renderProject(root, ctx, project, value));
    return btn;
  });
  return el("div", { class: "card" }, [
    el("div", { class: "row" }, [
      backBtn,
      el("div", { class: "spacer" }),
      el("div", { class: "segmented" }, tabs),
    ]),
    el("h2", { style: "margin-top:14px;" }, project.title),
    el("div", { class: "muted" }, `${project.genre || "未填写题材"} · 进度 ${project.progress?.percent || 0}%`),
  ]);
}

function renderGuide(root, ctx, project) {
  const layout = el("div", { class: "outline-workbench" }, [
    renderStepNav(project),
    el("div", {}, [
      renderCoreForm(root, ctx, project),
      renderCharactersForm(root, ctx, project),
      renderVolumeForm(root, ctx, project),
      renderBeatsForm(root, ctx, project),
      renderChaptersGuide(root, ctx, project),
    ]),
    renderChecklist(ctx, project),
  ]);
  root.appendChild(layout);
}

function renderStepNav(project) {
  return el("div", { class: "card outline-step-nav" }, [
    el("h2", {}, "引导填写"),
    ...GUIDE_STEPS.map((step, index) => el("div", { class: "outline-step-item" }, [
      el("span", { class: "outline-step-no" }, String(index + 1)),
      el("span", {}, step.label),
    ])),
  ]);
}

function field(label, input) {
  return el("div", { class: "field" }, [el("label", {}, label), input]);
}

function textInput(value = "") {
  const input = el("input", { type: "text" });
  input.value = value || "";
  return input;
}

function area(value = "", rows = 3) {
  const input = el("textarea", { rows: String(rows) });
  input.value = value || "";
  return input;
}

function saveButton(label, onSave) {
  const btn = el("button", { class: "btn btn-sm" }, label);
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const project = await onSave();
      showToast("已保存");
      return project;
    } catch (e) {
      showToast(`保存失败：${e.message}`, "error");
    } finally {
      btn.disabled = false;
    }
  });
  return btn;
}

function reviewButton(root, ctx, project, scope, label) {
  if (!ctx.state.ready.text) return null;
  const btn = el("button", { class: "btn secondary btn-sm" }, label);
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      await api.reviewOutlineProject(project.id, scope);
      const refreshed = await api.getOutlineProject(project.id);
      renderProject(root, ctx, refreshed, "guide");
    } catch (e) {
      showToast(`点评失败：${e.message}`, "error");
    } finally {
      btn.disabled = false;
    }
  });
  return btn;
}

function renderCoreForm(root, ctx, project) {
  const title = textInput(project.title);
  const genre = textInput(project.genre);
  const premise = area(project.premise);
  const mainGoal = area(project.mainGoal);
  const corePayoff = area(project.corePayoff);
  const save = saveButton("保存作品核心", async () => {
    const next = await api.updateOutlineProject(project.id, {
      title: title.value,
      genre: genre.value,
      premise: premise.value,
      mainGoal: mainGoal.value,
      corePayoff: corePayoff.value,
      currentStep: "core",
    });
    renderProject(root, ctx, next, "guide");
    return next;
  });
  return el("div", { class: "card" }, [
    el("h2", {}, "作品核心"),
    el("div", { class: "field-row" }, [field("作品名", title), field("题材 / 标签", genre)]),
    field("一句话卖点", premise),
    field("主线目标", mainGoal),
    field("核心爽点", corePayoff),
    el("div", { class: "row" }, [save, reviewButton(root, ctx, project, "core", "检查作品核心"), el("div", { class: "spacer" })]),
  ]);
}

function renderCharactersForm(root, ctx, project) {
  const c = project.characters;
  const protagonistIdentity = textInput(c.protagonistIdentity);
  const protagonistGoal = textInput(c.protagonistGoal);
  const protagonistWeakness = textInput(c.protagonistWeakness);
  const protagonistGrowth = textInput(c.protagonistGrowth);
  const antagonistIdentity = textInput(c.antagonistIdentity);
  const antagonistReason = textInput(c.antagonistReason);
  const antagonistPressure = textInput(c.antagonistPressure);
  const save = saveButton("保存轻量人物", async () => {
    const next = await api.updateOutlineCharacters(project.id, {
      protagonistIdentity: protagonistIdentity.value,
      protagonistGoal: protagonistGoal.value,
      protagonistWeakness: protagonistWeakness.value,
      protagonistGrowth: protagonistGrowth.value,
      antagonistIdentity: antagonistIdentity.value,
      antagonistReason: antagonistReason.value,
      antagonistPressure: antagonistPressure.value,
    });
    renderProject(root, ctx, next, "guide");
    return next;
  });
  return el("div", { class: "card" }, [
    el("h2", {}, "轻量人物"),
    el("div", { class: "muted" }, "这里只写会影响第一卷剧情的人物信息。"),
    el("div", { class: "field-row" }, [field("主角身份", protagonistIdentity), field("他现在最想要什么", protagonistGoal)]),
    el("div", { class: "field-row" }, [field("他最大的短板", protagonistWeakness), field("爽点成长方向", protagonistGrowth)]),
    el("div", { class: "field-row" }, [field("主要阻碍者身份", antagonistIdentity), field("他为什么挡主角", antagonistReason)]),
    field("他能制造什么压力", antagonistPressure),
    el("div", { class: "row" }, [save, reviewButton(root, ctx, project, "characters", "检查人物动力"), el("div", { class: "spacer" })]),
  ]);
}

function renderVolumeForm(root, ctx, project) {
  const v = project.volume;
  const title = textInput(v.title);
  const goal = area(v.goal);
  const pressure = area(v.pressure);
  const payoff = area(v.payoff);
  const endingHook = area(v.endingHook);
  const save = saveButton("保存第一卷目标", async () => {
    const next = await api.updateOutlineVolume(project.id, {
      title: title.value,
      goal: goal.value,
      pressure: pressure.value,
      payoff: payoff.value,
      endingHook: endingHook.value,
    });
    renderProject(root, ctx, next, "guide");
    return next;
  });
  return el("div", { class: "card" }, [
    el("h2", {}, "第一卷目标"),
    field("卷名", title),
    field("本卷目标", goal),
    field("主要压力", pressure),
    field("爽点兑现", payoff),
    field("卷末钩子", endingHook),
    el("div", { class: "row" }, [save, reviewButton(root, ctx, project, "volume", "检查第一卷"), el("div", { class: "spacer" })]),
  ]);
}

function renderBeatsForm(root, ctx, project) {
  const v = project.volume;
  const openingHook = area(v.openingHook);
  const midpointEscalation = area(v.midpointEscalation);
  const finalExplosion = area(v.finalExplosion);
  const save = saveButton("保存三段推进", async () => {
    const next = await api.updateOutlineVolume(project.id, {
      openingHook: openingHook.value,
      midpointEscalation: midpointEscalation.value,
      finalExplosion: finalExplosion.value,
    });
    renderProject(root, ctx, next, "guide");
    return next;
  });
  return el("div", { class: "card" }, [
    el("h2", {}, "三段推进"),
    field("开局钩子", openingHook),
    field("中段升级", midpointEscalation),
    field("卷末爆点", finalExplosion),
    el("div", { class: "row" }, [save]),
  ]);
}

function renderChaptersGuide(root, ctx, project) {
  const wrap = el("div", { class: "card" }, [el("h2", {}, "前10章章节纲")]);
  for (const chapter of project.chapters) {
    const title = textInput(chapter.title);
    const summary = area(chapter.summary, 2);
    const payoff = area(chapter.payoff, 2);
    const hook = area(chapter.hook, 2);
    const save = saveButton("保存章节", async () => {
      const next = await api.updateOutlineChapter(project.id, chapter.chapterNo, {
        title: title.value,
        summary: summary.value,
        payoff: payoff.value,
        hook: hook.value,
      });
      renderProject(root, ctx, next, "guide");
      return next;
    });
    wrap.appendChild(el("details", { class: "outline-chapter-detail", open: chapter.chapterNo === 1 ? "open" : null }, [
      el("summary", {}, `第${chapter.chapterNo}章：${chapter.title || "未命名"}`),
      field("标题", title),
      field("剧情摘要", summary),
      field("爽点/反转", payoff),
      field("章末钩子", hook),
      el("div", { class: "row" }, [save]),
    ]));
  }
  return wrap;
}

function renderChecklist(ctx, project) {
  const latest = project.reviews?.[0];
  return el("div", { class: "card outline-side-panel" }, [
    el("h2", {}, "自检"),
    checklistItem("主角是否有明确目标？", Boolean(project.characters.protagonistGoal)),
    checklistItem("主角是否有明显短板？", Boolean(project.characters.protagonistWeakness)),
    checklistItem("阻碍者是否能主动制造麻烦？", Boolean(project.characters.antagonistPressure)),
    checklistItem("本卷冲突是否会升级？", Boolean(project.volume.midpointEscalation)),
    checklistItem("每章是否有追读理由？", project.progress.completedChapters >= 10),
    ctx.state.ready.text ? null : el("div", { class: "muted", style: "margin-top:12px;" }, "文本模型未配置，AI点评已隐藏。"),
    latest ? renderReview(latest) : null,
  ]);
}

function checklistItem(text, ok) {
  return el("div", { class: "check-row" }, [
    el("input", { type: "checkbox", disabled: "disabled", checked: ok ? "checked" : null }),
    el("span", {}, text),
  ]);
}

function renderReview(review) {
  return el("div", { class: "outline-review" }, [
    el("h3", {}, "最近点评"),
    reviewList("问题", review.issues),
    reviewList("追问", review.questions),
    reviewList("建议", review.suggestions),
  ]);
}

function reviewList(title, items) {
  return el("div", {}, [
    el("strong", {}, title),
    el("ul", {}, (items || []).map((item) => el("li", {}, item))),
  ]);
}

function renderOverview(root, ctx, project) {
  const actions = project.chapters.map((chapter) => {
    const btn = el("button", { class: "btn secondary btn-sm" }, `写第${chapter.chapterNo}章`);
    btn.addEventListener("click", () => {
      localStorage.setItem(CHAPTER_KEY, chapter.chapterNo);
      renderProject(root, ctx, project, "write");
    });
    return btn;
  });
  root.appendChild(el("div", { class: "card" }, [
    el("h2", {}, "大纲总览"),
    el("div", { class: "scenario-box" }, [
      el("strong", {}, "一句话卖点："),
      el("span", {}, project.premise || "未填写"),
      "\n",
      el("strong", {}, "主线目标："),
      el("span", {}, project.mainGoal || "未填写"),
      "\n",
      el("strong", {}, "核心爽点："),
      el("span", {}, project.corePayoff || "未填写"),
    ]),
    el("div", { class: "outline-summary-grid" }, [
      overviewBlock("主角", [
        project.characters.protagonistIdentity,
        project.characters.protagonistGoal,
        project.characters.protagonistWeakness,
        project.characters.protagonistGrowth,
      ]),
      overviewBlock("阻碍者", [
        project.characters.antagonistIdentity,
        project.characters.antagonistReason,
        project.characters.antagonistPressure,
      ]),
      overviewBlock("第一卷", [
        project.volume.title,
        project.volume.goal,
        project.volume.pressure,
        project.volume.payoff,
        project.volume.endingHook,
      ]),
    ]),
  ]));

  const chapters = el("div", { class: "card" }, [el("h2", {}, "前10章章节纲")]);
  for (const chapter of project.chapters) {
    chapters.appendChild(el("div", { class: "outline-overview-chapter" }, [
      el("div", { class: "row" }, [
        el("strong", {}, `第${chapter.chapterNo}章：${chapter.title || "未命名"}`),
        el("div", { class: "spacer" }),
        actions[chapter.chapterNo - 1],
      ]),
      el("div", { class: "muted" }, `剧情摘要：${chapter.summary || "未填写"}`),
      el("div", { class: "muted" }, `爽点/反转：${chapter.payoff || "未填写"}`),
      el("div", { class: "muted" }, `章末钩子：${chapter.hook || "未填写"}`),
    ]));
  }
  root.appendChild(chapters);
}

function overviewBlock(title, lines) {
  return el("div", { class: "outline-overview-block" }, [
    el("h3", {}, title),
    el("ul", {}, lines.filter(Boolean).map((line) => el("li", {}, line))),
  ]);
}

function renderChapterWriting(root, ctx, project) {
  const selectedNo = Number(localStorage.getItem(CHAPTER_KEY) || 1);
  const chapter = project.chapters.find((item) => item.chapterNo === selectedNo) || project.chapters[0];
  localStorage.setItem(CHAPTER_KEY, chapter.chapterNo);

  const picker = el("select");
  for (const item of project.chapters) {
    const option = el("option", { value: item.chapterNo }, `第${item.chapterNo}章：${item.title || "未命名"}`);
    if (item.chapterNo === chapter.chapterNo) option.selected = true;
    picker.appendChild(option);
  }
  picker.addEventListener("change", () => {
    localStorage.setItem(CHAPTER_KEY, picker.value);
    renderProject(root, ctx, project, "write");
  });

  const draft = area(chapter.draft, 20);
  const count = el("div", { class: "char-count" });
  const updateCount = () => {
    count.textContent = `${charCount(draft.value)} 字`;
  };
  draft.addEventListener("input", updateCount);
  updateCount();

  const save = saveButton("保存正文草稿", async () => {
    const next = await api.updateOutlineChapter(project.id, chapter.chapterNo, { draft: draft.value });
    renderProject(root, ctx, next, "write");
    return next;
  });
  const review = ctx.state.ready.text
    ? el("button", { class: "btn secondary btn-sm" }, "检查本章")
    : null;
  review?.addEventListener("click", async () => {
    review.disabled = true;
    try {
      await api.reviewOutlineChapter(project.id, chapter.chapterNo);
      const next = await api.getOutlineProject(project.id);
      renderProject(root, ctx, next, "write");
    } catch (e) {
      showToast(`点评失败：${e.message}`, "error");
    } finally {
      review.disabled = false;
    }
  });

  root.appendChild(el("div", { class: "outline-write-layout" }, [
    el("div", { class: "card" }, [
      el("h2", {}, "本章大纲"),
      field("选择章节", picker),
      el("div", { class: "scenario-box" }, [
        el("strong", {}, `第${chapter.chapterNo}章：${chapter.title || "未命名"}`),
        "\n剧情摘要：", chapter.summary || "未填写",
        "\n爽点/反转：", chapter.payoff || "未填写",
        "\n章末钩子：", chapter.hook || "未填写",
        "\n相关人物动力：", project.characters.protagonistGoal || "未填写",
      ]),
      review,
      project.reviews?.[0] ? renderReview(project.reviews[0]) : null,
    ]),
    el("div", { class: "card" }, [
      el("h2", {}, "正文草稿"),
      draft,
      count,
      el("div", { class: "row", style: "margin-top:8px;" }, [el("div", { class: "spacer" }), save]),
      chapter.draft ? el("details", { class: "outline-chapter-detail" }, [
        el("summary", {}, "预览"),
        el("div", { class: "scenario-box", html: escapeHtml(chapter.draft) }),
      ]) : null,
    ]),
  ]));
}
