"""project.py — 后端服务实例管理（server 命令）核心逻辑。"""

from __future__ import annotations

from typing import Any, Dict

from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient, resolve_base_url


def discover(server: str = "", host: str = "127.0.0.1") -> Dict[str, Any]:
    """探测并连接后端服务。"""
    base = resolve_base_url(server, host=host)
    client = BackendClient(base)
    health = client.health()
    settings = client.get_settings()
    return {
        "base_url": base,
        "app": health.get("app", "go-music-dl"),
        "status": health.get("status", "ok"),
        "download_dir": settings.get("downloadDir", "data/downloads"),
        "download_to_local": settings.get("downloadToLocal", False),
    }
