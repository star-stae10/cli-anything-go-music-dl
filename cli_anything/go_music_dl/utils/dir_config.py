"""dir_config.py — 下载目录与软件 exe 路径的记忆与解析。

规则：
1. 用户显式传 --dir → 使用并持久化记住
2. 未传 --dir → 用上次记住的目录（存在则用）
3. 未记住 → 扫描常见位置找 `go music/data/downloads`（找到则记住）
4. 都找不到 → 抛 RuntimeError，要求指定 --dir

配置存用户配置目录（~/.config/cli-anything-go-music-dl/config.json），
跨项目/目录生效，且不污染包目录（利于打包发布）。
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

_CFG_HOME = os.path.join(
    os.path.expanduser("~"),
    ".config",
    "cli-anything-go-music-dl",
)
_CONFIG_FILE = os.path.join(_CFG_HOME, "config.json")

_DEFAULT_REL = ("go music", "data", "downloads")


def _load() -> dict:
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    try:
        os.makedirs(_CFG_HOME, exist_ok=True)
        merged = {**_load(), **data}
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    except OSError:
        # 配置目录不可写时静默降级：本次仍生效，只是不持久化
        pass


def get_saved_download_dir() -> Optional[str]:
    d = _load().get("download_dir")
    if d and os.path.isdir(d):
        return d
    return None


def save_download_dir(path: str) -> str:
    ap = os.path.abspath(path)
    if not os.path.isdir(ap):
        raise RuntimeError(f"下载目录不存在: {ap}。请先创建该目录，或改用已存在的目录。")
    _save({"download_dir": ap})
    return ap


def get_saved_exe_path() -> Optional[str]:
    p = _load().get("exe_path")
    if p and os.path.isfile(p):
        return p
    return None


def save_exe_path(path: str) -> str:
    ap = os.path.abspath(path)
    if not os.path.isfile(ap):
        raise RuntimeError(f"软件 exe 不存在: {ap}")
    _save({"exe_path": ap})
    return ap


def scan_default_candidates(cwd: Optional[str] = None) -> List[str]:
    """扫描常见位置下的 `go music/data/downloads`。"""
    cwd = cwd or os.getcwd()
    cands = []
    # 当前目录
    cands.append(os.path.join(cwd, *_DEFAULT_REL))
    # 当前目录的上一级
    cands.append(os.path.join(os.path.dirname(cwd), *_DEFAULT_REL))
    # 常见盘符根目录
    for drive in ("D:", "C:", "E:"):
        cands.append(os.path.join(drive + os.sep, *_DEFAULT_REL))
    # 用户主目录
    home = os.path.expanduser("~")
    cands.append(os.path.join(home, *_DEFAULT_REL))
    return cands


def resolve_download_dir(explicit: Optional[str] = None, cwd: Optional[str] = None) -> str:
    """解析下载目录。

    - explicit 给定 → 记住并返回
    - 已记住 → 返回
    - 扫描默认位置找到 → 记住并返回
    - 否则 → RuntimeError
    """
    if explicit:
        return save_download_dir(explicit)

    saved = get_saved_download_dir()
    if saved:
        return saved

    for cand in scan_default_candidates(cwd):
        if os.path.isdir(cand):
            return save_download_dir(cand)

    raise RuntimeError(
        "未找到默认下载目录 'go music/data/downloads'。"
        "请用 --dir <路径> 指定下载位置（指定后会记住，下次默认使用）。"
    )


def forget_download_dir() -> None:
    """清除记住的下载目录（测试/重置用）。"""
    _save({"download_dir": None} if False else {})
