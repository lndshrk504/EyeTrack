# Planning Records Workflow

- Status: Implemented
- Created: 2026-04-22
- Last updated: 2026-04-22

## Goal

Add a repository rule and reusable skill so EyeTrack keeps:

1. one stable working plan file per feature or change under `.agents/plans/`
2. one append-only master implementation log in `.agents/PLANS.md`

## Active paths

- `AGENTS.md`
- `.codex/agents/explorer.toml`
- `.codex/agents/worker.toml`
- `.agents/PLANS.md`
- `.agents/plans/2026-04-22-planning-records-workflow.md`
- `.agents/skills/feature-plan-records/SKILL.md`

## Contracts to preserve

- Existing DeepLabCut runtime, bridge, and environment skills remain in force.
- `.agents/PLANS.md` is reserved for implemented work, not planning drafts.
- Each planned feature or change keeps one stable file path while the text is refined.

## Planned edits

- Add a `feature-plan-records` skill that defines the two-record workflow.
- Update `AGENTS.md` so planning a new feature or nontrivial change requires the planning-records skill.
- Replace the old ExecPlan-in-`.agents/PLANS.md` rule with:
  - working plan files in `.agents/plans/`
  - master implementation summaries in `.agents/PLANS.md`
- Update Codex worker and explorer defaults so they look for existing feature plans and write back to the two records.
- Record this workflow change in both the working plan and the master implementation log.

## Validation

- Confirm `AGENTS.md` references:
  - `$feature-plan-records`
  - `.agents/plans/`
  - `.agents/PLANS.md` as the master log
- Confirm updated `.codex` TOML files still parse.
- Confirm the current change itself is recorded in both the working plan file and the master log.

## Implementation summary

- Added the `feature-plan-records` skill.
- Updated repository rules so planning discussions use a stable per-feature plan file.
- Converted `.agents/PLANS.md` into the append-only master implementation log.
- Added this working plan file as the first concrete example of the workflow.
