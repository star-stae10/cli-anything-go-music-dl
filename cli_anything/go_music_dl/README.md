# cli-anything-go-music-dl

go-music-dl（聚合音乐搜索下载工具）的 agent 可用 CLI 封装。它作为真实
go-music-dl 软件（桌面版 / Web 版）的命令行前端，通过软件自带的 HTTP API
完成搜索、探测、下载、歌词、封面、记录管理、设置与 Cookie 管理。

## 依赖软件

**go-music-dl 是硬依赖，CLI 不重实现任何搜索/下载逻辑。** 需要以下任一方式运行：

1. **桌面应用**：下载 `music-dl-desktop-go.exe`，双击运行（内嵌 Web 服务监听本机端口）
2. **Web 模式**：`music-dl web --no-browser`（默认端口 8080）
3. **GitHub Release**：https://github.com/guohuiyuan/go-music-dl/releases

## 安装 CLI

```bash
# 从 PyPI 安装（推荐）
pip install cli-anything-go-music-dl

# 或从源码安装
git clone https://github.com/star-stae10/cli-anything-go-music-dl.git
cd cli-anything-go-music-dl
pip install .
```

## 快速开始

```bash
# 1. 连接后端（软件运行中会自动探测；软件未启动时可记住路径并自动拉起）
cli-anything-go-music-dl server --exe "C:\你的路径\music-dl-desktop-go.exe"

# 2. 搜索（JSON 输出，供脚本/AI 消费）
cli-anything-go-music-dl --json search "周杰伦" --type song --sources netease --limit 5

# 3. 探测歌曲下载地址/大小/码率
cli-anything-go-music-dl --json inspect 5257138 netease

# 4. 下载歌曲（--dir 指定目录并记住，之后默认沿用）
cli-anything-go-music-dl download --id 5257138 --source netease --stream --dir ./out

# 5. 下载歌词 / 封面
cli-anything-go-music-dl lyrics --keyword "周杰伦" --dir ./out
cli-anything-go-music-dl cover  --keyword "周杰伦" --dir ./out

# 歌单 / 专辑 / 链接解析
cli-anything-go-music-dl playlist-detail <playlist_id> netease
cli-anything-go-music-dl album-detail <album_id> netease
cli-anything-go-music-dl parse-link "https://music.163.com/#/playlist?id=xxx"

# 下载记录 / 设置 / Cookie
cli-anything-go-music-dl records --page 1 --page-size 20
cli-anything-go-music-dl settings
cli-anything-go-music-dl settings-set --key downloadConcurrency --value 5
cli-anything-go-music-dl cookies

# 删除（不可撤销，需确认或 --yes）
cli-anything-go-music-dl delete                          # 列出下载目录文件
cli-anything-go-music-dl delete --local-id 123           # 经后端 API 硬删本地音乐
cli-anything-go-music-dl delete --collection 5           # 删除整个本地歌单
cli-anything-go-music-dl delete --collection 5 --song SID --source netease   # 歌单移除一首
cli-anything-go-music-dl delete --name "吹梦到西洲" --dir ./out --yes        # 直接删下载文件
cli-anything-go-music-dl delete --file ./out/xxx.mp3 --yes                   # 按路径直接删
```

## 重要特性

- **下载目录记忆**：`download --dir <目录>` 指定一次后，后续下载默认沿用，直到再次指定
- **软件自动启动**：`server --exe <exe路径>` 记住软件位置，检测不到时自动静默拉起
- **Agent 友好**：全部命令 `--json` 输出 + 交互式 REPL + 配套 skill

## REPL 交互模式

不带子命令直接运行进入 REPL：

```bash
cli-anything-go-music-dl
```

REPL 内可用：`search 关键词`、`download --keyword 关键词`、`records`、
`settings`、`cookies`、`local`、`collections`、`help`、`exit`。

## 指定后端

默认自动探测本机运行中的桌面版/Web 版。也可显式指定：

```bash
cli-anything-go-music-dl --server http://127.0.0.1:18901 server
```

## 运行测试

```bash
cd agent-harness/cli_anything/go_music_dl
python -m pytest tests/ -v -s
```

## 命令组概览

| 命令 | 功能 |
|------|------|
| `server` | 探测/连接后端 |
| `search` | 单曲/歌单/专辑搜索 |
| `inspect` | 探测歌曲下载地址/大小/码率 |
| `download` | 下载歌曲（save_local 或流式） |
| `lyrics` / `cover` | 下载歌词 / 封面 |
| `playlist-detail` / `album-detail` | 歌单 / 专辑详情 |
| `parse-link` | 解析单曲/歌单/专辑链接 |
| `records` / `records-clear` | 下载记录查询 / 清空 |
| `settings` / `settings-set` | 查看 / 更新设置 |
| `cookies` / `cookies-set` | 查看 / 设置 Cookie |
| `local` | 本地音乐列表 |
| `collections` | 我的歌单 |
| `delete` | 删除歌曲/歌单/本地下载文件（需确认或 `--yes`） |

所有命令支持 `--json`（全局选项，放在命令前）。
