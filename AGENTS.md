# Project Working Notes

This repository is a fork-based customization workspace for Pixelle-Video.

## Repository Remotes

- `origin`: `https://github.com/jinbinhan/Pixelle-Video.git`
- `upstream`: `https://github.com/AIDC-AI/Pixelle-Video`
- `upstream` push URL is intentionally disabled to avoid pushing to the official project by mistake.

## Branch Strategy

- `main`: tracks the official upstream baseline.
- `my-main`: long-lived customization branch. Use this as the base for local product changes.
- `feature/<name>`: short-lived branches for individual custom features.

Default work should happen on `my-main` or a feature branch created from `my-main`.

## Syncing Useful Upstream Updates

Use this flow when bringing in official updates:

```powershell
git checkout my-main
git fetch upstream
git merge upstream/main
git push
```

When only part of upstream is useful, prefer a smaller import:

```powershell
git log --oneline HEAD..upstream/main
git diff HEAD..upstream/main
git restore --source upstream/main -- path/to/file.py
git cherry-pick <commit_sha>
```

## Customization Guidelines

Prefer adding new files over editing upstream files. This keeps future merges easier.

- New video workflows: add a pipeline under `pixelle_video/pipelines/`, then register it in `pixelle_video/service.py`.
- New Web UI entry points: add a module under `web/pipelines/`, then register/import it in `web/pipelines/__init__.py`.
- New visual styles: add templates under `templates/` instead of modifying official templates.
- New ComfyUI or RunningHub workflows: add new JSON files under `workflows/selfhost/` or `workflows/runninghub/`.
- Private settings and API keys belong in `config.yaml`; do not commit secrets.

If core files must be changed, keep each requirement in a focused commit. Avoid mixing formatting-only changes, refactors, and behavior changes.

## Current Git Setup Notes

The local global Git ignore file is set to:

```text
C:/Users/jinbi/.gitignore_global
```

This avoids the previous warning about Git being unable to read `C:\Users\jinbi/.config/git/ignore`.

## Persistent Notes Rule

When future work creates durable project decisions, workflows, repository conventions, or setup details that later AI assistants should know, update `AGENTS.md` and, when useful for humans, add or update a file under `docs/`.
