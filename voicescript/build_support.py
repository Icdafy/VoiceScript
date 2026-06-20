from __future__ import annotations

import importlib.util
from pathlib import Path


def collect_package_modules_without_import(package_name: str) -> list[str]:
    """List package modules by walking files instead of importing the package.

    Qwen's top-level package imports nagisa, which can fail on Windows paths
    before VoiceScript installs its fallback. PyInstaller still needs these
    module names, so we discover them from the package directory.
    """
    spec = importlib.util.find_spec(package_name)
    if spec is None or not spec.submodule_search_locations:
        return []

    modules = {package_name}
    for package_root in spec.submodule_search_locations:
        root = Path(package_root)
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(root).with_suffix("")
            parts = list(relative.parts)
            if parts[-1] == "__init__":
                module_parts = parts[:-1]
            else:
                module_parts = parts
            module_name = ".".join([package_name, *module_parts]) if module_parts else package_name
            modules.add(module_name)
    return sorted(modules)


def _qwen_transformers_backend_modules() -> list[str]:
    modules = collect_package_modules_without_import("qwen_asr")
    return [
        module
        for module in modules
        if module == "qwen_asr"
        or module.startswith("qwen_asr.inference")
        or module.startswith("qwen_asr.core.transformers_backend")
    ]


def collect_asr_hiddenimports() -> list[str]:
    from PyInstaller.utils.hooks import collect_submodules

    hiddenimports = set(collect_submodules("voicescript"))
    hiddenimports.update(collect_submodules("whisper"))
    hiddenimports.update(collect_submodules("tiktoken_ext"))
    hiddenimports.update(_qwen_transformers_backend_modules())
    return sorted(hiddenimports)


def collect_asr_datas() -> list[tuple[str, str]]:
    from PyInstaller.utils.hooks import collect_data_files

    datas: list[tuple[str, str]] = []
    datas.extend(collect_data_files("whisper"))
    datas.extend(collect_data_files("qwen_asr"))
    return datas
