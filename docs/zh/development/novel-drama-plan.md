# 小说自动短剧方向计划

## 当前决策

我们不从零重写，也不把新方向深度绑死在 Pixelle-Video 原有通用视频生成流程里。

当前采用的路线是：先在这个项目上做一个干净隔离的新功能区，验证小说自动短剧方向；等短剧流程稳定后，再决定是否独立重构。

换句话说：先借这个项目的厨房试菜，菜谱跑通了，再开自己的餐厅。

## 为什么先借壳启动

Pixelle-Video 已经有一些可复用能力：

- Web UI 和任务入口。
- LLM 调用封装。
- TTS、字幕、视频合成、历史记录。
- ComfyUI / RunningHub 工作流调用基础。
- 本地 fork、`my-main` 分支和上游同步策略已经配置好。

这些能力适合帮助我们快速验证 MVP。

原项目现有剧本生成思路可以借鉴，但不能直接照搬。它当前主要是“主题/内容 -> 多段旁白 -> 每段生成画面 prompt -> 逐帧生成素材并合成”的旁白短视频流程。小说短剧需要的是“原文理解 -> 冲突改编 -> 角色卡 -> 场景 -> 镜头 -> 台词/旁白 -> 连续性控制”的叙事流程。

可以复用：

- `LinearVideoPipeline` 的阶段化流程思想。
- `PipelineContext` 的任务状态传递方式。
- `LLMService` 的结构化输出能力。
- `content_generators.py` 里的 JSON 解析和重试思路。
- 后续合成阶段的 `Storyboard`、TTS、模板、FFmpeg、历史记录。

不要直接复用：

- `topic_narration.py` 和 `content_narration.py` 的提示词目标，因为它们偏观点讲解/旁白，不适合戏剧冲突。
- 只用 `narrations` 数组表达内容的模型，因为短剧还需要角色、对白、动作、镜头语言和连续性信息。
- `generate_image_prompts` 的“一段旁白一个抽象画面 prompt”思路，后续需要改成“一个镜头绑定角色、场景、动作、台词、镜头运动和视觉连续性”。

但它也不适合作为长期短剧系统的完整架构：

- 原项目是通用视频生成，不是为小说、角色、剧集、镜头一致性设计的。
- ComfyUI workflow 适配容易受节点版本和模型文件名影响。
- 现有数据模型不够表达角色卡、分集剧情、场景、镜头、台词、重试单镜头等短剧生产概念。
- 如果直接硬塞进现有通用 pipeline，后续会变成技术债。

## 产品目标

长期目标是做一条“小说章节到短剧成片”的自动化流水线。

输入：

- 小说文本或章节。
- 可选：角色设定、风格要求、剧集时长、目标平台。

输出：

- 一集 30-90 秒竖屏短剧。
- 包含角色、场景、镜头、台词/旁白、字幕、音频、视频片段和最终 mp4。

## MVP 范围

第一阶段不要直接追求全自动生成视频。

第一阶段只做“可审核的剧本包”：

- 输入一段小说。
- AI 生成一集短剧结构化 JSON。
- 页面展示并允许人工编辑。
- 暂不接 ComfyUI 生成视频。

阶段 1 已采用“原文锚点优先”的实现原则。原因是本地 Gemma/llama.cpp 模型能生成结构化 JSON，但在小说改编任务中容易把原文替换成常见短剧套路。当前默认先用本地规则从原文中提取人物姓名、地点、道具和时间词，作为必须保留的 source anchors；LLM 生成剧本包后会检查这些锚点是否还在，如果跑偏会低温重试一次，仍失败则报错，不把错误剧本交给用户。

LLM 事实抽取接口保留为可选能力，但默认关闭。等后续换成更强的理解模型时，可以再打开 `use_llm_source_facts` 做更丰富的原文事实抽取。

阶段 1 页面还需要支持人工审核。当前 Web UI 已提供剧本包 JSON 编辑区：用户可以修改生成结果，点击“应用修改”时会按 `NovelDramaPackage` 结构校验；校验通过后页面展示更新后的剧本包。用户也可以把审核后的 JSON 保存到运行目录 `output/novel_drama_drafts/`，作为后续单镜头生成和成片流程的输入草稿。

剧本包至少包含：

- `episode_title`: 本集标题。
- `hook`: 前 3 秒钩子。
- `summary`: 本集剧情摘要。
- `characters`: 角色卡列表。
- `scenes`: 场景列表。
- `shots`: 镜头列表。
- `dialogue_or_narration`: 每个镜头的台词或旁白。
- `visual_prompt`: 每个镜头的画面提示词。
- `continuity_notes`: 人物、服装、道具、地点连续性提示。
- `ending_hook`: 结尾悬念。

## 推荐目录隔离

后端新增：

```text
pixelle_video/pipelines/novel_drama.py
pixelle_video/models/novel_drama.py
pixelle_video/prompts/novel_drama.py
```

前端新增：

```text
web/pipelines/novel_drama.py
```

可选模板：

```text
templates/1080x1920/video_drama.html
```

原则：

- 尽量新增文件，不改官方核心逻辑。
- 与现有 `standard`、`custom`、`i2v`、`asset_based` pipeline 保持隔离。
- 只有注册入口时才少量修改 `pixelle_video/service.py` 和 `web/pipelines/__init__.py`。

## 迭代计划

### 阶段 1：剧本包 MVP

目标：小说文本输入后，稳定生成短剧 JSON。

要做：

- 定义 `NovelDramaRequest`、`NovelDramaPackage`、`CharacterCard`、`DramaScene`、`DramaShot` 数据模型。
- 编写小说改编提示词。
- 新增后端 `NovelDramaPipeline`。
- 新增 Web 页面：文本输入、参数选择、生成按钮、JSON 展示。
- 增加 JSON 解析失败的重试和修复逻辑。
- 提供人工审核编辑区，支持应用修改、恢复生成版、保存草稿。

验收：

- 输入 1000-3000 字小说片段，能输出结构稳定的短剧 JSON。
- 每个镜头有明确画面、人物、动作、台词/旁白和时长。
- 输出可以人工编辑、校验、下载或保存为草稿。

### 阶段 2：角色一致性设计

目标：让同一角色在不同镜头中保持一致。

要做：

- 为每个角色生成固定角色卡。
- 每个角色包含外貌、服装、气质、禁用项和英文视觉提示词。
- 为后续参考图、IP-Adapter、PuLID、InstantID 或 LoRA 留接口。

验收：

- 镜头提示词能引用角色 ID。
- 同一角色在不同镜头中的描述不互相矛盾。

### 阶段 3：镜头素材生成

目标：把剧本包中的镜头接到 ComfyUI。

要做：

- 先支持单镜头生成，不做整集自动跑满。
- 允许重试单镜头。
- 保存每个镜头的输入 prompt、workflow、输出文件和错误信息。
- 优先支持图片生成，再支持图生视频。

当前实现从“单镜头图片”开始：在小说短剧页面中选择审核后的某个 shot，使用该 shot 的 `visual_prompt_en` 调用配置默认的图片 workflow，也可以临时选择其他 `image_*.json` workflow。生成结果保存到 `output/novel_drama_assets/`，页面展示图片和实际使用的 prompt。视频生成仍然保持未接入，等单张镜头图稳定后再继续。

2026-04-27 的真实 ComfyUI 测试结果：小说短剧单镜头入口已经能提交到 ComfyUI，但当前服务器还没有可用的本地图片模型组合。`selfhost/image_flux.json` 原先缺少 `easy int` 节点，已改成原生整数宽高；继续提交后发现服务器缺少 `flux1-dev.safetensors`、`clip_l.safetensors`、`t5xxl_fp8_e4m3fn.safetensors` 和 `ae.safetensors`。`selfhost/image_qwen.json` 也缺 Qwen Image 模型和 LoRA。`selfhost/image_nano_banana.json` 节点存在，但运行时报 `Unauthorized: Please login first to use this node.`。所以下一步如果要真的出图，需要先在 ComfyUI 服务器补齐 Flux/Qwen 图片模型，或配置 Gemini Image 节点授权，或提供一个已验证可运行的图片 workflow。

验收：

- 单个镜头可以从 JSON 生成图片或视频片段。
- 失败时能看到具体 ComfyUI 错误。
- 不影响现有通用视频生成入口。

### 阶段 4：配音、字幕和成片

目标：把镜头片段合成为一集短剧。

要做：

- 根据镜头台词或旁白生成 TTS。
- 生成字幕。
- 用竖屏短剧模板合成视频。
- 支持背景音乐、片头、片尾、结尾悬念卡。

验收：

- 能输出一条 30-90 秒 mp4。
- 字幕、配音、镜头顺序基本正确。
- 可以保留任务历史。

### 阶段 5：评估是否独立重构

触发条件：

- 剧本包质量稳定。
- 单镜头生成流程稳定。
- 至少能连续生成多集短剧样片。
- 当前项目结构开始限制短剧功能继续发展。

如果满足，再考虑新建独立项目，把短剧核心抽出去。

## 当前下一步

下一步优先做阶段 1。

具体任务：

1. 新增 `pixelle_video/models/novel_drama.py`，定义短剧 JSON 数据结构。
2. 新增 `pixelle_video/prompts/novel_drama.py`，写小说改编提示词。
3. 新增 `pixelle_video/pipelines/novel_drama.py`，调用 LLM 生成剧本包。
4. 新增 `web/pipelines/novel_drama.py`，提供小说输入和结果展示页面。
5. 注册 Web 入口，让页面中能选择“小说短剧”。

第一轮先不要接 ComfyUI。先把剧本包质量调通。
