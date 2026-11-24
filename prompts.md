# Prompts

- 2026-11-24: Asked to create `prompts.md` so `AGENTS.md` can do its work. Changed: created this prompt log. It worked.
- 2026-11-24: Asked to update `spec.md` to describe a Python desktop app using Tkinter without building anything. Changed: added the application platform and Tkinter interface structure sections. It worked.
- 2026-11-24: Asked to read `spec.md` and build the Python Tkinter desktop app using `index.html` as the behavior reference. Changed: added `app.py`, separated engineering logic in `beam_core.py`, and added a W12x26 baseline test. The core test and Python compilation passed.
- 2026-11-24: Follow-up validation found invalid Tkinter padding in `app.py`. Changed: corrected the label padding and reran compilation, the baseline unit test, and a Tkinter initialization smoke test. They passed.
- 2026-11-24: Asked to run every validation case in `spec.md` against the beam calculations and report expected versus actual values. Changed: ran the single W12x26 baseline case through `beam_core.py` and its unit test. It passed; all specified values matched at reported precision.
- 2026-11-24: Asked to add Save/Open beam file support and update `spec.md`. Changed: added the File menu, JSON save/open implementation, a deflection-limit input, and specification coverage for beam files.
- 2026-11-24: Asked to add and build a button that exports the along-beam x, V, M, and deflection table to CSV. Changed: updated `spec.md`, added the export button and Excel-compatible CSV writer, and added a CSV export test. Validation passed.
