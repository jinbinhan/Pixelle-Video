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

## Local Runtime Setup

Use the project virtual environment at `.venv`.

Initial setup or repair:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m playwright install chromium
```

Run the Web UI:

```powershell
.\.venv\Scripts\python.exe -m streamlit run web/app.py --server.port 8502 --server.headless true
```

Port `8501` may already be used by another local Streamlit app, so this workspace currently uses `8502`.

Runtime checks:

```powershell
.\.venv\Scripts\python.exe -c "import loguru, streamlit, playwright; print('imports ok')"
ffmpeg -version
```

FFmpeg is installed and available on PATH. Playwright Chromium has been installed under the user Playwright cache.

## Local LLM Setup

The local `config.yaml` is ignored by Git and currently configures an OpenAI-compatible llama.cpp server:

```yaml
llm:
  api_key: "EMPTY"
  base_url: "http://192.168.50.112:8012/v1"
  model: "gemma-4-31b-abliterated-Q8_0.gguf"
```

The server is reachable from this machine:

```powershell
Invoke-WebRequest -UseBasicParsing http://192.168.50.112:8012/v1/models
```

Pixelle-Video can call this LLM through `LLMService`. For short prompts with low `max_tokens`, this model may return text in `reasoning_content` while `message.content` is empty. For Pixelle-Video JSON-style prompts, use explicit "return only JSON/final answer" wording and enough `max_tokens`.

Verified project-level call:

```powershell
.\.venv\Scripts\python.exe -c "from pixelle_video.config import config_manager; print(config_manager.config.llm.base_url); print(config_manager.config.validate_required())"
```

## Local ComfyUI Setup

The local `config.yaml` also configures a self-hosted ComfyUI server:

```yaml
comfyui:
  comfyui_url: "http://192.168.50.112:8188"
  comfyui_api_key: ""
  runninghub_api_key: ""
  runninghub_concurrent_limit: 1

  tts:
    default_workflow: selfhost/tts_edge.json

  image:
    default_workflow: selfhost/image_flux.json
    prompt_prefix: "Minimalist black-and-white matchstick figure style illustration, clean lines, simple sketch style"

  video:
    default_workflow: selfhost/video_ltx2.3_t2v_i2v_single_stage_distilled_full.json
    prompt_prefix: "Minimalist black-and-white matchstick figure style illustration, clean lines, simple sketch style"
```

ComfyUI is reachable from this machine:

```powershell
Invoke-WebRequest -UseBasicParsing http://192.168.50.112:8188/system_stats
Invoke-WebRequest -UseBasicParsing http://192.168.50.112:8188/object_info
```

Image generation should use `selfhost/image_flux.json`. Video generation should use `selfhost/video_ltx2.3_t2v_i2v_single_stage_distilled_full.json`, which was converted from the LTX 2.3 example workflow at `/mnt/data/apps/ComfyUI/custom_nodes/ComfyUI-LTXVideo/example_workflows/2.3/LTX-2.3_T2V_I2V_Single_Stage_Distilled_Full.json`.

Pixelle-Video only lists video workflows whose filename contains `video_`, so the LTX workflow is committed with a `video_` prefix. The converted workflow has been verified to parse with ComfyKit and exposes `prompt`, `width`, and `height` parameters. A full video generation run has not yet been completed in this workspace because it may be slow; if execution fails, first check that the ComfyUI server has the exact model files and custom nodes referenced by that workflow.

## Persistent Notes Rule

When future work creates durable project decisions, workflows, repository conventions, or setup details that later AI assistants should know, update `AGENTS.md` and, when useful for humans, add or update a file under `docs/`.
