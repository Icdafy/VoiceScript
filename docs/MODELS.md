# 模型说明

VoiceScript v0.2.2 只接入 Qwen3-ASR，不沿用 v0.1.x 的 Whisper 代码。

## 标准模型

- ASR：`Qwen/Qwen3-ASR-0.6B`
- 时间戳：`Qwen/Qwen3-ForcedAligner-0.6B`
- UI 名称：标准模型
- 默认选择，适合 6GB 显存机器优先跑通。

## 精准模型

- ASR：`Qwen/Qwen3-ASR-1.7B`
- 时间戳：`Qwen/Qwen3-ForcedAligner-0.6B`
- UI 名称：精准模型
- 准确率优先，资源占用更高。

## 输出原则

模型输出统一转换为 `TranscriptDocument`。导出器只写时间戳和识别文字，不生成总结、纪要、摘要、语义标签或说话人分离结果。
