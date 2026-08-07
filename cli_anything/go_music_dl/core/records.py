"""records.py — 下载记录查询/清除的核心逻辑。"""

from __future__ import annotations

from typing import Any, Dict

from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient


def list_records(
    client: BackendClient, page: int = 1, page_size: int = 20
) -> Dict[str, Any]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    return client.download_records(page=page, page_size=page_size)


def clear_records(client: BackendClient) -> Dict[str, Any]:
    return client.clear_download_records()
