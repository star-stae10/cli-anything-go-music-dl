# TEST.md — cli-anything-go-music-dl 测试文档

## Part 1: 测试计划

### 1. 测试清单

- `test_core.py`：约 14 个单元测试（合成数据，无外部依赖）
- `test_full_e2e.py`：约 8 个 E2E 测试（真实后端 + 真实下载）

### 2. 单元测试计划

| 模块 | 测试函数 | 边界用例 |
|------|----------|----------|
| `utils/html_parse.py` | `parse_songs` | 空 HTML、无 song-card、含 data-extra JSON、属性缺省 |
| `utils/html_parse.py` | `search_results` | song / playlist / album 三种类型 |
| `utils/html_parse.py` | `song_to_query_params` | extra 缺省、album 回退 |
| `core/settings.py` | `update_settings` | 未知键报错、类型保持 |
| `core/records.py` | `list_records` | page<1、page_size<1 归一化 |
| `core/song.py` | `search` | 非法 search_type 报错 |
| `core/song.py` | `find_song` | 空结果、索引越界 |
| `utils/go_music_dl_backend.py` | `_suggest_filename` | 非法字符清洗、空名回退 |

### 3. E2E 测试计划（真实后端）

需要本机运行 go-music-dl 桌面版/Web 版（自动探测 `127.0.0.1`）。测试：

- `server --json` 探测后端 → ok
- `search --json "关键词"` → 返回歌曲列表
- `inspect <id> <source>` → valid=true、url 非空
- 真实下载（save_local）→ saved=true、文件存在（ID3 头）
- 流式下载到临时目录 → 文件存在且大小>0
- 下载记录查询 → 非空
- CLI 子进程：`--help`、`--json server`、完整工作流

> 注：E2E 依赖外网与平台 API，网络/授权不可用时搜索可能返回空。按 HARNESS.md
> 要求不降级，测试失败即失败并提示原因。

### 4. 真实工作流场景

- **搜索→探测→下载**：搜索"周杰伦" → inspect 取首个 → save_local 下载 → 校验 ID3
- **流式下载**：download --stream 到临时目录 → 校验 magic bytes
- **CLI 全链路**：子进程调用 search + download，校验 stdout JSON

## Part 2: 测试结果

（运行 `pytest -v --tb=no` 后追加）

### 测试结果（2026-08-07，force-installed 模式）

**Summary:** 28 passed in ~7-14s（连续 3 次全绿），通过率 100%

```
platform win32 -- Python 3.14.6, pytest-9.1.1
collected 28 items

test_core.py::test_parse_songs_basic PASSED
test_core.py::test_parse_songs_empty PASSED
test_core.py::test_parse_songs_missing_fields PASSED
test_core.py::test_parse_songs_bad_extra PASSED
test_core.py::test_search_results_types PASSED
test_core.py::test_song_to_query_params PASSED
test_core.py::test_update_settings_unknown_key PASSED
test_core.py::test_update_settings_merge PASSED
test_core.py::test_cookies_set_merge PASSED
test_core.py::test_list_records_normalizes_page PASSED
test_core.py::test_clear_records PASSED
test_core.py::test_search_invalid_type PASSED
test_core.py::test_find_song_empty PASSED
test_core.py::test_find_song_index_out_of_range PASSED
test_core.py::test_find_song_ok PASSED
test_core.py::test_suggest_filename_sanitize PASSED
test_core.py::test_is_port_open_closed PASSED
test_full_e2e.py::test_server_health PASSED
test_full_e2e.py::test_settings_read PASSED
test_full_e2e.py::test_search_returns_songs PASSED
test_full_e2e.py::test_inspect_valid PASSED
test_full_e2e.py::test_real_download_save_local PASSED
test_full_e2e.py::test_real_download_stream PASSED
test_full_e2e.py::TestCLISubprocess::test_help PASSED
test_full_e2e.py::TestCLISubprocess::test_version PASSED
test_full_e2e.py::TestCLISubprocess::test_server_json PASSED
test_full_e2e.py::TestCLISubprocess::test_search_json PASSED
test_full_e2e.py::TestCLISubprocess::test_full_workflow PASSED

============================= 28 passed =============================
```

### 覆盖率说明

- **单元测试**（17）：HTML 解析、设置/记录/歌曲核心逻辑、文件名清洗、端口探测
- **E2E 真实后端**（11）：health/settings/search/inspect、save_local 下载（含去重跳过场景）、流式下载（验证 ID3/MPEG magic bytes 与文件大小）、CLI 子进程全工作流（server→search→inspect→download→验证文件）
- **覆盖缺口**：
  - 歌单/专辑详情、链接解析未做真实 E2E（需要歌单 ID，可用时补充）
  - Cookie 登录、settings-set 写操作未测（需管理员鉴权）
  - 网易云/QQ 平台受外部限流影响不稳定，E2E 下载类测试优先使用 kuwo 源
  - REPL 交互未做自动化测试

