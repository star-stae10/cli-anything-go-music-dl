# cli-anything-go-music-dl

> go-music-dl 聚合音乐搜索下载工具的 **Agent 命令行工具** —— 用命令行、脚本或 AI
> 直接操纵真实的 go-music-dl 软件，无需打开图形界面。

`cli-anything-go-music-dl` 是 [go-music-dl](https://github.com/guohuiyuan/go-music-dl)
（多平台聚合音乐搜索下载工具）的命令行封装。它通过软件自带的 HTTP 接口驱动真实的
go-music-dl 引擎完成搜索、探测、下载、管理等工作 —— **CLI 是遥控器，软件才是引擎**，
不重实现任何搜索/下载逻辑。

- 🎵 覆盖 **12+ 个音乐源**：网易云、QQ、酷狗、酷我、咪咕、千千、汽水、5sing、Jamendo、JOOX、Bilibili、Apple Music 等
- 🤖 **Agent 友好**：全部命令支持 `--json` 机器可读输出，附带交互式 REPL 与配套 skill
- 📁 **下载目录记忆**：`--dir` 指定一次，后续默认沿用，直到再次指定
- 🚀 **软件自动启动**：`server --exe <路径>` 记住软件位置，检测不到时自动静默拉起
- 🗑️ **安全删除**：删除歌曲/歌单/下载文件，支持精确匹配防止误删

## 安装

```bash
# 从 PyPI 安装（推荐）
pip install cli-anything-go-music-dl
```

或从源码安装：

```bash
git clone https://github.com/star-stae10/cli-anything-go-music-dl.git
cd cli-anything-go-music-dl
pip install .
```

## 前置依赖

**go-music-dl 软件是硬依赖**，CLI 必须连接运行中的软件实例：

1. 下载桌面版（推荐）：GitHub Releases → [go-music-dl/releases](https://github.com/guohuiyuan/go-music-dl/releases)，解压后双击 `music-dl-desktop-go.exe`
2. 或 Web 模式：`music-dl web --no-browser`

## 快速开始

```bash
# 1. 确认安装
cli-anything-go-music-dl --version

# 2. 连接后端（软件运行中会自动探测）
cli-anything-go-music-dl server

# 3. 让 CLI 记住软件位置（之后软件没开也能自动启动，推荐）
cli-anything-go-music-dl server --exe "C:\你的路径\music-dl-desktop-go.exe"

# 4. 指定下载目录（目录必须已存在；指定一次后默认沿用）
mkdir -p "D:\Music\downloads"
cli-anything-go-music-dl download --keyword "测试" --stream --dir "D:\Music\downloads"

# 5. 下载一首歌
cli-anything-go-music-dl search "吹梦到西洲 黄诗扶" --limit 20
cli-anything-go-music-dl --json inspect <歌曲ID> <音源>
cli-anything-go-music-dl download --id <ID> --source netease --name "歌名" --artist "歌手" --stream
```

## 命令一览

| 命令 | 功能 |
|------|------|
| `server` | 探测后端；`--exe` 记住并自动启动软件 |
| `search` | 单曲/歌单/专辑搜索（`--sources` 指定音源） |
| `inspect` | 探测歌曲下载地址/大小/码率 |
| `download` | 下载歌曲（save_local 或 `--stream` 到指定目录） |
| `lyrics` / `cover` | 下载歌词 / 封面 |
| `playlist-detail` / `album-detail` | 歌单 / 专辑详情 |
| `parse-link` | 解析单曲/歌单/专辑链接 |
| `records` / `records-clear` | 下载记录查询 / 清空 |
| `settings` / `settings-set` | 查看 / 更新设置 |
| `cookies` / `cookies-set` | 查看 / 设置 Cookie |
| `local` | 本地音乐列表 |
| `collections` | 我的歌单 |
| `delete` | 删除歌曲/歌单/下载文件 |

所有命令支持 `--json`（全局选项，放命令前）和 `--help`。

## 音源

`netease`（网易云）、`qq`（QQ音乐）、`kugou`（酷狗）、`kuwo`（酷我）、`migu`（咪咕）、
`qianqian`（千千）、`soda`（汽水）、`fivesing`（5sing）、`jamendo`、`joox`、`bilibili`、
`apple`、`local`（本地）

> **搜索策略**：知道歌曲在哪个音源就传入 `--sources` 指定；不知道音源就**不传**，
> 让软件聚合所有源一起搜索。同一首歌不同源可用性差异大，**kuwo（酷我）通常最稳**，
> 无需登录即可下载；QQ 无 Cookie 仅试听版；汽水/咪咕部分歌曲仅会员。

## Agent / AI 使用

配套 skill（`go-music-dl-cli`）提供了完整操作指南：操作前必须先确保软件运行、
搜索策略、音源可靠性排序、限流应对、删除安全等全部踩坑经验。

详见 [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md)。

## 测试

```bash
pip install pytest
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/go_music_dl/tests/ -v
```

- 单元测试：无外部依赖，纯逻辑
- E2E 测试：需要本机运行 go-music-dl 后端 + 网络，会产生真实下载文件

## 文档

- [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) — Agent 使用指南
- [agent-harness/GO_MUSIC_DL.md](agent-harness/GO_MUSIC_DL.md) — 架构分析（内部）

## 开源许可

[MIT](LICENSE)

## 致谢

- [go-music-dl](https://github.com/guohuiyuan/go-music-dl) — 底层音乐搜索下载引擎
