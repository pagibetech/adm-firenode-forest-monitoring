# ICM Workspace Router

This `.icm/` directory is the control plane for this development workspace.
Do NOT modify its structure manually — use `dres-icm` commands.

## Directory Map

| Path | Purpose | Managed By |
|------|---------|------------|
| `ROUTER.md` | This file — ICM structure reference | dres-icm |
| `state/PROJECT_STATE.md` | Objective project facts | dres-icm state |
| `memory/PROJECT_MEMORY.md` | Durable architecture knowledge | dres-icm memory |
| `handoffs/CURRENT_HANDOFF.md` | Where work stopped + next step | dres-icm handoff |
| `handoffs/history/` | Archived handoffs | dres-icm handoff |
| `decisions/DECISIONS.md` | Material decisions + rationale | dres-icm |
| `checkpoints/CURRENT_CHECKPOINT.md` | Exact resumable position | dres-icm checkpoint |
| `checkpoints/history/` | Archived checkpoints | dres-icm checkpoint |
| `design/` | Design documents (dated) | dres-icm design |
| `plans/` | Implementation plans (dated) | dres-icm plan |
| `tasks/` | Task ledger | dres-icm task |
| `stages/` | Pipeline stages (structured workflows) | Manual |
| `artifacts/` | Produced work | Manual / Executor |
| `evidence/` | Validation proof | Manual / Executor |
| `provenance/` | Origin records | Manual / Executor |
| `context/` | External linkage (e.g., HCNF) | dres-icm hcnf-link |
