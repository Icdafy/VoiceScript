# VoiceScript v0.2.4 发布说明

## 性能 / 设备

- **GPU/CPU 运算设备指示**：界面显示当前转录使用「GPU 加速 · 显卡名」还是「CPU 运算（较慢）」。
- **预计剩余时间**：转录过程中根据已用时实时估算剩余时间。
- **GPU 加速**：安装 CUDA 版 PyTorch 后自动检测并使用 NVIDIA 显卡，未安装时回退 CPU。
  例：`pip install torch==2.12.1+cu126 --index-url https://download.pytorch.org/whl/cu126`。
  在 RTX 3060 等显卡上，长音频转录通常比 CPU 快约 10–20 倍。
- 为 6GB 显存的笔记本 GPU 下调标准模型推理 batch（8 → 4），降低显存溢出风险。

## 界面

- **深色模式改为纯黑背景**（`#000000`），卡片为近黑色，去除残留浅色块。
- **Windows 标题栏同步深色**：深色模式下顶部标题栏不再是白条（DWM 沉浸式深色）。

## 说明

- 打包的 .exe 默认捆绑 CPU 版 PyTorch，因此安装包始终走 CPU；从源码运行（已装 CUDA torch 的 venv）才会使用 GPU。
  如需可用 GPU 的安装包，需用装有 CUDA torch 的环境重新打包（体积更大，且仅适用于带 NVIDIA 显卡的机器）。

## 兼容性

- 转录、导出、模型档位与 v0.2.3 一致；30 分钟分段、默认中文、带时间戳输出不变。
- 用户配置（主题、保存位置）继续沿用。

## 发布文件

- `VoiceScript-v0.2.4-windows-x64.zip`
