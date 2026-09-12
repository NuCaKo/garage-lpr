# Garage LPR agent guide

## Product invariant

The system is fail-safe: no recognition uncertainty, dependency failure, or
unexpected exception may cause a gate-open command. Optimize in this order:
stability, recognition accuracy, resource use, modularity, configuration, UI.

## Architecture boundaries

- `backend/src/garage_lpr/api`: transport only; no business rules.
- `config`: validated bootstrap and database-backed runtime configuration.
- `database`: SQLAlchemy models, sessions, migrations, repositories.
- Future external integrations must live behind adapters: camera, detector, OCR,
  gate, and storage.
- Queues must be bounded and frame processing must use latest-frame-wins.
- Never log secrets or return camera/gate credentials from API responses.

## Verification

- Backend: `python -m pytest backend/tests`
- Frontend: `npm --prefix frontend run check && npm --prefix frontend run build`
- Run Graphify update after source or architecture changes.

## graphify

Before answering codebase questions, query `graphify-out/graph.json` when it
exists. After code changes run `graphify --update`; after documentation changes,
the semantic update must be run manually. The installed post-commit hook keeps
the code graph current after commits.
