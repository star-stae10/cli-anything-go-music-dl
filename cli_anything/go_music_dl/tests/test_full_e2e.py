"""test_full_e2e.py — E2E 测试：调用真实 go-music-dl 后端，产生真实下载文件。

依赖：本机已运行 go-music-dl 桌面版/Web 版（自动探测 127.0.0.1）。
不降级：后端不可用时测试失败并给出明确提示。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

from cli_anything.go_music_dl.utils.go_music_dl_backend import (
    BackendClient,
    resolve_base_url,
)
from cli_anything.go_music_dl.utils.html_parse import parse_songs


def _retry(fn, tries=3, delay=2.0, exc=Exception, check=None):
    """网络偶发失败重试。check 为可选校验函数，返回 False 时重试。"""
    last = None
    for i in range(tries):
        try:
            result = fn()
            if check is None or check(result):
                return result
            last = RuntimeError("check 校验未通过")
        except exc as e:  # noqa: BLE001
            last = e
        if i < tries - 1:
            print(f"\n  [retry {i + 1}] {last}")
            time.sleep(delay)
    raise last if isinstance(last, Exception) else RuntimeError(last)

SEARCH_KEYWORD = os.environ.get("GMDL_TEST_KEYWORD", "周杰伦")
SOURCES = os.environ.get("GMDL_TEST_SOURCES", "netease")
FALLBACK_SOURCES = ["kugou", "kuwo", "qq"]
# 下载类测试优先使用已验证稳定的源（kuwo 实测最稳），避免平台限流
DOWNLOAD_SOURCES = ["kuwo", "netease", "kugou"]


def _require_backend():
    try:
        base = resolve_base_url()
    except RuntimeError as e:
        pytest.fail(f"后端不可用，E2E 无法执行（不降级）: {e}")
    return base


def _find_song(client, keyword, sources):
    """尝试多个源搜索，返回 (song, source_used)。"""
    for src in list(sources) + [s for s in FALLBACK_SOURCES if s not in sources]:
        html = client.search_page(keyword, "song", [src])
        songs = parse_songs(html)
        if songs:
            print(f"[source: {src}]")
            return songs[0], src
    return None, None


@pytest.fixture(scope="module")
def backend_client():
    base = _require_backend()
    return BackendClient(base)


def _resolve_cli(name):
    """解析已安装 CLI；未安装时回退 python -m（开发模式）。"""
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.go_music_dl.go_music_dl_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


@pytest.fixture(scope="module")
def tmp_dir():
    d = tempfile.mkdtemp(prefix="gmdl-e2e-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def sample_song(backend_client):
    """搜索并返回一首真实歌曲（优先稳定源，用于下载类测试）。"""
    song_obj, src = _find_song(backend_client, SEARCH_KEYWORD, DOWNLOAD_SOURCES)
    assert song_obj, f"搜索 '{SEARCH_KEYWORD}' 无结果，可能网络或平台授权受限"
    return song_obj, src


# ---------------- 真实后端 API 测试 ----------------

def test_server_health(backend_client):
    health = backend_client.health()
    assert health.get("app") == "go-music-dl"
    assert health.get("status") == "ok"


def test_settings_read(backend_client):
    st = backend_client.get_settings()
    assert "downloadDir" in st
    assert "downloadConcurrency" in st


def test_search_returns_songs(backend_client):
    song_obj, src = _retry(
        lambda: _find_song(backend_client, SEARCH_KEYWORD, [SOURCES]),
        check=lambda r: r[0] is not None,
    )
    assert song_obj, "搜索无结果"
    for field in ("id", "source", "name", "artist"):
        assert song_obj.get(field), f"字段缺失: {field}"
    print(f"\n  搜索结果: {song_obj['artist']} - {song_obj['name']} [{song_obj['source']}] {song_obj['id']}")


def test_inspect_valid(sample_song):
    song_obj, src = sample_song
    client = BackendClient(_require_backend())
    result = _retry(
        lambda: client.inspect(song_obj["id"], song_obj["source"], song_obj.get("extra")),
        check=lambda r: r.get("valid") is True,
    )
    assert result.get("valid") is True, f"inspect 无效: {result}"
    assert result.get("url"), "下载 URL 为空"
    print(f"\n  inspect: {result['size']} {result['bitrate']}")


def test_real_download_save_local(sample_song, tmp_dir):
    song_obj, src = sample_song
    client = BackendClient(_require_backend())

    def _do_download():
        return client.download_song(
            song_id=song_obj["id"],
            source=song_obj["source"],
            name=song_obj.get("name", "Unknown"),
            artist=song_obj.get("artist", "Unknown"),
            album=song_obj.get("album", ""),
            cover=song_obj.get("cover", ""),
            extra=song_obj.get("extra"),
            save_local=True,
        )

    result = _retry(_do_download, exc=Exception)
    assert result.get("saved") is True, f"下载失败: {result}"
    if result.get("skipped"):
        # 后端去重跳过：说明该歌此前已下载（正确行为）
        assert result.get("filename"), "去重场景缺少文件名"
        print(f"\n  已存在（去重跳过）: {result.get('filename')}")
    else:
        path = result.get("path")
        assert path, "无保存路径"
        print(f"\n  已保存 (后端相对路径): {path}")


def test_real_download_stream(sample_song, tmp_dir):
    song_obj, src = sample_song
    client = BackendClient(_require_backend())
    out = os.path.join(tmp_dir, "stream_download.mp3")

    def _do_download():
        return client.download_song(
            song_id=song_obj["id"],
            source=song_obj["source"],
            name=song_obj.get("name", "Unknown"),
            artist=song_obj.get("artist", "Unknown"),
            save_local=False,
            out_path=out,
        )

    def _check(r):
        return r.get("saved") is True and os.path.exists(out) and os.path.getsize(out) > 1000

    result = _retry(_do_download, exc=Exception, check=_check)
    assert result.get("saved") is True
    assert os.path.exists(out), "流式下载文件不存在"
    size = os.path.getsize(out)
    assert size > 1000, f"文件过小: {size}"
    with open(out, "rb") as f:
        magic = f.read(3)
    assert magic in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xe3"), f"非音频文件头: {magic}"
    print(f"\n  流式下载: {out} ({size:,} bytes)")


# ---------------- CLI 子进程测试 ----------------

class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-go-music-dl")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            encoding="utf-8",
            errors="replace",
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "search" in result.stdout
        assert "download" in result.stdout

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "cli-anything-go-music-dl" in result.stdout

    def test_server_json(self):
        result = self._run(["--json", "server"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert "base_url" in data["data"]

    def test_search_json(self, tmp_dir):
        client = BackendClient(_require_backend())
        song_obj, src = _retry(
            lambda: _find_song(client, SEARCH_KEYWORD, [SOURCES]),
            check=lambda r: r[0] is not None,
        )
        assert song_obj, "搜索无结果"
        result = self._run(["--json", "search", SEARCH_KEYWORD, "--sources", src, "--limit", "3"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert len(data["data"]["items"]) > 0

    def test_full_workflow(self, tmp_dir):
        """完整工作流：server → search → inspect → 流式下载 → 验证输出文件。"""
        r_server = self._run(["--json", "server"])
        assert r_server.returncode == 0
        server_data = json.loads(r_server.stdout)
        assert server_data["ok"] is True

        client = BackendClient(_require_backend())
        song_obj, src = _retry(
            lambda: _find_song(client, SEARCH_KEYWORD, DOWNLOAD_SOURCES),
            check=lambda r: r[0] is not None,
        )
        assert song_obj, "搜索结果为空"

        r_inspect = _retry(
            lambda: self._run(["--json", "inspect", song_obj["id"], song_obj["source"]]),
            check=lambda r: r.returncode == 0
            and json.loads(r.stdout).get("ok") is True
            and json.loads(r.stdout)["data"].get("valid") is True,
        )
        inspect_data = json.loads(r_inspect.stdout)
        assert inspect_data["data"].get("valid") is True

        r_dl = _retry(
            lambda: self._run(
                [
                    "--json", "download",
                    "--id", song_obj["id"], "--source", song_obj["source"],
                    "--name", song_obj["name"], "--artist", song_obj["artist"],
                    "--stream", "--dir", tmp_dir,
                ]
            ),
            check=lambda r: r.returncode == 0
            and json.loads(r.stdout).get("ok") is True
            and os.path.exists(json.loads(r.stdout)["data"].get("path", ""))
            and os.path.getsize(json.loads(r.stdout)["data"]["path"]) > 1000,
        )
        assert r_dl.returncode == 0, f"下载失败: {r_dl.stdout} {r_dl.stderr}"
        dl_data = json.loads(r_dl.stdout)
        assert dl_data["ok"] is True
        path = dl_data["data"].get("path", "")
        assert path and os.path.exists(path), f"下载文件不存在: {path}"
        assert os.path.getsize(path) > 1000
        print(f"\n  CLI 工作流产物: {path} ({os.path.getsize(path):,} bytes)")
