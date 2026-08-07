"""delete.py — 删除歌曲 / 歌单 / 下载文件的核心逻辑。"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from cli_anything.go_music_dl.utils.fs_delete import delete_files, find_by_name, list_downloads
from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient


def delete_local_music(client: BackendClient, track_id: str) -> Dict[str, Any]:
    """经后端 API 删除一首本地音乐（硬删磁盘 + 索引）。"""
    return client.delete_local_music(track_id)


def delete_collection(client: BackendClient, collection_id: str) -> Dict[str, Any]:
    """经后端 API 删除一个本地歌单。"""
    return client.delete_collection(collection_id)


def delete_collection_song(
    client: BackendClient, collection_id: str, song_id: str, source: str
) -> Dict[str, Any]:
    """经后端 API 从歌单移除一首歌。"""
    return client.delete_collection_song(collection_id, song_id, source)


def list_local_downloads(download_dir: str) -> List[str]:
    """列出下载目录中的音频文件。"""
    return list_downloads(download_dir)


def delete_download_files(
    download_dir: str, name: str = "", artist: str = "", paths: List[str] = None
) -> Dict[str, Any]:
    """直接删除下载目录中的文件（文件系统操作）。

    - 给 paths 则直接删这些路径
    - 给 name/artist 则按名称匹配
    - 都不给则列全部并提示
    """
    if paths:
        targets = [os.path.abspath(p) for p in paths]
    elif name or artist:
        targets = find_by_name(download_dir, name, artist)
    else:
        targets = []
    if not targets:
        return {"deleted": 0, "total": 0, "files": [], "matched": len(list_downloads(download_dir))}
    return delete_files(targets)
