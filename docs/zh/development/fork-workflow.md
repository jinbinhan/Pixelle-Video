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
