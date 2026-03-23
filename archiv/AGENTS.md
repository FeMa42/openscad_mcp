# Repository Guidelines

## Project Structure & Module Organization
- Root: Python MCP server (`openscad_fastmcp_server.py`), utilities (`build_knowledge_base.py`, `printing_pipeline.py`, `verify_server.py`).
- UI: `gradio_app/` (launch via `app.py`, config in `gradio_app/config.json`).
- Knowledge base: `faiss_index_*` (ignored by Git).
- OpenSCAD docs/info: `openscad_info/`, `openscad_documentation/`.
- Library configs: `library_configs/` (JSON for library detection/usage).
- Tests: `test_fastmcp_server.py`, `test_multiview.py` (script-style tests).
- Outputs: `scad_output/`, `output/` (rendered files; ignored by Git).

## Build, Test, and Development Commands
- Setup venv and deps:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Run MCP server (for MCP clients):
  ```bash
  python openscad_fastmcp_server.py
  ```
- Run UI:
  ```bash
  cd gradio_app && python app.py
  ```
- Run tests (ensure OpenSCAD is installed or set `OPENSCAD_EXECUTABLE`):
  ```bash
  python test_fastmcp_server.py
  python test_multiview.py
  ```

## Coding Style & Naming Conventions
- Python 3.8+; 4‑space indent; PEP 8; use f-strings.
- Prefer type hints on public functions and clear docstrings.
- Use `logging` (configured to stderr) over `print` in library code.
- File/module names: `snake_case.py`; tests start with `test_*.py`.

## Testing Guidelines
- Tests write images to `scad_output/` or temporary dirs; do not commit artifacts.
- OpenSCAD must be available (`openscad` in PATH) or set:
  ```bash
  export OPENSCAD_EXECUTABLE=/path/to/OpenSCAD
  ```
- Keep tests deterministic and fast; prefer minimal geometry and small images.

## Commit & Pull Request Guidelines
- Commits: short, imperative summaries (e.g., "improve logging", "add gcode generation").
- PRs include: clear description, rationale, test evidence (logs or small PNGs), and any config/docs updates.
- Avoid committing machine-specific paths or API keys; use placeholders in `gradio_app/config.json`.

## Security & Configuration Tips
- Never commit secrets. Use env vars or a local `.env`.
- Configure via `gradio_app/config.json` and environment variables: `OPENSCAD_EXECUTABLE`, `OPENSCAD_OUTPUT_DIR`, `FAISS_INDEX_PATH`, `OPENSCAD_USER_LIBRARY_PATH`, etc.
- Large indices and renders are already ignored by `.gitignore`.

## Agent-Specific Instructions
- Make minimal, focused changes; match existing patterns/names.
- Update README or this file when commands or structure change.
- Do not introduce heavy dependencies without discussion.

