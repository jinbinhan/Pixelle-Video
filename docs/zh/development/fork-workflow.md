# 二开与同步官方更新

这个仓库是从官方 Pixelle-Video fork 出来的二开工作区。目标是：可以按照自己的需求改项目，同时还能持续同步官方更新里对我们有用的部分。

## 当前仓库关系

- `origin`: `https://github.com/jinbinhan/Pixelle-Video.git`
- `upstream`: `https://github.com/AIDC-AI/Pixelle-Video`
- `upstream` 的 push 地址已禁用，避免误推到官方仓库。

## 分支约定

- `main`: 保留官方基线，跟随 `upstream/main`。
- `my-main`: 我们自己的长期二开主分支。
- `feature/<name>`: 每个具体需求单独开的功能分支。

日常开发优先从 `my-main` 开始：

```powershell
git checkout my-main
git checkout -b feature/your-feature
```

开发完成后合回 `my-main`：

```powershell
git checkout my-main
git merge feature/your-feature
git push
```

## 同步官方更新

当需要同步官方主分支时：

```powershell
git checkout my-main
git fetch upstream
git merge upstream/main
git push
```

如果官方更新很多，但只想拿一部分，可以先查看差异：

```powershell
git log --oneline HEAD..upstream/main
git diff HEAD..upstream/main
```

只拿某个文件：

```powershell
git restore --source upstream/main -- path/to/file.py
```

只拿某个提交：

```powershell
git cherry-pick <commit_sha>
```

## 二开原则

尽量新增文件，少改官方核心文件。这样以后同步官方更新时冲突更少。

- 新视频生成流程：新增 `pixelle_video/pipelines/your_pipeline.py`，再到 `pixelle_video/service.py` 注册。
- 新 Web 页面或功能入口：新增 `web/pipelines/your_ui.py`，再到 `web/pipelines/__init__.py` 引入。
- 新视觉样式：新增 `templates/` 下的 HTML 模板，不直接改官方模板。
- 新 ComfyUI 或 RunningHub 工作流：新增 `workflows/selfhost/` 或 `workflows/runninghub/` 下的 JSON 文件。
- 私有配置、API Key：放在 `config.yaml`，不要提交到 Git。

如果必须修改核心文件，尽量让每个 commit 只对应一个明确需求。不要把格式化、重构和功能改动混在同一个 commit 里。

## 给后续 AI 的提醒

后续 AI 接手任务时，优先读取根目录的 `AGENTS.md`。那里记录了本仓库的 remote、分支策略、同步方式和二开约定。

以后如果任务中产生了长期有效的项目决策、工作流约定、仓库配置或环境说明，需要继续更新 `AGENTS.md`；如果这些内容也适合人阅读，再同步补充到 `docs/` 目录。

## 本地启动环境

本项目使用根目录下的 `.venv` 作为本地 Python 虚拟环境。不要直接用系统 Python 启动，否则可能出现类似 `ModuleNotFoundError: No module named 'loguru'` 的依赖错误。

首次安装或修复依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m playwright install chromium
```

启动 Web UI：

```powershell
.\.venv\Scripts\python.exe -m streamlit run web/app.py --server.port 8502 --server.headless true
```

当前本机 `8501` 端口可能已经被其他 Streamlit 应用占用，所以这个项目默认用 `8502` 查看：

```text
http://localhost:8502
```

运行前可以检查关键依赖：

```powershell
.\.venv\Scripts\python.exe -c "import loguru, streamlit, playwright; print('imports ok')"
ffmpeg -version
```

FFmpeg 已在系统 PATH 上可用；Playwright Chromium 已安装到当前用户的 Playwright 缓存目录。

## 本地大语言模型配置

本地 `config.yaml` 已被 Git 忽略，用来保存私有运行配置。当前 LLM 使用一台 OpenAI 兼容的 llama.cpp 服务：

```yaml
llm:
  api_key: "EMPTY"
  base_url: "http://192.168.50.112:8012/v1"
  model: "gemma-4-31b-abliterated-Q8_0.gguf"
```

可以用下面命令确认服务可访问：

```powershell
Invoke-WebRequest -UseBasicParsing http://192.168.50.112:8012/v1/models
```

项目的 `LLMService` 已验证可以调用该接口。需要注意：这个模型在短输出、低 `max_tokens` 时可能把内容放在 `reasoning_content`，导致标准 `message.content` 为空。用于 Pixelle-Video 时，提示词最好明确要求“只返回 JSON / 只返回最终答案”，并给足 `max_tokens`。

## 本地 ComfyUI 配置

本地 `config.yaml` 同样保存 ComfyUI 连接信息，不提交到 Git。当前使用的 ComfyUI 服务是：

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

可以用下面命令确认 ComfyUI 服务可访问：

```powershell
Invoke-WebRequest -UseBasicParsing http://192.168.50.112:8188/system_stats
Invoke-WebRequest -UseBasicParsing http://192.168.50.112:8188/object_info
```

图片生成使用 `selfhost/image_flux.json`。视频生成使用 `selfhost/video_ltx2.3_t2v_i2v_single_stage_distilled_full.json`。这个 LTX 2.3 工作流来自服务器上的：

```text
/mnt/data/apps/ComfyUI/custom_nodes/ComfyUI-LTXVideo/example_workflows/2.3/LTX-2.3_T2V_I2V_Single_Stage_Distilled_Full.json
```

注意：Pixelle-Video 的 Web UI 只会把文件名包含 `video_` 的工作流识别为视频工作流，所以 LTX 文件在项目中改名为 `video_ltx2.3_t2v_i2v_single_stage_distilled_full.json`。该工作流已转换成 ComfyUI API JSON 格式，并验证 ComfyKit 可以识别 `prompt`、`width`、`height` 参数。完整视频生成还没有在本机跑完验证，如果后续执行失败，优先检查 ComfyUI 服务器上对应模型文件和自定义节点是否齐全。

单独的“图生视频”页面位于 `web/pipelines/i2v.py`，它不是读取标准视频模板里的 `comfyui.video.default_workflow`。这个页面现在会扫描 `i2v_*.json` 和本地 `selfhost/video_*.json`，并优先选择本地工作流。执行本地工作流时，页面会在当前任务目录生成一个临时适配版 workflow：把上传的首帧图片映射到 `LoadImage`，把 LTX 的 `bypass_i2v` 设为 `false`，并给每个 `SaveVideo` 节点写入唯一的 `filename_prefix`，避免 ComfyUI 缓存命中时本次 history 不返回视频输出；原始提交的 workflow 文件不被修改。

下载的 LTX 示例工作流原本在 `4967` 节点使用 `ClownSampler_Beta`。当前本地 ComfyUI 服务器没有这个自定义节点，所以项目里的工作流已把 `4967` 替换为内置 `KSamplerSelect`，采样器使用 `euler_ancestral_cfg_pp`。替换后已用服务器 `/object_info` 校验，工作流里的所有 `class_type` 都能在当前 ComfyUI 环境中找到。

该 LTX 工作流也已按当前服务器 `/object_info` 的节点 schema 做兼容：模型文件使用 `ltx-2.3-22b-dev-bf16.safetensors`，文本编码器使用 `gemma_3_12B_it_fp4_mixed.safetensors`，`SaveVideo` 补充 `codec: auto`，新版必填参数如 `strength`、`img_compression`、`cfg`、`skip_blocks` 已补齐，tiled VAE decode 的 tile/overlap 参数改为合法数值，LoRA 节点使用服务器已有的 LTX LoRA 文件名并显式设置 `strength_model`。当前本地 schema 校验结果为 0 个明显 required/combo/type 问题。
