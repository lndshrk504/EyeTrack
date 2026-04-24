# EyeTrack Master Implementation Log

This file is the append-only master record of implemented plan-backed changes in this repository.

Working feature plans live under `.agents/plans/`. Use those files for planning, iteration, and implementation notes. Use this file only after a planned change has been implemented.

## Workflow
- During planning, create or update exactly one working feature plan file under `.agents/plans/`.
- Keep refining the same working plan file until the plan is ready and the change is implemented.
- After implementation, update the working plan status and append a new entry to the log below.

## Entry Template

```md
## YYYY-MM-DD - Feature Title
- Plan file: `.agents/plans/YYYY-MM-DD-short-feature-title.md`
- Summary:
- Changed files:
- Validation:
- Follow-ups:
```

## Log

## 2026-04-22 - Planning Records Workflow
- Plan file: `.agents/plans/2026-04-22-planning-records-workflow.md`
- Summary: Added a repo rule and skill for maintaining one stable per-feature plan file during planning and one append-only master implementation log after implementation.
- Changed files: `AGENTS.md`, `.codex/agents/explorer.toml`, `.codex/agents/worker.toml`, `.agents/PLANS.md`, `.agents/plans/2026-04-22-planning-records-workflow.md`, `.agents/skills/feature-plan-records/SKILL.md`
- Validation: `rg` checks confirmed the new skill and `.agents/plans/` workflow are referenced from `AGENTS.md`; TOML parsing confirmed `.codex/agents/explorer.toml` and `.codex/agents/worker.toml` remained valid.
- Follow-ups: Use the new workflow for the next planned feature or behavior change so the pattern becomes the default repository habit.
