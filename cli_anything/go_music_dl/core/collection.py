"""collection.py — 本地歌单 / 本地音乐命令的核心逻辑。"""

from __future__ import annotations

from typing import Any, Dict, List

from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient


def my_collections(client: BackendClient) -> List[Dict[str, Any]]:
    return client.my_collections()


def local_music_page(
    client: BackendClient, page: int = 1, page_size: int = 200, keyword: str = ""
) -> Dict[str, Any]:
    return client.local_music_page(page=page, page_size=page_size, keyword=keyword)


def local_music_list(client: BackendClient) -> List[Dict[str, Any]]:
    return client.local_music_list()
