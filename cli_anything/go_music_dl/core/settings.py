"""settings.py — 配置与设置命令的核心逻辑。"""

from __future__ import annotations

from typing import Any, Dict, List

from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient


def get_settings(client: BackendClient) -> Dict[str, Any]:
    return client.get_settings()


def update_settings(client: BackendClient, updates: Dict[str, Any]) -> Dict[str, Any]:
    current = client.get_settings()
    unknown = [k for k in updates if k not in current]
    if unknown:
        raise ValueError(f"未知设置项: {', '.join(unknown)}")
    merged = {**current, **updates}
    return client.post_settings(merged)


def get_cookies(client: BackendClient) -> Dict[str, str]:
    return client.get_cookies()


def set_cookies(client: BackendClient, cookies: Dict[str, str]) -> Dict[str, Any]:
    current = client.get_cookies()
    merged = {**current, **cookies}
    return client.post_cookies(merged)


def available_sources(client: BackendClient) -> List[str]:
    """从设置或已知源列表返回可用音乐源。"""
    settings = client.get_settings()
    # 部分版本 settings 不直接列出源；返回常见源以便校验。
    known = [
        "netease", "qq", "kugou", "kuwo", "migu",
        "qianqian", "soda", "fivesing", "jamendo", "joox", "bilibili",
    ]
    return known
