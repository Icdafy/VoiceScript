# VoiceScript 声笺录

声落成笺，语转为文。

VoiceScript v0.2.0 是从零重写的 Windows 桌面音频转文字工具。它只做完整转录：上传苹果或安卓录音文件，通过 Qwen3-ASR 输出按时间分段的文字内容，不总结、不整理纪要、不语义改写。

## v0.2.0 功能

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
release\VoiceScript-v0.2.0-windows-x64.zip
```

模型权重不会提交到 GitHub，也不会放入 release zip。首次使用模型时由 `qwen-asr` 下载到用户缓存。

## Sources

- Qwen3-ASR: <https://github.com/QwenLM/Qwen3-ASR>
- Qwen3-ASR blog: <https://qwen.ai/blog?id=qwen3asr>
- Hugging Face collection: <https://huggingface.co/collections/Qwen/qwen3-asr>
