# VoiceScript 声笺录

声落成笺，语转为文。

VoiceScript v0.2.4 是从零重写的 Windows 桌面音频转文字工具。它只做完整转录：上传苹果或安卓录音文件，通过 Qwen3-ASR 输出按时间分段的文字内容，不总结、不整理纪要、不语义改写。

## v0.2.4 更新

- 新增「运算设备」指示：界面显示当前使用 GPU 加速还是 CPU 运算。
- 转录进度新增「预计剩余时间」估算。
- 深色模式改为纯黑背景，并将 Windows 标题栏同步为深色（不再有顶部白条）。
- 为 6GB 显存的笔记本 GPU 下调标准模型推理 batch，降低显存溢出风险。

> GPU 加速说明：需安装 CUDA 版 PyTorch，例如
> `pip install torch==2.12.1+cu126 --index-url https://download.pytorch.org/whl/cu126`，
> 程序会自动检测并使用 NVIDIA 显卡；未安装时自动回退到 CPU。

## v0.2.3 更新

- 核心转录升级：长音频按 **30 分钟自动分段**逐段送入 Qwen3-ASR，稳定转录数小时录音，默认以中文输出，并生成带时间戳的文本。
- 转录进度细化：实时显示「正在转录第 N/M 段（时间区间）· 提取/识别中」等阶段信息，进度条显示百分比。
- 导航精简为「首页 / 文件列表 / 历史记录」，移除设置与帮助入口；新增可用的文件列表页与历史记录页。
- 修复「说话人识别」开关无法开启的问题（开关现可切换，作为偏好保存）。
- 「转录模型」说明更详细，解释标准 / 精准两档的差异与适用场景。
- 深色模式改为完全深色，去除卡片的浅色描边。

## v0.2.2 更新

- 修复全局图标渲染：图标不再被裁切到角落，全部完整居中显示；「设置」改用清晰的齿轮图标。
- 移除「登录 / 注册」与右上角「账户」入口，界面更聚焦。
- 修复上传区「选择文件」按钮与下方三张功能卡重叠的问题。
- 主内容区改为可滚动布局，窗口高度不足时自动滚动，任何尺寸下都不再重叠。

## v0.2.1 更新

- 全面扁平化的界面重做：统一的线性矢量图标、更克制的卡片描边与柔和投影。
- 更丝滑的交互：开关采用缓动动画滑块、进度条平滑过渡、转录结果与窗口淡入。
- 上传区拖拽时高亮反馈，下拉菜单、滚动条、提示气泡统一风格。
- 最近文件表重做：文件图标、状态徽标、悬停高亮与行内操作按钮。

## 功能

- Windows 桌面 UI：左侧导航、中央上传区、右侧转录设置、最近文件表。
- 黑色 / 白色主题切换，并持久化到用户配置。
- 支持 `.m4a`、`.aac`、`.caf`、`.amr`、`.3gp`、`.ogg`、`.opus`、`.mp3`、`.wav`、`.flac`。
- 标准模型：`Qwen/Qwen3-ASR-0.6B` + `Qwen/Qwen3-ForcedAligner-0.6B`。
- 精准模型：`Qwen/Qwen3-ASR-1.7B` + `Qwen/Qwen3-ForcedAligner-0.6B`。
- 导出 TXT、Markdown、SRT、JSON，或一次导出全部格式。
- CLI 与桌面端共享同一套转录、导出和配置逻辑。

## Quick Start

```powershell
cd F:\声笺录
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m voicescript env
.\.venv\Scripts\python -m voicescript.ui
```

CLI 转录：

```powershell
.\.venv\Scripts\python -m voicescript transcribe `
  --input "F:\path\audio.m4a" `
  --out "F:\声笺录\transcripts" `
  --formats txt,md,srt,json `
  --model standard `
  --language auto
```

## Windows Build

```powershell
.\scripts\build-windows.ps1
```

输出文件：

```text
release\VoiceScript-v0.2.4-windows-x64.zip
```

模型权重不会提交到 GitHub，也不会放入 release zip。首次使用模型时由 `qwen-asr` 下载到用户缓存。

## Sources

- Qwen3-ASR: <https://github.com/QwenLM/Qwen3-ASR>
- Qwen3-ASR blog: <https://qwen.ai/blog?id=qwen3asr>
- Hugging Face collection: <https://huggingface.co/collections/Qwen/qwen3-asr>
