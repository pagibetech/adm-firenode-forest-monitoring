# ROUTER.md — adm-firenode-forest-monitoring

Task routing table for executor entry. The executor reads this file first to
determine which `.icm/` files and application files to load.

## Route by Task Type

| Task Type | Load | Why |
|-----------|------|-----|
| Continue / resume work | CURRENT_HANDOFF.md, CURRENT_CHECKPOINT.md, PROJECT_STATE.md, git status/log | Recover exact position |
| New feature | design/current-approved-design.md, plans/current-implementation-plan.md, tasks/ | Understand what to build |
| Bug fix | PROJECT_STATE.md (known issues), PROJECT_MEMORY.md (constraints), tests/ | Reproduce and fix |
| Code review | DECISIONS.md, design/ (relevant specs), tests/ | Evaluate against design |
| Refactor | PROJECT_MEMORY.md (architecture facts), DECISIONS.md, tests/ | Understand before changing |
| Investigation | PROJECT_MEMORY.md, ARCHITECTURE.md (if present), source tree | Map before acting |

## Quick Reference

- **State:** `.icm/state/PROJECT_STATE.md`
- **Memory:** `.icm/memory/PROJECT_MEMORY.md`
- **Handoff:** `.icm/handoffs/CURRENT_HANDOFF.md`
- **Checkpoint:** `.icm/checkpoints/CURRENT_CHECKPOINT.md`
- **Decisions:** `.icm/decisions/DECISIONS.md`
- **Design:** `.icm/design/`
- **Plans:** `.icm/plans/`
- **Tasks:** `.icm/tasks/`
- **HCNF Link:** `.icm/context/HCNF_LINK.md` (if present)

## Executor Commands

- `Continue.` — full bootstrap from AGENTS.md startup protocol
- `Review this repository and continue the current development.` — same
