"""test_core.py — 单元测试（合成数据，无外部依赖）。"""

import json

import pytest

from cli_anything.go_music_dl.core import delete as delete_mod
from cli_anything.go_music_dl.core import records, settings as settings_mod, song
from cli_anything.go_music_dl.utils import dir_config, fs_delete, go_music_dl_backend as backend
from cli_anything.go_music_dl.utils import html_parse


class FakeClient:
    """模拟 BackendClient，避免网络依赖。"""

    def __init__(self, **overrides):
        self._settings = {"downloadDir": "data/downloads", "downloadConcurrency": 3}
        self._cookies = {"netease": "abc"}
        self._records = {"records": [{"Name": "歌", "Artist": "手"}], "total": 1, "page": 1, "page_size": 20, "total_pages": 1}
        self._search_html = ""
        self._inspect = {"valid": True, "url": "http://x/m.mp3", "size": "1 MB", "bitrate": "128 kbps"}
        self._overrides = overrides

    def get_settings(self):
        return dict(self._settings)

    def post_settings(self, merged):
        self._settings = dict(merged)
        return dict(self._settings)

    def get_cookies(self):
        return dict(self._cookies)

    def post_cookies(self, merged):
        self._cookies = dict(merged)
        return dict(self._cookies)

    def search_page(self, keyword, search_type="song", sources=None, exact_artist=""):
        return self._overrides.get("search_html", self._search_html)

    def inspect(self, song_id, source, extra=None):
        return dict(self._inspect)

    def download_records(self, page=1, page_size=20):
        return dict(self._records)

    def clear_download_records(self):
        return {"status": "ok"}


SONG_HTML = """
<html><body><ul>
<li class="song-card"
    data-id="5257138" data-source="netease" data-album-id="ALB" data-album="专辑"
    data-duration="319" data-name="屋顶" data-artist="周杰伦"
    data-cover="http://c.jpg" data-sort-size="1"
    data-extra='{"song_id":"5257138","size":"123"}'>
</li>
</ul></body></html>
"""


# ---------------- html_parse ----------------

def test_parse_songs_basic():
    songs = html_parse.parse_songs(SONG_HTML)
    assert len(songs) == 1
    s = songs[0]
    assert s["id"] == "5257138"
    assert s["source"] == "netease"
    assert s["name"] == "屋顶"
    assert s["artist"] == "周杰伦"
    assert s["album"] == "专辑"
    assert s["duration"] == "319"
    assert s["cover"] == "http://c.jpg"
    assert s["extra"]["song_id"] == "5257138"


def test_parse_songs_empty():
    assert html_parse.parse_songs("") == []
    assert html_parse.parse_songs("<html><body><p>no cards</p></body></html>") == []


def test_parse_songs_missing_fields():
    html = '<li class="song-card" data-id="1" data-source="qq" data-duration="" data-name="n" data-artist="a" data-extra=\'{}\'></li>'
    songs = html_parse.parse_songs(html)
    assert len(songs) == 1
    assert songs[0]["album"] == ""
    assert songs[0]["extra"] == {}


def test_parse_songs_bad_extra():
    html = '<li class="song-card" data-id="1" data-source="qq" data-duration="1" data-name="n" data-artist="a" data-extra=\'{bad json\'></li>'
    songs = html_parse.parse_songs(html)
    assert songs[0]["extra"] == {}


def test_search_results_types():
    r_song = html_parse.search_results(SONG_HTML, "song")
    assert r_song["type"] == "song"
    assert r_song["count"] == 1

    r_album = html_parse.search_results(SONG_HTML, "album")
    assert r_album["type"] == "album"
    assert isinstance(r_album["playlists"], list)


def test_song_to_query_params():
    s = {
        "id": "1", "source": "netease", "name": "n", "artist": "a",
        "album": "", "cover": "", "duration": "10", "extra": {"album": "via-extra"},
    }
    p = html_parse.song_to_query_params(s)
    assert p["album"] == "via-extra"
    assert p["id"] == "1"

    p2 = html_parse.song_to_query_params({"id": "2", "source": "qq", "extra": {}})
    assert p2["name"] == "Unknown"
    assert p2["artist"] == "Unknown"


# ---------------- settings ----------------

def test_update_settings_unknown_key():
    client = FakeClient()
    with pytest.raises(ValueError):
        settings_mod.update_settings(client, {"not_a_key": 1})


def test_update_settings_merge():
    client = FakeClient()
    result = settings_mod.update_settings(client, {"downloadConcurrency": 5})
    assert result["downloadConcurrency"] == 5
    assert result["downloadDir"] == "data/downloads"


def test_cookies_set_merge():
    client = FakeClient()
    result = settings_mod.set_cookies(client, {"qq": "xyz"})
    assert result["netease"] == "abc"
    assert result["qq"] == "xyz"


# ---------------- records ----------------

def test_list_records_normalizes_page():
    client = FakeClient()
    r0 = records.list_records(client, page=0, page_size=0)
    assert r0["page"] == 1
    assert r0["page_size"] == 20


def test_clear_records():
    client = FakeClient()
    assert records.clear_records(client) == {"status": "ok"}


# ---------------- song ----------------

def test_search_invalid_type():
    client = FakeClient()
    with pytest.raises(ValueError):
        song.search(client, "周杰伦", "badtype")


def test_find_song_empty():
    client = FakeClient(search_html="<html></html>")
    with pytest.raises(ValueError):
        song.find_song(client, "不存在")


def test_find_song_index_out_of_range():
    client = FakeClient(search_html=SONG_HTML)
    with pytest.raises(ValueError):
        song.find_song(client, "屋顶", index=5)


def test_find_song_ok():
    client = FakeClient(search_html=SONG_HTML)
    s = song.find_song(client, "屋顶", index=0)
    assert s["id"] == "5257138"


# ---------------- backend util ----------------

def test_suggest_filename_sanitize():
    assert backend._suggest_filename('a<b>c:d"e', "x") == "x - abcde.mp3"
    assert backend._suggest_filename("", "") == "unknown - song.mp3"


def test_is_port_open_closed():
    assert backend._is_port_open("127.0.0.1", 1, timeout=0.3) is False


# ---------------- fs_delete ----------------

def test_safe_join_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        fs_delete.safe_join(str(tmp_path), "../../etc/passwd")
    joined = fs_delete.safe_join(str(tmp_path), "周杰伦 - 屋顶.mp3")
    assert joined == str(tmp_path / "周杰伦 - 屋顶.mp3")


def test_find_by_name_and_delete(tmp_path):
    (tmp_path / "周杰伦 - 屋顶.mp3").write_bytes(b"mp3data")
    (tmp_path / "黄诗扶 - 吹梦到西洲.mp3").write_bytes(b"mp3data")
    (tmp_path / "note.txt").write_text("keep")

    matches = fs_delete.find_by_name(str(tmp_path), "屋顶")
    assert len(matches) == 1
    assert "屋顶" in matches[0]

    matches2 = fs_delete.find_by_name(str(tmp_path), "吹梦到西洲", artist="黄诗扶")
    assert len(matches2) == 1
    assert "黄诗扶" in matches2[0]

    result = fs_delete.delete_files([str(tmp_path / "周杰伦 - 屋顶.mp3"), str(tmp_path / "nonexist.mp3")])
    assert result["deleted"] == 1
    assert result["total"] == 2
    assert not (tmp_path / "周杰伦 - 屋顶.mp3").exists()
    assert (tmp_path / "黄诗扶 - 吹梦到西洲.mp3").exists()
    assert (tmp_path / "note.txt").exists()


def test_list_downloads_only_audio_like(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"x")
    (tmp_path / "b.flac").write_bytes(b"x")
    (tmp_path / "c.txt").write_text("x")
    files = fs_delete.list_downloads(str(tmp_path))
    assert len(files) == 2


def test_delete_download_files_by_name(tmp_path):
    (tmp_path / "歌手 - 歌名.mp3").write_bytes(b"x")
    result = delete_mod.delete_download_files(str(tmp_path), name="歌名", artist="歌手")
    assert result["deleted"] == 1
    assert not (tmp_path / "歌手 - 歌名.mp3").exists()


def test_delete_download_files_no_match(tmp_path):
    result = delete_mod.delete_download_files(str(tmp_path), name="不存在")
    assert result["deleted"] == 0
    assert result["total"] == 0


# ---------------- dir_config（下载目录记忆） ----------------

@pytest.fixture
def cfg_tmp(tmp_path, monkeypatch):
    """把配置重定向到临时目录，测试后清理。"""
    cfg_file = tmp_path / ".cfg.json"
    monkeypatch.setattr(dir_config, "_CONFIG_FILE", str(cfg_file))
    return tmp_path


def test_resolve_explicit_saves_and_remembers(cfg_tmp):
    d = cfg_tmp / "Music"
    d.mkdir()
    # 第一次显式指定 → 记住
    r1 = dir_config.resolve_download_dir(str(d))
    assert r1 == str(d)
    assert dir_config.get_saved_download_dir() == str(d)
    # 第二次不指定 → 用记住的
    r2 = dir_config.resolve_download_dir()
    assert r2 == str(d)


def test_resolve_explicit_nonexistent_raises(cfg_tmp):
    missing = cfg_tmp / "no-such-dir"
    with pytest.raises(RuntimeError):
        dir_config.resolve_download_dir(str(missing))


def test_resolve_scans_default_then_remembers(cfg_tmp, monkeypatch):
    # 构造一个默认扫描路径存在，且无已记忆配置的场景
    fake_default = cfg_tmp / "go music" / "data" / "downloads"
    fake_default.mkdir(parents=True)
    monkeypatch.setattr(dir_config, "scan_default_candidates", lambda cwd=None: [str(fake_default)])
    r = dir_config.resolve_download_dir()
    assert r == str(fake_default)
    assert dir_config.get_saved_download_dir() == str(fake_default)


def test_resolve_nothing_found_raises(cfg_tmp, monkeypatch):
    monkeypatch.setattr(dir_config, "scan_default_candidates", lambda cwd=None: [])
    with pytest.raises(RuntimeError):
        dir_config.resolve_download_dir()


def test_save_download_dir_nonexistent_raises(cfg_tmp):
    with pytest.raises(RuntimeError):
        dir_config.save_download_dir(str(cfg_tmp / "missing"))


def test_find_by_name_artist_exact_not_substring(tmp_path):
    """回归测试：--artist 必须精确匹配歌手字段，不能子串误伤。

    场景：artist='黄诗扶、王敬轩(妖扬)' 应只匹配 QQ 试听版，
    绝不能误伤 '恋恋故人难、黄诗扶、王敬轩（妖扬）' 原版。
    """
    (tmp_path / "恋恋故人难、黄诗扶、王敬轩（妖扬） - 吹梦到西洲.mp3").write_bytes(b"x")
    (tmp_path / "黄诗扶、王敬轩(妖扬) - 吹梦到西洲.mp3").write_bytes(b"x")
    (tmp_path / "黄诗扶 - 独唱版.mp3").write_bytes(b"x")

    # 精确歌手字段 = '黄诗扶、王敬轩(妖扬)' 的只有 QQ 试听版
    matches = fs_delete.find_by_name(str(tmp_path), "吹梦到西洲", artist="黄诗扶、王敬轩(妖扬)")
    assert len(matches) == 1, f"应只匹配 1 个，实际: {matches}"
    assert "恋恋故人难" not in matches[0]
    assert "独唱版" not in matches[0]

    # 原版歌手字段必须与 '黄诗扶、王敬轩(妖扬)' 不同，删不到
    original = fs_delete.find_by_name(str(tmp_path), "吹梦到西洲", artist="恋恋故人难、黄诗扶、王敬轩（妖扬）")
    assert len(original) == 1
    assert "恋恋故人难" in original[0]

    # 不带 artist 时按歌名仍应匹配多首
    by_title = fs_delete.find_by_name(str(tmp_path), "吹梦到西洲")
    assert len(by_title) == 2


def test_split_song_filename():
    assert fs_delete._split_song_filename("周杰伦 - 屋顶.mp3") == ("周杰伦", "屋顶")
    assert fs_delete._split_song_filename("宇多田ヒカル - One Last Kiss.flac") == ("宇多田ヒカル", "One Last Kiss")
    assert fs_delete._split_song_filename("纯歌名.mp3") == ("", "纯歌名")
