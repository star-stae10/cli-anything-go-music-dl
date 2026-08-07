"""song.py — 歌曲搜索、探测、详情命令的核心逻辑。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient
from cli_anything.go_music_dl.utils.html_parse import parse_songs, search_results


def search(
    client: BackendClient,
    keyword: str,
    search_type: str = "song",
    sources: Optional[List[str]] = None,
    exact_artist: str = "",
) -> Dict[str, Any]:
    if search_type not in ("song", "playlist", "album"):
        raise ValueError(f"不支持的搜索类型: {search_type}")
    html_text = client.search_page(keyword, search_type, sources, exact_artist)
    return search_results(html_text, search_type)


def inspect(
    client: BackendClient,
    song_id: str,
    source: str,
    extra: Optional[dict] = None,
) -> Dict[str, Any]:
    return client.inspect(song_id, source, extra)


def find_song(
    client: BackendClient, keyword: str, index: int = 0
) -> Dict[str, Any]:
    """按关键词搜索并返回指定索引的歌曲（默认第一条）。"""
    result = search(client, keyword, "song")
    songs = result.get("songs", [])
    if not songs:
        raise ValueError(f"未找到歌曲: {keyword}")
    if index >= len(songs) or index < 0:
        raise ValueError(f"索引越界: {index}，共 {len(songs)} 首")
    return songs[index]


def download_song(
    client: BackendClient,
    song: Dict[str, Any],
    save_local: bool = True,
    out_path: Optional[str] = None,
) -> Dict[str, Any]:
    return client.download_song(
        song_id=song["id"],
        source=song["source"],
        name=song.get("name", "Unknown"),
        artist=song.get("artist", "Unknown"),
        album=song.get("album", ""),
        cover=song.get("cover", ""),
        extra=song.get("extra"),
        save_local=save_local,
        out_path=out_path,
    )


def download_lyrics(
    client: BackendClient,
    song: Dict[str, Any],
    out_path: Optional[str] = None,
) -> Dict[str, Any]:
    return client.download_lrc(
        song_id=song["id"],
        source=song["source"],
        name=song.get("name", "Unknown"),
        artist=song.get("artist", "Unknown"),
        album=song.get("album", ""),
        duration=str(song.get("duration", "")),
        extra=song.get("extra"),
        out_path=out_path,
    )


def download_cover(
    client: BackendClient,
    song: Dict[str, Any],
    out_path: Optional[str] = None,
) -> Dict[str, Any]:
    url = song.get("cover") or (song.get("extra") or {}).get("cover", "")
    if not url:
        raise ValueError(f"歌曲 {song.get('name', '')} 没有封面地址")
    return client.download_cover(
        url,
        name=song.get("name", "cover"),
        artist=song.get("artist", ""),
        out_path=out_path,
    )
