"""html_parse.py — 解析 go-music-dl 后端返回的 SSR HTML 页面。

搜索 / 歌单 / 专辑接口返回的是服务端渲染 HTML。歌曲以
`<li class="song-card" data-id=... data-extra='{...}'>` 形式嵌入。
这里用标准库正则提取数据，无第三方依赖。
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List, Optional

LI_RE = re.compile(
    r'<li\s+class="song-card"[^>]*data-id="(?P<id>[^"]*)"[^>]*data-source="(?P<source>[^"]*)"'
    r'(?:[^>]*data-album="(?P<album>[^"]*)")?[^>]*data-duration="(?P<duration>[^"]*)"'
    r'[^>]*data-name="(?P<name>[^"]*)"[^>]*data-artist="(?P<artist>[^"]*)"'
    r'(?:[^>]*data-cover="(?P<cover>[^"]*)")?[^>]*data-extra=\'(?P<extra>[^\']*)\'',
    re.DOTALL,
)

FALLBACK_LI_RE = re.compile(
    r'<li\s+class="song-card".*?data-id="([^"]*)"', re.DOTALL
)

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)


def _unescape(s: str) -> str:
    return html.unescape(s or "")


def parse_songs(html_text: str) -> List[Dict[str, Any]]:
    """从搜索/歌单/专辑页面提取歌曲列表。"""
    songs: List[Dict[str, Any]] = []
    for m in LI_RE.finditer(html_text):
        extra_raw = _unescape(m.group("extra"))
        extra: Dict[str, Any] = {}
        if extra_raw:
            try:
                parsed = json.loads(extra_raw)
                if isinstance(parsed, dict):
                    extra = parsed
            except json.JSONDecodeError:
                extra = {}
        songs.append(
            {
                "id": _unescape(m.group("id")),
                "source": _unescape(m.group("source")),
                "name": _unescape(m.group("name")),
                "artist": _unescape(m.group("artist")),
                "album": _unescape(m.group("album") or ""),
                "duration": _unescape(m.group("duration")),
                "cover": _unescape(m.group("cover") or ""),
                "extra": extra,
            }
        )
    return songs


def parse_playlists(html_text: str) -> List[Dict[str, Any]]:
    """从歌单网格页面提取歌单列表（playlist-grid partial）。"""
    out: List[Dict[str, Any]] = []
    # 歌单卡片通常以 <a ... class="playlist-card"... href=".../playlist?id=..." 形式出现
    cards = re.findall(
        r'<a[^>]*class="[^"]*playlist-card[^"]*"[^>]*href="(?P<href>[^"]*)"[^>]*>.*?'
        r'<[^>]*playlist-title[^>]*>(?P<title>.*?)</.*?>.*?'
        r'(?:<[^>]*playlist-count[^>]*>(?P<count>.*?)</)?',
        html_text,
        re.DOTALL,
    )
    for href, title, count in cards:
        id_match = re.search(r"(?:id|playlist)=([^&\"']+)", href)
        out.append(
            {
                "id": id_match.group(1) if id_match else "",
                "title": _unescape(title).strip(),
                "count": _unescape(count).strip() if count else "",
                "link": _unescape(href),
            }
        )
    return out


def parse_count(html_text: str) -> int:
    """从页面标题或结果区域估算结果数量。"""
    title = TITLE_RE.search(html_text)
    if not title:
        return 0
    m = re.search(r"共\s*(\d+)\s*个|(\d+)\s*results|搜索到\s*(\d+)", title.group(1))
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return len(parse_songs(html_text))


def search_results(
    html_text: str,
    search_type: str = "song",
) -> Dict[str, Any]:
    """统一入口：从搜索页面提取结构化结果。"""
    if search_type in ("song", "local_music"):
        return {"type": "song", "songs": parse_songs(html_text), "count": len(parse_songs(html_text))}
    if search_type == "album":
        return {"type": "album", "playlists": parse_playlists(html_text), "count": len(parse_playlists(html_text))}
    return {"type": "playlist", "playlists": parse_playlists(html_text), "count": len(parse_playlists(html_text))}


def song_to_query_params(song: Dict[str, Any]) -> Dict[str, Any]:
    """将 Song 转为下载/歌词接口的 query 参数。"""
    extra = song.get("extra") or {}
    return {
        "id": song.get("id", ""),
        "source": song.get("source", ""),
        "name": song.get("name", "Unknown"),
        "artist": song.get("artist", "Unknown"),
        "album": song.get("album", "") or extra.get("album", ""),
        "cover": song.get("cover", "") or extra.get("cover", ""),
        "duration": song.get("duration", ""),
        "extra": extra,
    }
