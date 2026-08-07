"""backend.py — 调用真实 go-music-dl 软件的 HTTP API。

这是 CLI 与真实软件之间的唯一桥梁。所有命令最终都通过它访问
桌面版 / Web 版软件暴露的 Gin HTTP 接口，绝不重实现搜索/下载逻辑。

桌面版默认监听 127.0.0.1:<port>，内嵌 Web 服务路由前缀为 /music。
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

import requests

DEFAULT_PREFIX = "/music"
# 桌面 GUI 常见端口，按优先级探测（含已知实例端口 37777）
PROBE_PORTS = [18901, 37777, 8080, 8081, 8082, 9090]
PROBE_TIMEOUT = 0.8


def _is_port_open(host: str, port: int, timeout: float = PROBE_TIMEOUT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def find_desktop_server(
    host: str = "127.0.0.1",
    ports: Optional[List[int]] = None,
    prefix: str = DEFAULT_PREFIX,
) -> Optional[str]:
    """探测本机正在运行的 go-music-dl 服务，返回 base URL 或 None。"""
    candidates = ports or PROBE_PORTS
    for port in candidates:
        base = f"http://{host}:{port}{prefix}"
        if _is_port_open(host, port):
            try:
                r = requests.get(f"{base}/healthz", timeout=2.5)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    return base
            except (requests.RequestException, ValueError):
                continue
    return None


def resolve_base_url(server: Optional[str] = None, host: str = "127.0.0.1") -> str:
    """解析 base URL；未指定时自动探测桌面版/Web 版。

    传入的 server 若不含 /music 路由前缀，自动补全（桌面/Web 版 API 均挂载
    在 /music 下）。找不到时抛出 RuntimeError，给出明确的启动指引（不降级）。
    """
    if server:
        base = server.rstrip("/")
        if not base.startswith("http"):
            base = f"http://{base}"
        if DEFAULT_PREFIX not in base:
            base += DEFAULT_PREFIX
        return base
    found = find_desktop_server(host=host)
    if found:
        return found
    # 尝试启动桌面版：优先用已记住的 exe 路径，其次 PATH
    exe = None
    from cli_anything.go_music_dl.utils.dir_config import get_saved_exe_path

    saved_exe = get_saved_exe_path()
    if saved_exe:
        exe = saved_exe
    else:
        exe = shutil.which("music-dl-desktop-go")
    if not exe:
        raise RuntimeError(
            "找不到 go-music-dl 后端服务，且不知道软件 exe 位置。"
            "请先启动桌面应用 (music-dl-desktop-go.exe)，"
            "或用 --server http://127.0.0.1:8080 指定后端地址，"
            "或用 `server --exe <exe路径>` 告诉 CLI 软件位置（会记住）。"
        )
    # 启动桌面版（Windows，后台无窗口）
    try:
        if exe.lower().endswith(".exe"):
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:  # 非 exe（如 .sh / 命令）直接执行
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
    for _ in range(40):
        found = find_desktop_server(host=host)
        if found:
            return found
        time.sleep(0.5)
    raise RuntimeError(
        "已尝试启动 go-music-dl 但未检测到服务。请手动启动桌面应用后重试。"
    )


def get_download_dir(base_url: str) -> str:
    """从后端设置读取下载目录。"""
    st = get_settings(base_url)
    return st.get("downloadDir") or "data/downloads"


class BackendClient:
    """真实软件的 HTTP 客户端。"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "cli-anything-go-music-dl/1.0"})

    # ---- 基础 ----

    def health(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/healthz", timeout=5)
        r.raise_for_status()
        return r.json()

    def get_settings(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/settings", timeout=10)
        r.raise_for_status()
        return r.json()

    def post_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        r = self.session.post(f"{self.base_url}/settings", json=settings, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_cookies(self) -> Dict[str, str]:
        r = self.session.get(f"{self.base_url}/cookies", timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {}

    def post_cookies(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        r = self.session.post(f"{self.base_url}/cookies", json=cookies, timeout=15)
        r.raise_for_status()
        return r.json()

    # ---- 搜索 / 探测 ----

    def search_page(
        self,
        keyword: str,
        search_type: str = "song",
        sources: Optional[List[str]] = None,
        exact_artist: str = "",
    ) -> str:
        """搜索并返回 SSR HTML 页面（供 html_parse 提取）。"""
        params: Dict[str, Any] = {"q": keyword, "type": search_type}
        if sources:
            params["sources"] = sources
        if exact_artist:
            params["exact_artist"] = exact_artist
        r = self.session.get(f"{self.base_url}/search", params=params, timeout=60)
        r.raise_for_status()
        return r.text

    def inspect(self, song_id: str, source: str, extra: Optional[dict] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"id": song_id, "source": source}
        if extra:
            import json

            params["extra"] = json.dumps(extra, ensure_ascii=False)
        r = self.session.get(f"{self.base_url}/inspect", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def playlist_page(self, playlist_id: str, source: str, link: str = "") -> str:
        params: Dict[str, Any] = {"id": playlist_id, "source": source}
        if link:
            params["link"] = link
        r = self.session.get(f"{self.base_url}/playlist", params=params, timeout=60)
        r.raise_for_status()
        return r.text

    def album_page(self, album_id: str, source: str) -> str:
        r = self.session.get(
            f"{self.base_url}/album", params={"id": album_id, "source": source}, timeout=60
        )
        r.raise_for_status()
        return r.text

    # ---- 下载 ----

    def download_song(
        self,
        song_id: str,
        source: str,
        name: str = "Unknown",
        artist: str = "Unknown",
        album: str = "",
        cover: str = "",
        extra: Optional[dict] = None,
        save_local: bool = True,
        out_path: Optional[str] = None,
        embed: bool = True,
    ) -> Dict[str, Any]:
        """下载歌曲。

        save_local=True 时交给软件保存（去重/元数据/文件名模板），返回 JSON。
        save_local=False 时流式下载到 out_path（默认 cwd），返回文件信息。
        """
        params: Dict[str, Any] = {
            "id": song_id,
            "source": source,
            "name": name,
            "artist": artist,
            "album": album,
            "cover": cover,
            "save_local": "1" if save_local else "",
            "embed": "1" if (embed and not save_local) else "",
        }
        if extra:
            import json

            params["extra"] = json.dumps(extra, ensure_ascii=False)
        if save_local:
            # 后端要求 save_local 走 POST + X-Requested-With 同源头
            headers = {"X-Requested-With": "XMLHttpRequest"}
            r = self.session.post(
                f"{self.base_url}/download", params=params, headers=headers, timeout=180
            )
            r.raise_for_status()
            return r.json()
        r = self.session.get(f"{self.base_url}/download", params=params, timeout=120, stream=True)
        r.raise_for_status()
        target = out_path or os.path.join(os.getcwd(), _suggest_filename(name, artist))
        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
        return {
            "saved": True,
            "path": os.path.abspath(target),
            "size": os.path.getsize(target),
            "content_type": r.headers.get("Content-Type", ""),
        }

    def download_lrc(
        self,
        song_id: str,
        source: str,
        name: str = "Unknown",
        artist: str = "Unknown",
        album: str = "",
        duration: str = "",
        extra: Optional[dict] = None,
        out_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "id": song_id,
            "source": source,
            "name": name,
            "artist": artist,
            "album": album,
            "duration": duration,
        }
        if extra:
            import json

            params["extra"] = json.dumps(extra, ensure_ascii=False)
        r = self.session.get(f"{self.base_url}/download_lrc", params=params, timeout=60)
        if r.status_code == 404:
            return {"found": False, "path": None}
        r.raise_for_status()
        target = out_path or os.path.join(os.getcwd(), f"{name} - {artist}.lrc")
        with open(target, "w", encoding="utf-8") as f:
            f.write(r.text)
        return {"found": True, "path": os.path.abspath(target), "bytes": len(r.text.encode("utf-8"))}

    def download_cover(
        self,
        url: str,
        name: str = "cover",
        artist: str = "",
        out_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {"url": url, "name": name, "artist": artist}
        r = self.session.get(f"{self.base_url}/download_cover", params=params, timeout=60, stream=True)
        if r.status_code != 200 or not r.content:
            return {"found": False, "path": None}
        target = out_path or os.path.join(os.getcwd(), f"{name} - {artist}.jpg")
        with open(target, "wb") as f:
            f.write(r.content)
        return {"found": True, "path": os.path.abspath(target), "size": len(r.content)}

    # ---- 记录 / 本地 ----

    def download_records(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/api/downloads/records",
            params={"page": page, "page_size": page_size},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def clear_download_records(self) -> Dict[str, Any]:
        r = self.session.delete(f"{self.base_url}/api/downloads/records", timeout=15)
        r.raise_for_status()
        return r.json()

    def local_music_page(self, page: int = 1, page_size: int = 200, keyword: str = "") -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if keyword:
            params["keyword"] = keyword
        r = self.session.get(f"{self.base_url}/local_music_page", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def local_music_list(self) -> List[Dict[str, Any]]:
        r = self.session.get(f"{self.base_url}/local_music", timeout=30)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else data.get("items", [])

    def my_collections(self) -> List[Dict[str, Any]]:
        r = self.session.get(f"{self.base_url}/my_collections", timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("collections", [])

    # ---- 删除 ----

    def delete_local_music(self, track_id: str) -> Dict[str, Any]:
        """硬删除一首本地音乐（磁盘文件 + 索引行）。"""
        r = self.session.delete(
            f"{self.base_url}/local_music", params={"id": track_id}, timeout=30
        )
        r.raise_for_status()
        return r.json()

    def delete_collection(self, collection_id: str) -> Dict[str, Any]:
        """删除一个本地歌单。"""
        r = self.session.delete(
            f"{self.base_url}/collections/{collection_id}", timeout=30
        )
        r.raise_for_status()
        return r.json()

    def delete_collection_song(
        self, collection_id: str, song_id: str, source: str
    ) -> Dict[str, Any]:
        """从本地歌单中移除一首歌。"""
        r = self.session.delete(
            f"{self.base_url}/collections/{collection_id}/songs",
            params={"id": song_id, "source": source},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


def _suggest_filename(name: str, artist: str) -> str:
    safe_name = "".join(c for c in name if c not in '<>:"/\\|?*').strip() or "song"
    safe_artist = "".join(c for c in artist if c not in '<>:"/\\|?*').strip() or "unknown"
    return f"{safe_artist} - {safe_name}.mp3"
