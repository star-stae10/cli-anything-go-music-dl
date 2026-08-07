"""go_music_dl_cli.py — go-music-dl 的 Click CLI 入口 + REPL。

用法示例：
  cli-anything-go-music-dl --server http://127.0.0.1:18901 search "周杰伦" --json
  cli-anything-go-music-dl download --keyword "周杰伦" --index 0 --dir ./out
  cli-anything-go-music-dl                      # 进入 REPL
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from typing import Any, Dict, Optional

import click

from cli_anything.go_music_dl import __version__
from cli_anything.go_music_dl.core import collection, playlist, project, settings as settings_mod, song
from cli_anything.go_music_dl.core import delete as delete_mod
from cli_anything.go_music_dl.core import records as records_mod
from cli_anything.go_music_dl.utils.dir_config import resolve_download_dir
from cli_anything.go_music_dl.utils.go_music_dl_backend import BackendClient, resolve_base_url
from cli_anything.go_music_dl.utils.repl_skin import ReplSkin


def _echo(data: Any, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(data)


def _err(msg: str, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    else:
        click.echo(f"错误: {msg}", err=True)


def _make_client(server: str) -> BackendClient:
    base = resolve_base_url(server)
    return BackendClient(base)


@click.group(invoke_without_command=True)
@click.option("--server", "-s", default="", help="go-music-dl 后端 base URL（默认自动探测）")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
@click.option("--version", "show_version", is_flag=True, help="显示版本")
@click.pass_context
def cli(ctx: click.Context, server: str, as_json: bool, show_version: bool) -> None:
    """go-music-dl 聚合音乐搜索下载 CLI（操作真实软件后端）。"""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    ctx.obj["json"] = as_json
    if show_version:
        click.echo(f"cli-anything-go-music-dl v{__version__}")
        ctx.exit(0)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ---------------- server ----------------

@cli.command()
@click.option("--server", "-s", default=None, help="后端 URL（缺省用全局 --server）")
@click.option("--exe", "exe_path", default=None, help="软件 exe 路径（记住后下次自动启动）")
@click.pass_context
def server(ctx: click.Context, server: str, exe_path: str) -> None:
    """探测后端；可指定/记住软件 exe 路径以便自动启动。"""
    as_json = ctx.obj["json"]
    try:
        if exe_path:
            from cli_anything.go_music_dl.utils.dir_config import save_exe_path

            saved = save_exe_path(exe_path)
            if not as_json:
                _echo(f"  已记住软件 exe: {saved}", False)
        effective = server if server else ctx.obj.get("server", "")
        info = project.discover(effective)
        if as_json:
            _echo({"ok": True, "data": info}, True)
        else:
            _echo(f"  应用: {info['app']} ({info['status']})", False)
            _echo(f"  Base URL: {info['base_url']}", False)
            _echo(f"  下载目录: {info['download_dir']}", False)
    except RuntimeError as e:
        _err(str(e), as_json)


# ---------------- search ----------------

@cli.command()
@click.argument("keyword")
@click.option("--type", "search_type", type=click.Choice(["song", "playlist", "album"]), default="song")
@click.option("--sources", default="", help="逗号分隔的音乐源，如 netease,qq")
@click.option("--exact-artist", default="", help="精确匹配歌手")
@click.option("--limit", type=int, default=20, help="限制输出条数")
@click.pass_context
def search(ctx: click.Context, keyword: str, search_type: str, sources: str, exact_artist: str, limit: int) -> None:
    """搜索歌曲 / 歌单 / 专辑。"""
    as_json = ctx.obj["json"]
    srcs = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    try:
        client = _make_client(ctx.obj["server"])
        result = song.search(client, keyword, search_type, srcs, exact_artist)
        items = result.get("songs", []) or result.get("playlists", [])
        result["items"] = items[:limit]
        result["display_count"] = len(result["items"])
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"搜索 {keyword!r}（{search_type}）结果: {result['count']} 条", False)
            for i, item in enumerate(items[:limit]):
                if search_type == "song":
                    _echo(f"  [{i}] {item['artist']} - {item['name']} [{item['source']}] ({item['id']})", False)
                else:
                    _echo(f"  [{i}] {item.get('title', item.get('name', ''))} [{item.get('source', '')}]", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- inspect ----------------

@cli.command()
@click.argument("song_id")
@click.argument("source")
@click.pass_context
def inspect(ctx: click.Context, song_id: str, source: str) -> None:
    """探测歌曲下载地址 / 大小 / 码率。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        info = song.inspect(client, song_id, source)
        if as_json:
            _echo({"ok": True, "data": info}, True)
        else:
            _echo(f"  valid:   {info.get('valid')}", False)
            _echo(f"  size:    {info.get('size')}", False)
            _echo(f"  bitrate: {info.get('bitrate')}", False)
            _echo(f"  url:     {info.get('url', '')}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- download ----------------

@cli.command()
@click.option("--keyword", "-k", default="", help="搜索关键词（与 --id 二选一）")
@click.option("--id", "song_id", default="", help="歌曲 ID")
@click.option("--source", default="netease", help="音乐源")
@click.option("--name", default="", help="歌曲名（配合 --id）")
@click.option("--artist", default="", help="歌手（配合 --id）")
@click.option("--index", type=int, default=0, help="搜索结果索引（默认 0）")
@click.option("--dir", "out_dir", default=None, help="下载目录（指定后记住，下次默认使用）")
@click.option("--stream", is_flag=True, help="流式下载到本地（默认交给软件保存）")
@click.pass_context
def download(ctx: click.Context, keyword: str, song_id: str, source: str, name: str, artist: str, index: int, out_dir: str, stream: bool) -> None:
    """下载歌曲（默认 save_local，写入软件下载目录）。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        if keyword:
            target = song.find_song(client, keyword, index)
        elif song_id:
            target = {"id": song_id, "source": source, "name": name, "artist": artist}
        else:
            raise click.UsageError("需要 --keyword 或 --id")
        if stream:
            resolved_dir = resolve_download_dir(out_dir)
            out_path = os.path.join(
                resolved_dir,
                f"{target.get('artist', 'Unknown')} - {target.get('name', 'song')}.mp3",
            )
        else:
            out_path = None
        result = song.download_song(client, target, save_local=not stream, out_path=out_path)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"  下载完成: {result.get('path', result.get('saved'))}", False)
            if result.get("skipped"):
                _echo(f"  跳过（已存在）: {result.get('filename', '')}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.option("--keyword", "-k", default="", help="搜索关键词")
@click.option("--id", "song_id", default="")
@click.option("--source", default="netease")
@click.option("--index", type=int, default=0)
@click.option("--dir", "out_dir", default=None, help="输出目录（指定后记住）")
@click.pass_context
def lyrics(ctx: click.Context, keyword: str, song_id: str, source: str, index: int, out_dir: str) -> None:
    """下载歌词 (.lrc)。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        if keyword:
            target = song.find_song(client, keyword, index)
        elif song_id:
            target = {"id": song_id, "source": source, "name": "Unknown", "artist": "Unknown"}
        else:
            raise click.UsageError("需要 --keyword 或 --id")
        resolved_dir = resolve_download_dir(out_dir)
        path = os.path.join(resolved_dir, f"{target.get('name', 'song')} - {target.get('artist', 'artist')}.lrc")
        result = song.download_lyrics(client, target, out_path=path)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            if result.get("found"):
                _echo(f"  歌词已保存: {result['path']}", False)
            else:
                _echo("  未找到歌词", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.option("--keyword", "-k", default="")
@click.option("--id", "song_id", default="")
@click.option("--source", default="netease")
@click.option("--index", type=int, default=0)
@click.option("--dir", "out_dir", default=None, help="输出目录（指定后记住）")
@click.pass_context
def cover(ctx: click.Context, keyword: str, song_id: str, source: str, index: int, out_dir: str) -> None:
    """下载封面图片。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        if keyword:
            target = song.find_song(client, keyword, index)
        elif song_id:
            target = {"id": song_id, "source": source, "name": "Unknown", "artist": "Unknown"}
        else:
            raise click.UsageError("需要 --keyword 或 --id")
        resolved_dir = resolve_download_dir(out_dir)
        path = os.path.join(resolved_dir, f"{target.get('name', 'cover')} - {target.get('artist', 'artist')}.jpg")
        result = song.download_cover(client, target, out_path=path)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            if result.get("found"):
                _echo(f"  封面已保存: {result['path']}", False)
            else:
                _echo("  未找到封面", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- playlist / album ----------------

@cli.command()
@click.argument("playlist_id")
@click.argument("source")
@click.option("--link", default="", help="原始歌单链接")
@click.pass_context
def playlist_detail(ctx: click.Context, playlist_id: str, source: str, link: str) -> None:
    """获取歌单详情歌曲列表。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = playlist.playlist_detail(client, playlist_id, source, link)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"歌单 {playlist_id} [{source}]: {len(result['songs'])} 首", False)
            for i, s in enumerate(result["songs"]):
                _echo(f"  [{i}] {s['artist']} - {s['name']}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.argument("album_id")
@click.argument("source")
@click.pass_context
def album_detail(ctx: click.Context, album_id: str, source: str) -> None:
    """获取专辑详情歌曲列表。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = playlist.album_detail(client, album_id, source)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"专辑 {album_id} [{source}]: {len(result['songs'])} 首", False)
            for i, s in enumerate(result["songs"]):
                _echo(f"  [{i}] {s['artist']} - {s['name']}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.argument("url")
@click.pass_context
def parse_link(ctx: click.Context, url: str) -> None:
    """解析单曲 / 歌单 / 专辑链接。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = playlist.parse_link(client, url)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"解析 {url}: {len(result['songs'])} 首", False)
            for i, s in enumerate(result["songs"]):
                _echo(f"  [{i}] {s['artist']} - {s['name']} [{s['source']}]", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- records ----------------

@cli.command()
@click.option("--page", type=int, default=1)
@click.option("--page-size", type=int, default=20)
@click.pass_context
def records(ctx: click.Context, page: int, page_size: int) -> None:
    """查询下载记录。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = records_mod.list_records(client, page, page_size)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"下载记录: 共 {result['total']} 条", False)
            for i, rec in enumerate(result.get("records", [])):
                _echo(f"  [{i}] {rec.get('artist', '')} - {rec.get('title', rec.get('name', ''))} | {rec.get('file', '')}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.confirmation_option(prompt="确定清空全部下载记录？")
@click.pass_context
def records_clear(ctx: click.Context) -> None:
    """清空下载记录。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = records_mod.clear_records(client)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo("  已清空下载记录", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- settings ----------------

@cli.command()
@click.pass_context
def settings(ctx: click.Context) -> None:
    """查看后端设置。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = settings_mod.get_settings(client)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo("后端设置:", False)
            for k, v in result.items():
                _echo(f"  {k}: {v}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.option("--key", required=True, help="设置键")
@click.option("--value", required=True, help="设置值（自动按类型转换）")
@click.pass_context
def settings_set(ctx: click.Context, key: str, value: str) -> None:
    """更新单个后端设置。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        current = settings_mod.get_settings(client)
        if key not in current:
            raise ValueError(f"未知设置项: {key}")
        if isinstance(current[key], bool):
            value = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(current[key], int):
            value = int(value)
        elif isinstance(current[key], float):
            value = float(value)
        result = settings_mod.update_settings(client, {key: value})
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"  已更新 {key} = {value}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- cookies ----------------

@cli.command()
@click.pass_context
def cookies(ctx: click.Context) -> None:
    """查看后端 Cookie。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = settings_mod.get_cookies(client)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo("后端 Cookie:", False)
            for k, v in result.items():
                _echo(f"  {k}: {v if not v else '(已设置)'}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.option("--key", required=True, help="平台名，如 netease")
@click.option("--value", default="", help="Cookie 值")
@click.pass_context
def cookies_set(ctx: click.Context, key: str, value: str) -> None:
    """设置 / 清除某个平台的 Cookie。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = settings_mod.set_cookies(client, {key: value})
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"  已设置 {key} Cookie", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- local / collection ----------------

@cli.command()
@click.option("--page", type=int, default=1)
@click.option("--page-size", type=int, default=200)
@click.option("--keyword", default="")
@click.pass_context
def local(ctx: click.Context, page: int, page_size: int, keyword: str) -> None:
    """列出本地音乐。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = collection.local_music_page(client, page, page_size, keyword)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            items = result.get("items", result.get("songs", []))
            _echo(f"本地音乐: {len(items)} 条", False)
            for i, item in enumerate(items):
                _echo(f"  [{i}] {item.get('artist', '')} - {item.get('name', '')}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


@cli.command()
@click.pass_context
def collections(ctx: click.Context) -> None:
    """列出我的歌单（本地收藏）。"""
    as_json = ctx.obj["json"]
    try:
        client = _make_client(ctx.obj["server"])
        result = collection.my_collections(client)
        if as_json:
            _echo({"ok": True, "data": result}, True)
        else:
            _echo(f"我的歌单: {len(result)} 个", False)
            for i, c in enumerate(result):
                _echo(f"  [{i}] {c.get('name', c.get('title', ''))}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- delete ----------------

@cli.command()
@click.option("--local-id", "local_id", default="", help="本地音乐 ID（经后端 API 硬删）")
@click.option("--collection", "collection_id", default="", help="本地歌单 ID（删除整个歌单）")
@click.option("--song", "song_id", default="", help="从歌单移除的歌曲 ID（需配合 --collection）")
@click.option("--source", "source", default="", help="歌曲所属源（配合 --song）")
@click.option("--file", "file_paths", multiple=True, help="直接删除的本地文件路径（可多次）")
@click.option("--name", "name", default="", help="按歌名匹配删除下载目录文件")
@click.option("--artist", "artist", default="", help="按歌手匹配删除下载目录文件")
@click.option("--dir", "download_dir", default="", help="下载目录（配合 --name/--artist）")
@click.option("--yes", "yes", is_flag=True, help="跳过确认（删除不可撤销）")
@click.pass_context
def delete(ctx: click.Context, local_id: str, collection_id: str, song_id: str, source: str, file_paths, name: str, artist: str, download_dir: str, yes: bool) -> None:
    """删除歌曲/歌单/本地下载文件（不可撤销）。"""
    as_json = ctx.obj["json"]

    # 1) 经后端 API 删除
    if local_id:
        if not yes and not as_json and not click.confirm(f"确定删除本地音乐 #{local_id}？(硬删磁盘文件)"):
            _err("已取消", as_json)
            return
        try:
            client = _make_client(ctx.obj["server"])
            result = delete_mod.delete_local_music(client, local_id)
            _echo({"ok": True, "data": result}, True) if as_json else _echo(f"  已删除本地音乐 #{local_id}", False)
        except Exception as e:  # noqa: BLE001
            _err(str(e), as_json)
        return

    if collection_id and song_id and source:
        if not yes and not as_json and not click.confirm(f"确定从歌单 {collection_id} 移除 {song_id}？"):
            _err("已取消", as_json)
            return
        try:
            client = _make_client(ctx.obj["server"])
            result = delete_mod.delete_collection_song(client, collection_id, song_id, source)
            _echo({"ok": True, "data": result}, True) if as_json else _echo("  已从歌单移除", False)
        except Exception as e:  # noqa: BLE001
            _err(str(e), as_json)
        return

    if collection_id:
        if not yes and not as_json and not click.confirm(f"确定删除整个歌单 {collection_id}？"):
            _err("已取消", as_json)
            return
        try:
            client = _make_client(ctx.obj["server"])
            result = delete_mod.delete_collection(client, collection_id)
            _echo({"ok": True, "data": result}, True) if as_json else _echo(f"  已删除歌单 {collection_id}", False)
        except Exception as e:  # noqa: BLE001
            _err(str(e), as_json)
        return

    # 2) 直接删除下载目录文件（文件系统操作）
    if file_paths or name or artist:
        if not download_dir:
            try:
                client = _make_client(ctx.obj["server"])
                download_dir = client.get_settings().get("downloadDir", "data/downloads")
            except Exception:
                download_dir = "data/downloads"
        if file_paths:
            targets = list(file_paths)
            desc = " ".join(targets)
        elif name or artist:
            targets = None
            desc = f"{artist} - {name}" if artist else name
        else:
            targets = None
            desc = "全部文件"
        if not yes and not as_json and not click.confirm(f"确定删除下载目录文件：{desc}？(不可撤销)"):
            _err("已取消", as_json)
            return
        try:
            result = delete_mod.delete_download_files(download_dir, name=name, artist=artist, paths=list(file_paths) if file_paths else None)
            if as_json:
                _echo({"ok": True, "data": result}, True)
            else:
                _echo(f"  删除 {result['deleted']}/{result['total']} 个文件", False)
                for f in result.get("files", []):
                    _echo(f"    {'✓' if f['deleted'] else '✗'} {f['path']}", False)
        except Exception as e:  # noqa: BLE001
            _err(str(e), as_json)
        return

    # 3) 无参数：列出下载目录
    try:
        client = _make_client(ctx.obj["server"])
        d = download_dir or client.get_settings().get("downloadDir", "data/downloads")
        files = delete_mod.list_local_downloads(d)
        if as_json:
            _echo({"ok": True, "data": {"download_dir": d, "files": files}}, True)
        else:
            _echo(f"下载目录 {d}: {len(files)} 个文件", False)
            for f in files:
                _echo(f"  {os.path.basename(f)}", False)
    except Exception as e:  # noqa: BLE001
        _err(str(e), as_json)


# ---------------- REPL ----------------

REPL_COMMANDS = {
    "server": "探测并显示后端服务信息",
    "search <关键词> [--type song|playlist|album]": "搜索歌曲/歌单/专辑",
    "inspect <id> <source>": "探测歌曲下载地址",
    "download --keyword 关键词 [--index N]": "下载歌曲（保存到软件目录）",
    "download --id ID --source SRC --stream --dir ./out": "流式下载到本地目录",
    "lyrics --keyword 关键词": "下载歌词",
    "cover --keyword 关键词": "下载封面",
    "playlist-detail <id> <source>": "歌单详情",
    "album-detail <id> <source>": "专辑详情",
    "parse-link <url>": "解析歌单/专辑链接",
    "records [--page N]": "查询下载记录",
    "settings": "查看设置",
    "cookies": "查看 Cookie",
    "local": "本地音乐列表",
    "collections": "我的歌单",
    "delete --local-id ID": "删除本地音乐",
    "delete --collection ID [--song SID --source SRC]": "删除歌单/歌单内歌曲",
    "delete --name 歌名 [--artist 歌手] --dir 下载目录 --yes": "直接删除下载文件",
    "delete": "列出下载目录文件",
    "help": "显示帮助",
    "exit": "退出",
}


@cli.command(hidden=True)
@click.pass_context
def repl(ctx: click.Context) -> None:
    """交互式 REPL。"""
    server = ctx.obj.get("server", "")
    base = ""
    try:
        base = resolve_base_url(server)
    except RuntimeError as e:
        click.echo(f"⚠ {e}", err=True)
    skill_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "skills", "SKILL.md")
    )
    skin = ReplSkin("go-music-dl", version=__version__, skill_path=skill_path)
    skin.print_banner()
    if not base:
        skin.error("未检测到后端服务。请先启动桌面应用或指定 --server。")
        return
    skin.success(f"已连接后端: {base}")
    skin.help(REPL_COMMANDS)
    while True:
        try:
            line = skin.get_input(project_name="go-music-dl")
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in ("exit", "quit", "q"):
            break
        if line == "help":
            skin.help(REPL_COMMANDS)
            continue
        args = shlex.split(line)
        try:
            from click.testing import CliRunner

            runner = CliRunner()
            # 注入 server 参数
            if server:
                args = ["--server", server, *args]
            result = runner.invoke(cli, args, input="", catch_exceptions=False)
            if result.output:
                click.echo(result.output.rstrip())
            if result.exit_code != 0:
                skin.error(f"命令失败 (exit {result.exit_code})")
        except Exception as e:  # noqa: BLE001
            skin.error(str(e))
    skin.print_goodbye()


if __name__ == "__main__":
    cli()
