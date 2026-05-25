# Daily Practice Multiple Sessions Design

## Context

The current daily practice flow treats "每日主练" as one exercise per day. Before submission, the user can keep editing a draft or replace the unsubmitted prompt. After submission, the daily page shows the scored result and does not offer a direct way to keep writing.

The desired behavior is to keep the daily practice identity while allowing extra momentum on good writing days.

## Goals

- Let the user write multiple daily practice submissions on the same date.
- Offer two clear continuation paths after a scored daily practice:
  - "再写同一题": start a new draft using the same title, story seed, and focus dimension.
  - "换一题再写": generate a new daily practice prompt and start a new draft.
- Preserve submitted records. Replacing a prompt must only affect unsubmitted assignments.
- Keep history and stats compatible with multiple daily submissions on the same date.

## Non-Goals

- No changes to journal, outline practice, or image practice behavior.
- No changes to the scoring rubric or minimum character count.
- No editing or resubmitting an existing submitted record.

## User Flow

1. The user opens "每日主练".
2. If there is an unsubmitted daily assignment for today, the app opens that draft.
3. If there is no unsubmitted daily assignment but there is a submitted daily assignment today, the app shows the most recent result.
4. From the result view:
   - "再写同一题" creates a new unsubmitted daily assignment copied from the displayed assignment.
   - "换一题再写" creates a new generated daily assignment.
5. The new assignment opens in the editor and can be submitted as another daily practice record.

## Backend Design

- Change daily assignment lookup to prefer today's latest unsubmitted `daily` assignment.
- If none exists, return today's latest submitted `daily` assignment with its submission so the result view remains available.
- Add a service function that duplicates an existing daily assignment into a new unsubmitted assignment for today.
- Add an API endpoint for "再写同一题", likely `POST /api/assignments/{id}/repeat`.
- Adjust `replace_today_daily_assignment` so it deletes only today's unsubmitted daily assignments and then generates a new prompt. It should no longer reject the request only because a daily submission already exists today.

## Frontend Design

- Add API client support for the repeat endpoint.
- In the daily result view, add two primary continuation actions:
  - "再写同一题": calls the repeat endpoint for the displayed assignment id, then renders the returned assignment editor.
  - "换一题再写": calls the existing new daily assignment endpoint, then renders the returned assignment editor.
- Keep "查看历史" and "查看统计" available as secondary actions.
- Keep the existing editor "换一题" button behavior for unsubmitted assignments.

## Data Compatibility

The database already supports multiple assignments with the same date and type because `assignments.date` is indexed but not unique. Submissions are tied to assignment ids, so multiple daily submissions on one date do not require a schema migration.

History already groups by assignment type and lists submissions individually. Stats collect submissions and should naturally include every scored daily record.

## Error Handling

- Repeating a non-existent assignment returns 404.
- Repeating a non-daily assignment returns 400.
- Repeating a daily assignment from another date is allowed only if the endpoint intentionally supports it; for this feature, restrict it to daily assignments and create the copy for today.
- Generation failures for "换一题再写" should reuse the current daily new-assignment error handling.

## Tests

- Service test: daily lookup reuses an unsubmitted daily assignment even when earlier submitted daily assignments exist today.
- Service test: after a submitted daily assignment, generating a new daily assignment creates a different assignment instead of failing.
- Service test: repeating a daily assignment creates a new unsubmitted assignment with copied title, scenario, and focus dimension.
- Router or contract test: frontend API exposes the repeat daily endpoint.
- Frontend contract test: daily result view includes actions for repeating the same prompt and writing a new prompt.
