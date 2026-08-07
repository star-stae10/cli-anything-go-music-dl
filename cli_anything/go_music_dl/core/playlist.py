"""playlist.py — 歌单 / 专辑 详情命令的核心逻辑。"""

from __future__ import annotations

from typing import Any, Dict, List

from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient
from cli_anything.go_music_dl.utils.html_parse import parse_songs


def playlist_detail(
    client: BackendClient, playlist_id: str, source: str, link: str = ""
) -> Dict[str, Any]:
    html_text = client.playlist_page(playlist_id, source, link)
    return {"type": "playlist", "id": playlist_id, "source": source, "songs": parse_songs(html_text)}


def album_detail(
    client: BackendClient, album_id: str, source: str
) -> Dict[str, Any]:
    html_text = client.album_page(album_id, source)
    return {"type": "album", "id": album_id, "source": source, "songs": parse_songs(html_text)}


def parse_link(client: BackendClient, url: str) -> Dict[str, Any]:
    """解析歌单/专辑/单曲链接：走后端 /search 接口（关键词以 http 开头自动解析）。"""
    html_text = client.search_page(url, "song")
    return {"type": "parsed", "url": url, "songs": parse_songs(html_text)}
