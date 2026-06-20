# VoiceScript 声笺录

声落成笺，语转为文。

这是 VoiceScript 声笺录的 Obsidian 知识库文件夹。

## 当前版本

- 版本：v0.2.2
- 类型：Windows 桌面端音频转文字 app
- 开发方式：从零重写，不沿用 v0.1.4 源码
- 核心模型：Qwen3-ASR + Qwen3-ForcedAligner
- 输出原则：只输出带时间分段的完整文字转录，不总结、不纪要、不语义整理
- v0.2.2 重点：修复图标裁切、移除登录/账户入口、修复模块重叠、改为可滚动布局

## 功能边界

支持上传苹果和安卓常见录音格式，包括 `.m4a`、`.aac`、`.caf`、`.amr`、`.3gp`、`.ogg`、`.opus`、`.mp3`、`.wav`、`.flac`。

v0.2.2 暂不包含说话人分离、实时麦克风转写、会议纪要、总结或语义改写。

## 仓库

GitHub：<https://github.com/Icdafy/VoiceScript>
