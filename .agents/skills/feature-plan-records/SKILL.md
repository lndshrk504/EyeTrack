---
name: feature-plan-records
description: Use this skill when a user asks for a plan, when proposing or refining a new feature or nontrivial behavior change in EyeTrack, or when implementing a plan-backed change that must be recorded in both a per-feature plan file and the master implementation log.
---

# Feature plan records

## Goal

Maintain one stable working plan file per feature or change, and one append-only master implementation log for completed work.

## Required workflow

1. Choose or create the working feature plan file.
   - Reuse an existing file under `.agents/plans/` if it already tracks the same feature or change.
   - Otherwise create a new file named `YYYY-MM-DD-short-feature-title.md`.
   - Keep the path stable while the plan is discussed, refined, and implemented.

2. Use the working feature plan file during planning.
   Record:
   - a unique human-readable title
   - current status
   - goal
   - active paths
   - contracts to preserve
   - planned edits
   - validation plan
   - implementation summary once work lands

3. Keep `.agents/PLANS.md` reserved for implemented work.
   - Do not use it as scratch planning space.
   - Append to it only after the planned change has been implemented.

4. When implementation completes:
   - update the working feature plan status to `Implemented`
   - append a dated entry to `.agents/PLANS.md`
   - include the working plan path, summary, changed files, validation, and follow-ups

5. In the handoff, report both records.
   State:
   - which working feature plan file was created or updated
   - whether `.agents/PLANS.md` was appended
   - any remaining follow-up items still left in the working plan

## Default file shapes

Working feature plan:

```md
# Feature Title

- Status: Planning | Ready for implementation | Implemented
- Created: YYYY-MM-DD
- Last updated: YYYY-MM-DD

## Goal
## Active paths
## Contracts to preserve
## Planned edits
## Validation
## Implementation summary
```

Master implementation log entry:

```md
## YYYY-MM-DD - Feature Title
- Plan file: `.agents/plans/YYYY-MM-DD-short-feature-title.md`
- Summary:
- Changed files:
- Validation:
- Follow-ups:
```

## Do not

- do not create multiple competing plan files for the same feature or change
- do not overwrite `.agents/PLANS.md` with planning drafts
- do not mark a feature as logged in the master record before implementation actually lands
