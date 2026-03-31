# Authority Matrix

## Active Default

`paper_execute`

## Modes

1. `observe` — read only, no proposals that imply action
2. `recommend` — strategy and proposals only
3. `paper_execute` — proposals may be expressed as paper trades and queued actions
4. `live_with_approval` — reserved for future use
5. `autonomous_capped` — reserved for future use

## Governance

- Any mode above `paper_execute` requires an explicit written update.
- Mode changes should be logged in `I-insights/decision-log.md`.
