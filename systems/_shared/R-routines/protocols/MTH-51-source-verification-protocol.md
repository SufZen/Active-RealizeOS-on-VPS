# MTH-51 — Source Verification And Stale Data Protocol

## Purpose

Prevents investment workflows from treating stale, partial, or low-confidence data as reliable input.

## Rules

- Identify the source, date, and confidence of every market or holdings input.
- Flag any number older than its reasonable freshness window.
- If the source set conflicts, say so before giving advice.
- If a proposal depends on unresolved data conflicts, block the proposal.
