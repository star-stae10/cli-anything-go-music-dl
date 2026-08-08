# GO_MUSIC_DL.md — go-music-dl CLI Harness 架构分析

## 1. 软件概述

go-music-dl 是一个 Go 编写的**聚合音乐搜索与下载工具**，支持 Web 界面、TUI 终端和桌面应用三种模式。核心能力：

- 多平台聚合搜索：网易云、QQ、酷狗、酷我、咪咕、千千、汽水、5sing、Jamendo、JOOX、Bilibili 等
- 单曲 / 歌单 / 专辑 搜索与下载
- 无损音乐（FLAC）支持（网易云、QQ、Bilibili）
- 歌词 / 封面下载，LRC 双格式（原文/译文/罗马音）
- 歌单链接 / 专辑链接解析
- 本地自制歌单、收藏、本地音乐管理
- Cookie 扫码登录
- 下载记录持久化（SQLite）

## 2. 架构发现

### 2.1 进程模型

| 组件 | 说明 |
|------|------|
| `music-dl` (CLI/TUI) | `cmd/music-dl`，Cobra 命令行 + 交互式 TUI |
| `music-dl web` | `internal/web`，Gin HTTP 服务，默认端口 8080 |
| `music-dl-desktop-go.exe` | 桌面 GUI，内嵌 Web 服务监听 `127.0.0.1:<port>`，默认关闭鉴权 |
| `data/settings.db` | SQLite，存储配置、Cookie、下载记录、本地歌单、本地音乐索引 |

### 2.2 后端引擎

核心库在 `core/`（`service.go`、`download.go`、`config_store.go` 等），提供：
- `core.GetSearchFunc(src)` / `GetPlaylistSearchFunc` / `GetAlbumSearchFunc` — 各源搜索
- `core.GetDownloadFunc(src)` — 获取下载 URL
- `core.GetPlaylistDetailFunc` / `GetAlbumDetailFunc` — 详情
- `core.GetLyricFunc` — 歌词
- `core.GetParseFunc` / `GetParsePlaylistFunc` / `GetParseAlbumFunc` — 链接解析

**关键发现**：桌面 GUI 通过内嵌 HTTP 服务暴露完整 Web API，这是我们 CLI 后端的最佳集成点。它本身就是"软件的真实接口"，不是 Python 重实现。

### 2.3 数据模型

- `model.Song`：`{ID, Source, Name, Artist, Album, Cover, Duration, Extra, Link}`
- `model.Playlist`：`{ID, Source, Title, Count, Cover, Link, ...}`
- `core.DownloadRecord`：`{ID, Title, Artist, Album, File, Size, Source, Time, ...}`
- `core.WebSettings`：`{embedDownload, downloadToLocal, downloadDir, downloadFilenameTemplate, downloadConcurrency, ...}`

### 2.4 已确认的 HTTP API（桌面版基址 `http://127.0.0.1:18901/music`）

| 方法 | 路径 | 返回 | 说明 |
|------|------|------|------|
| GET | `/healthz` | JSON | 健康检查 |
| GET | `/settings` | JSON | 读取设置 |
| GET | `/search?q=&type=song\|playlist\|album&sources=` | HTML(SSR) | 搜索，页面含 `li.song-card[data-*]` |
| GET | `/inspect?id=&source=&extra=` | JSON | 探测下载 URL / 大小 / 码率 |
| GET/POST | `/download?id=&source=&name=&artist=&album=&cover=&extra=&save_local=1` | 音频流 或 JSON | 下载；`save_local=1` 时保存到软件下载目录并返回 JSON |
| GET | `/download_lrc?id=&source=...&format=auto` | LRC 文本 | 歌词 |
| GET | `/download_cover?url=&name=&artist=` | 图片 | 封面 |
| GET | `/playlist?id=&source=` | HTML(SSR) | 歌单详情 |
| GET | `/album?id=&source=` | HTML(SSR) | 专辑详情 |
| GET | `/api/downloads/records?page=&page_size=` | JSON | 下载记录分页 |
| GET | `/my_collections` | JSON | 本地歌单列表 |
| GET | `/collection?id=` | HTML(SSR) | 歌单内容 |
| GET | `/local_music_page` / `/local_music` | JSON | 本地音乐 |
| GET/POST | `/cookies` | JSON | Cookie 管理（需鉴权） |
| GET/POST | `/settings` | JSON | 设置读写（POST 需鉴权） |
| GET | `/playlist_categories` / `/category_playlists` | HTML(SSR) | 歌单分类 |
| GET | `/recommend` / `/user_playlists` | HTML(SSR) | 推荐 / 我的歌单 |

## 3. CLI 架构设计

### 3.1 交互模型

- **一次性子命令**：`cli-anything-go-music-dl search "周杰伦" --json`
- **REPL**：无子命令时进入交互式 REPL（`invoke_without_command=True`）
- **`--json` 全局开关**：所有命令输出机器可读 JSON

### 3.2 命令组（按领域映射）

| 命令组 | 功能域 | 后端 API |
|--------|--------|----------|
| `server` | 后端服务管理（find/health/ping） | 端口探测 + `/healthz` |
| `search` | 单曲 / 歌单 / 专辑搜索，链接解析 | `/search` + HTML 解析 |
| `song` | 歌曲详情、inspect 探测、下载 URL | `/inspect` |
| `download` | 下载音频 / 歌词 / 封面 | `/download`, `/download_lrc`, `/download_cover` |
| `records` | 下载记录查询 / 清空 | `/api/downloads/records` |
| `playlist` | 歌单详情、解析 | `/playlist` + HTML 解析 |
| `album` | 专辑详情、解析 | `/album` + HTML 解析 |
| `collection` | 本地歌单（我的收藏） | `/my_collections`, `/collection` |
| `local` | 本地音乐列表 | `/local_music_page`, `/local_music` |
| `settings` | 查看 / 更新设置 | `/settings` |
| `cookies` | Cookie 查看 / 更新 | `/cookies` |

### 3.3 状态模型

- 无持久化项目文件；"项目"= 后端软件实例（base URL + 下载目录）
- 会话状态：`ServerConfig`（base URL，可配置 `--server`）
- 输出：统一 `{ok, data, meta}` 结构；错误 `{ok:false, error}`

### 3.4 后端集成原则

- **调用真实软件**：所有命令走桌面版 / Web 版的 HTTP API（`utils/go_music_dl_backend.py`）
- 搜索 HTML 解析 `li.song-card` 的 `data-id / data-source / data-name / data-artist / data-album / data-duration / data-cover / data-extra`
- 下载优先 `save_local=1`（软件自身完成去重、嵌入元数据、文件名模板），返回文件路径
- 后端未启动时给出明确安装 / 启动指引，不降级

## 4. 目录结构

```
agent-harness/
├── GO_MUSIC_DL.md              # 本文件
├── setup.py
└── cli_anything/               # PEP 420 命名空间包（无 __init__.py）
    └── go_music_dl/
        ├── __init__.py
        ├── __main__.py
        ├── README.md
        ├── go_music_dl_cli.py  # Click 入口 + REPL
        ├── core/               # project/settings/records/song 等
        ├── utils/              # backend (HTTP)、html_parse、repl_skin
        └── tests/              # TEST.md + test_core.py + test_full_e2e.py
```
