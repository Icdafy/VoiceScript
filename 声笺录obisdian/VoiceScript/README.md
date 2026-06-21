# VoiceScript 声笺录

声落成笺，语转为文。

这是 VoiceScript 声笺录的 Obsidian 知识库文件夹。

## 当前版本

- 版本：v0.2.4
- 类型：Windows 桌面端音频转文字 app
- 开发方式：从零重写，不沿用 v0.1.4 源码
- 核心模型：Qwen3-ASR + Qwen3-ForcedAligner
- 输出原则：只输出带时间分段的完整文字转录，不总结、不纪要、不语义整理
- v0.2.4 重点：GPU/CPU 运算设备指示、预计剩余时间、纯黑深色模式 + 深色标题栏、6GB 显存优化
- GPU 加速：装 CUDA 版 torch（如 `torch==2.12.1+cu126`）后自动用 NVIDIA 显卡，否则回退 CPU

## 功能边界

支持上传苹果和安卓常见录音格式，包括 `.m4a`、`.aac`、`.caf`、`.amr`、`.3gp`、`.ogg`、`.opus`、`.mp3`、`.wav`、`.flac`。

v0.2.4 暂不包含说话人分离、实时麦克风转写、会议纪要、总结或语义改写。

## 仓库

GitHub：<https://github.com/Icdafy/VoiceScript>
