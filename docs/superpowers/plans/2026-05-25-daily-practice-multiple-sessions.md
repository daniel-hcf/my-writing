# Daily Practice Multiple Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the user to write multiple "每日主练" submissions on the same day, either by repeating the same prompt or generating a new one.

**Architecture:** Keep the current SQLite schema. Change daily lookup to prefer today's unsubmitted daily assignment, add a repeat service/API that copies an existing daily assignment into a new draft for today, and add result-page buttons that open the next writing session.

**Tech Stack:** FastAPI, SQLite, Python `unittest`, vanilla browser JavaScript.

---

### Task 1: Backend Daily Assignment Behavior

**Files:**
- Modify: `my_writing/services.py`
- Test: `tests/test_practice_modes.py`

- [ ] **Step 1: Write failing service tests**

Add these tests after `test_get_or_create_today_assignment_returns_daily_and_reuses_it` in `tests/test_practice_modes.py`:

```python
    async def test_daily_assignment_prefers_unsubmitted_after_submission(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "submitted daily", "old seed", None, "叙事结构", f"{today}T00:00:00"),
            )
            submitted_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (submitted_id, today, "x" * 300, 300, "{}", "{}", f"{today}T00:01:00"),
            )
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "open daily", "new seed", None, "人物塑造", f"{today}T00:02:00"),
            )
            open_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        result = await services.get_or_create_today_assignment(self.cfg)

        self.assertEqual(result["id"], open_id)
        self.assertNotIn("submission", result)
        self.assertEqual(result["draftContent"], "")

    async def test_replace_today_daily_assignment_allows_new_after_submission(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "submitted daily", "old seed", None, None, f"{today}T00:00:00"),
            )
            submitted_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (submitted_id, today, "x" * 300, 300, "{}", "{}", f"{today}T00:01:00"),
            )

        with patch.object(
            services,
            "generate_daily_assignment",
            AsyncMock(
                return_value={
                    "type": "daily",
                    "title": "new daily",
                    "scenario": "new seed",
                    "image_data": None,
                    "focus_dimension": None,
                }
            ),
        ) as gen:
            result = await services.replace_today_daily_assignment(self.cfg)

        self.assertNotEqual(result["id"], submitted_id)
        self.assertEqual(result["title"], "new daily")
        self.assertEqual(gen.await_count, 1)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:GOTOOLCHAIN='local'; python -m unittest tests.test_practice_modes.PracticeModesTest.test_daily_assignment_prefers_unsubmitted_after_submission tests.test_practice_modes.PracticeModesTest.test_replace_today_daily_assignment_allows_new_after_submission
```

Expected: at least one failure because daily lookup returns the latest daily assignment without preferring unsubmitted records and `replace_today_daily_assignment` rejects days with submissions.

- [ ] **Step 3: Implement backend behavior**

In `my_writing/services.py`, replace `get_or_create_today_assignment` and `replace_today_daily_assignment` with:

```python
async def get_or_create_today_assignment(cfg: FullConfig) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    row = get_current_unsubmitted_assignment(today, MODE_DAILY)
    if not row:
        row = get_assignment_by_date(today, mode_filter=MODE_DAILY)
    if not row:
        focus = latest_weakest_dimension()
        recent = recent_assignment_titles(MODE_DAILY)
        data = await generate_daily_assignment(focus, cfg, recent)
        aid = insert_assignment(data, today)
        row = get_assignment_by_id(aid)
    result = assignment_row_to_dict(row)
    sub = get_submission_by_assignment(row["id"])
    if sub:
        result["submission"] = submission_row_to_dict(sub)
    else:
        attach_assignment_draft(result, row["id"])
    return result


async def replace_today_daily_assignment(cfg: FullConfig) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    delete_unsubmitted_assignments(today, MODE_DAILY)
    focus = latest_weakest_dimension()
    recent = recent_assignment_titles(MODE_DAILY)
    data = await generate_daily_assignment(focus, cfg, recent)
    aid = insert_assignment(data, today)
    return attach_assignment_draft(assignment_row_to_dict(get_assignment_by_id(aid)), aid)
```

- [ ] **Step 4: Run focused tests**

Run the same command from Step 2.

Expected: both tests pass.

---

### Task 2: Repeat Same Daily Prompt API

**Files:**
- Modify: `my_writing/services.py`
- Modify: `my_writing/routers/assignments.py`
- Test: `tests/test_practice_modes.py`
- Test: `tests/test_frontend_contracts.py`

- [ ] **Step 1: Write failing repeat service test**

Add this test after the tests from Task 1:

```python
    def test_repeat_daily_assignment_copies_prompt_for_today(self):
        source_date = "2026-04-29"
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source_date, "daily", "source daily", "source seed", None, "环境描写", f"{source_date}T00:00:00"),
            )
            source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        result = services.repeat_daily_assignment(source_id)

        self.assertNotEqual(result["id"], source_id)
        self.assertEqual(result["date"], today)
        self.assertEqual(result["type"], "daily")
        self.assertEqual(result["title"], "source daily")
        self.assertEqual(result["scenario"], "source seed")
        self.assertEqual(result["focusDimension"], "环境描写")
        self.assertEqual(result["draftContent"], "")
```

- [ ] **Step 2: Write failing frontend API contract test**

Add this test to `tests/test_frontend_contracts.py`:

```python
    def test_daily_repeat_endpoint_is_exposed_in_frontend_api(self):
        source = (ROOT / "web" / "js" / "api.js").read_text(encoding="utf-8")

        self.assertIn("repeatDailyAssignment", source)
        self.assertIn("/repeat", source)
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
$env:GOTOOLCHAIN='local'; python -m unittest tests.test_practice_modes.PracticeModesTest.test_repeat_daily_assignment_copies_prompt_for_today tests.test_frontend_contracts.FrontendContractsTest.test_daily_repeat_endpoint_is_exposed_in_frontend_api
```

Expected: fails because `repeat_daily_assignment` and `repeatDailyAssignment` do not exist.

- [ ] **Step 4: Implement repeat service**

In `my_writing/services.py`, add this function near `replace_today_daily_assignment`:

```python
def repeat_daily_assignment(assignment_id: int) -> dict:
    row = get_assignment_by_id(assignment_id)
    if row is None:
        raise ValueError("assignment_not_found")
    if row["type"] != MODE_DAILY:
        raise ValueError("repeat_only_supports_daily")

    today = datetime.now().strftime("%Y-%m-%d")
    aid = insert_assignment(
        {
            "type": MODE_DAILY,
            "title": row["title"],
            "scenario": row["scenario"],
            "image_data": None,
            "focus_dimension": row["focus_dimension"],
        },
        today,
    )
    return attach_assignment_draft(assignment_row_to_dict(get_assignment_by_id(aid)), aid)
```

- [ ] **Step 5: Implement repeat route and frontend API client**

In `my_writing/routers/assignments.py`, import `repeat_daily_assignment` and add this route before `@router.get("/{aid}")`:

```python
@router.post("/{aid}/repeat")
def repeat_assignment(aid: int):
    try:
        return repeat_daily_assignment(aid)
    except ValueError as exc:
        if str(exc) == "assignment_not_found":
            raise HTTPException(status_code=404, detail="assignment not found")
        if str(exc) == "repeat_only_supports_daily":
            raise HTTPException(status_code=400, detail="repeat is only supported for daily assignments")
        raise HTTPException(status_code=400, detail=str(exc))
```

In `web/js/api.js`, add:

```javascript
  repeatDailyAssignment: (assignmentId) => request("POST", `/api/assignments/${assignmentId}/repeat`),
```

- [ ] **Step 6: Run focused tests**

Run the command from Step 3.

Expected: both tests pass.

---

### Task 3: Daily Result View Actions

**Files:**
- Modify: `web/js/views/daily.js`
- Test: `tests/test_frontend_contracts.py`

- [ ] **Step 1: Write failing frontend contract test**

Add this test to `tests/test_frontend_contracts.py`:

```python
    def test_daily_result_view_offers_repeat_and_new_prompt_actions(self):
        source = (ROOT / "web" / "js" / "views" / "daily.js").read_text(encoding="utf-8")

        self.assertIn("再写同一题", source)
        self.assertIn("换一题再写", source)
        self.assertIn("api.repeatDailyAssignment", source)
        self.assertIn("api.newAssignment", source)
        self.assertIn("renderAssignment(root, ctx, next)", source)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
$env:GOTOOLCHAIN='local'; python -m unittest tests.test_frontend_contracts.FrontendContractsTest.test_daily_result_view_offers_repeat_and_new_prompt_actions
```

Expected: fails because the result view does not have the new actions.

- [ ] **Step 3: Implement result actions**

In `web/js/views/daily.js`, update `renderResult` to create two async buttons before calling `renderScoredResult`:

```javascript
function renderResult(root, ctx, assignment, result) {
  const repeatBtn = el("button", { class: "btn" }, "再写同一题");
  repeatBtn.addEventListener("click", async () => {
    repeatBtn.disabled = true;
    repeatBtn.textContent = "正在准备...";
    try {
      const next = await api.repeatDailyAssignment(assignment.id);
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`创建练习失败：${e.message}`, "error");
      repeatBtn.disabled = false;
      repeatBtn.textContent = "再写同一题";
    }
  });

  const newPromptBtn = el("button", { class: "btn secondary" }, "换一题再写");
  newPromptBtn.addEventListener("click", async () => {
    newPromptBtn.disabled = true;
    newPromptBtn.textContent = "正在生成...";
    try {
      const next = await api.newAssignment();
      renderAssignment(root, ctx, next);
    } catch (e) {
      showToast(`生成题目失败：${e.message}`, "error");
      newPromptBtn.disabled = false;
      newPromptBtn.textContent = "换一题再写";
    }
  });

  renderScoredResult(root, assignment, result, [
    repeatBtn,
    newPromptBtn,
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("outline_practice") }, "去写故事小纲"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("image_practice") }, "去看图写作"),
    el("div", { class: "spacer" }),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("history") }, "查看历史"),
    el("button", { class: "btn secondary", onclick: () => ctx.navigate("stats") }, "查看统计"),
  ]);
}
```

- [ ] **Step 4: Run focused test**

Run the command from Step 2.

Expected: test passes.

---

### Task 4: Full Verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run practice mode tests**

Run:

```powershell
$env:GOTOOLCHAIN='local'; python -m unittest tests.test_practice_modes
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend contract tests**

Run:

```powershell
$env:GOTOOLCHAIN='local'; python -m unittest tests.test_frontend_contracts
```

Expected: all tests pass.

- [ ] **Step 3: Inspect final diff**

Run:

```powershell
git diff -- my_writing/services.py my_writing/routers/assignments.py web/js/api.js web/js/views/daily.js tests/test_practice_modes.py tests/test_frontend_contracts.py
```

Expected: diff only contains daily practice repeat support and matching tests.
