# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata


block_cipher = None
binaries = []
datas = []
hiddenimports = []

qwen_hiddenimports = [
    "qwen_asr",
    "qwen_asr.inference",
    "qwen_asr.inference.qwen3_asr",
    "qwen_asr.inference.qwen3_forced_aligner",
    "qwen_asr.inference.utils",
    "qwen_asr.core",
    "qwen_asr.core.transformers_backend",
    "qwen_asr.core.transformers_backend.configuration_qwen3_asr",
    "qwen_asr.core.transformers_backend.modeling_qwen3_asr",
    "qwen_asr.core.transformers_backend.processing_qwen3_asr",
]
hiddenimports += qwen_hiddenimports
datas += [(".venv/Lib/site-packages/qwen_asr/inference/assets", "qwen_asr/inference/assets")]

for package in [
    "transformers",
    "accelerate",
    "librosa",
    "soundfile",
    "numpy",
    "torch",
]:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

for package in ["qwen-asr", "transformers", "accelerate", "torch"]:
    try:
        datas += copy_metadata(package)
    except Exception:
        pass


a = Analysis(
    ["voicescript/ui/app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["vllm", "gradio", "flask", "notebook", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VoiceScript",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VoiceScript",
)
