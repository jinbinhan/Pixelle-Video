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

## Novel Drama Direction

Current product direction decision: use Pixelle-Video as a temporary, isolated shell for a novel-to-short-drama MVP, then decide later whether to extract the short-drama core into a new standalone project.

Use the metaphor agreed with the user: borrow this project's kitchen to test the recipe; once the recipe works, open our own restaurant.

Do not rewrite from scratch yet, and do not deeply couple the new short-drama logic to the existing generic pipelines. Build a clean isolated feature area first:

- Backend pipeline: `pixelle_video/pipelines/novel_drama.py`
- Web UI entry: `web/pipelines/novel_drama.py`
- Domain models: `pixelle_video/models/novel_drama.py`
- Prompts: `pixelle_video/prompts/novel_drama.py`
- Optional vertical drama template: `templates/1080x1920/video_drama.html`

The first milestone is not full video generation. The first milestone is a reviewable "script package": input a novel excerpt and generate structured JSON containing episode hook, characters, scenes, shots, dialogue/narration, visual prompts, and continuity notes. Only after the script package is stable should ComfyUI video generation and final composition be connected.

The first implementation uses source anchors before adaptation. Local Gemma/llama.cpp can produce valid JSON while drifting into unrelated short-drama tropes, so `NovelDramaPipeline` defaults to rule-based source fact extraction for names, locations, props, and time markers. The generated package is checked against those markers and retried once at lower temperature if it drifts. Optional LLM source-fact extraction exists behind `use_llm_source_facts`, but it is off by default until a stronger model is used.

Human-readable plan: `docs/zh/development/novel-drama-plan.md`.

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

The standalone Image To Video (`web/pipelines/i2v.py`) page is separate from the standard video-template media selector. It scans `i2v_*.json` and self-hosted `video_*.json` workflows, preferring self-hosted workflows by default. For local workflows, the page writes a task-local adapted workflow that maps the uploaded first-frame image to `LoadImage`, sets the LTX `bypass_i2v` boolean to `false`, and gives each `SaveVideo` node a unique `filename_prefix` so ComfyUI cache hits still return a current video output. The committed source workflow is left unchanged.

The downloaded LTX example originally used `ClownSampler_Beta` at node `4967`. The local ComfyUI server does not provide that custom node, so the committed workflow replaces node `4967` with the built-in `KSamplerSelect` using `euler_ancestral_cfg_pp`. After this replacement, all workflow node `class_type` values are present in the server `/object_info`.

The LTX workflow is adapted to the current server schema from `/object_info`: model checkpoints use `ltx-2.3-22b-dev-bf16.safetensors`, the text encoder uses `gemma_3_12B_it_fp4_mixed.safetensors`, `SaveVideo` nodes include `codec: auto`, newer required inputs such as `strength`, `img_compression`, `cfg`, and `skip_blocks` are filled, tiled VAE decode uses numeric tile/overlap values, and LoRA nodes use the server's available LTX LoRA filenames with explicit `strength_model`. A local schema check against `/object_info` currently reports zero obvious required-input/combo/type issues.

## Persistent Notes Rule

When future work creates durable project decisions, workflows, repository conventions, or setup details that later AI assistants should know, update `AGENTS.md` and, when useful for humans, add or update a file under `docs/`.
