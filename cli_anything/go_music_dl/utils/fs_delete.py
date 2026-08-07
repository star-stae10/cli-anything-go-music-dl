"""fs_delete.py — 直接删除本地下载文件（文件系统操作）。

注意：这只删除磁盘文件，不进软件的下载记录。删除动作不可撤销，
调用方（CLI）必须提供显式的 --yes 确认。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

_DANGEROUS = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")
_AUDIO_EXT = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aac", ".ape", ".opus", ".wma"}
_DOWNLOAD_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".lrc", ".jpg", ".jpeg", ".png", ".ape", ".opus"}


def _is_audio(fn: str) -> bool:
    return os.path.splitext(fn)[1].lower() in _AUDIO_EXT


def _is_download_artifact(fn: str) -> bool:
    return os.path.splitext(fn)[1].lower() in _DOWNLOAD_EXTS


def safe_join(directory: str, filename: str) -> str:
    """安全拼接下载目录与文件名，防止路径穿越。"""
    directory = os.path.abspath(directory)
    if os.path.isabs(filename) or ".." in filename:
        raise ValueError(f"非法文件名（不允许绝对路径或 ..）: {filename}")
    filename = filename.replace("/", "\\")
    # 去掉路径分隔符与危险字符，只保留文件名
    base = os.path.basename(filename)
    base = _DANGEROUS.sub("", base)
    if not base:
        raise ValueError("非法文件名")
    return os.path.join(directory, base)


def list_downloads(directory: str) -> List[str]:
    """列出下载目录中的音频/附属文件（绝对路径）。"""
    out = []
    if not os.path.isdir(directory):
        return out
    for fn in sorted(os.listdir(directory)):
        if _is_download_artifact(fn):
            out.append(os.path.join(directory, fn))
    return out


def _split_song_filename(fn: str) -> "tuple[str, str]":
    """把 '歌手 - 歌名.ext' 拆成 (artist, title)。"""
    base = fn
    for ext in _DOWNLOAD_EXTS:
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
            break
    if " - " in base:
        artist, _, title = base.rpartition(" - ")
        return artist.strip(), title.strip()
    return "", base.strip()


def find_by_name(directory: str, name: str, artist: str = "") -> List[str]:
    """按歌名/歌手查找下载文件。

    匹配规则：
    - 给 artist 时：要求文件名中的"歌手字段"与 artist 精确相等（而不是子串包含），
      避免 '黄诗扶' 误匹配 '恋恋故人难、黄诗扶、王敬轩（妖扬）'
    - 给 name 时：歌名字段模糊包含即可
    - 都不给：返回目录下全部音频文件
    """
    directory = os.path.abspath(directory)
    matches = []
    for fn in sorted(os.listdir(directory)):
        if not _is_download_artifact(fn):
            continue
        file_artist, file_title = _split_song_filename(fn)
        if artist:
            if file_artist != artist:
                continue
        if name:
            if name not in file_title:
                continue
        if not artist and not name:
            matches.append(os.path.join(directory, fn))
            continue
        matches.append(os.path.join(directory, fn))
    return matches


def delete_files(paths: List[str]) -> Dict[str, object]:
    """删除一批文件。返回每文件的处理结果。"""
    results: List[Dict[str, object]] = []
    for p in paths:
        ap = os.path.abspath(p)
        if not os.path.isfile(ap):
            results.append({"path": p, "deleted": False, "reason": "not-found"})
            continue
        try:
            os.remove(ap)
            results.append({"path": p, "deleted": True, "size": os.path.getsize(ap) if os.path.exists(ap) else 0})
        except OSError as e:
            results.append({"path": p, "deleted": False, "reason": str(e)})
    return {"files": results, "deleted": sum(1 for r in results if r["deleted"]), "total": len(results)}
