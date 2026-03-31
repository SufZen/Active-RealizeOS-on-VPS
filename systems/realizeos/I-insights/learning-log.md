# RealizeOS — Learning Log

Decisions, lessons, and observations from platform development. This feeds into the builder agents' memory layer.

## Format

Each entry: `[DATE] — Category — Lesson`
Categories: decision | lesson | architecture | bug | optimization

---

[2026-03-24] — architecture — YAML LLM routing config was completely ignored by router.py. Hardcoded model_map was overriding config. Fixed by making select_model() read from realize-os.yaml with fallback chain.

[2026-03-24] — bug — Analytics tracking (InteractionTimer, log_interaction) was fully implemented but never wired into process_message(). The entire evolution module was starved of data. Fixed by wrapping process_message() with tracker.

[2026-03-24] — architecture — V1 skill pipeline and review handler were hardcoded to call_claude, bypassing multi-LLM router. Fixed to route through route_to_llm() for proper model selection.

[2026-03-24] — architecture — Evolution handler (KB learning from conversations) was fully built but never called. Wired into process_message() between skill check and agent routing.

[2026-03-24] — decision — Enabled cross_system: true in config. Created state maps for all 6 missing systems to feed cross-system context.
