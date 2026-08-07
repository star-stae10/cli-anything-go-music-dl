---
name: "cli-anything-go-music-dl"
description: "go-music-dl 聚合音乐搜索下载工具的 agent CLI。操作真实 go-music-dl 后端（桌面版/Web 版 HTTP API），支持搜索、探测、下载、歌词、封面、下载记录、设置与 Cookie 管理。全部命令支持 --json 输出供脚本/AI 消费。"
---

# cli-anything-go-music-dl

通过真实 go-music-dl 软件（桌面版 `music-dl-desktop-go.exe` 或 Web 模式
`music-dl web`）的 HTTP API 操作音乐搜索与下载。**CLI 是软件的前端，不重实现
搜索/下载逻辑。**

## 前置条件

- 已运行 go-music-dl 桌面版 / Web 版（内嵌 HTTP 服务）
- CLI 已安装：`pip install -e .`（在 agent-harness 目录）

## 命令语法

```
cli-anything-go-music-dl [--server URL] [--json] <command> [args]
```

`--json` 是全局选项，放在命令前。默认自动探测后端地址。

## 命令组

### server — 后端探测
```
cli-anything-go-music-dl --json server
```

### search — 搜索
```
cli-anything-go-music-dl --json search "关键词" --type song|playlist|album [--sources netease,qq] [--exact-artist 歌手] [--limit N]
```
返回 `{ok, data: {type, songs|playlists, count, items}}`。歌曲项含
`id / source / name / artist / album / duration / cover / extra`。

### inspect — 探测歌曲下载地址
```
cli-anything-go-music-dl --json inspect <song_id> <source>
```
返回 `{ok, data: {valid, url, size, bitrate}}`。URL 是带时效签名的直链。

### download — 下载歌曲
```
# 保存到软件下载目录（默认，自带去重/元数据/文件名模板）
cli-anything-go-music-dl download --keyword "关键词" --index 0
cli-anything-go-music-dl download --id <song_id> --source <src> --name <名> --artist <歌手>

# 流式下载到本地目录
cli-anything-go-music-dl download --id <song_id> --source <src> --stream --dir ./out
```
save_local 模式返回 `{saved, path, filename, skipped}`。

### lyrics / cover — 歌词与封面
```
cli-anything-go-music-dl lyrics --keyword "关键词" --dir ./out
cli-anything-go-music-dl cover  --keyword "关键词" --dir ./out
```
歌词返回 `.lrc`，封面返回 `.jpg`。

### playlist-detail / album-detail / parse-link
```
cli-anything-go-music-dl playlist-detail <playlist_id> <source>
cli-anything-go-music-dl album-detail <album_id> <source>
cli-anything-go-music-dl parse-link <url>
```

### records / settings / cookies / local / collections / delete
```
cli-anything-go-music-dl records --page 1 --page-size 20
cli-anything-go-music-dl records-clear
cli-anything-go-music-dl settings
cli-anything-go-music-dl settings-set --key downloadConcurrency --value 5
cli-anything-go-music-dl cookies
cli-anything-go-music-dl cookies-set --key netease --value "cookie值"
cli-anything-go-music-dl local
cli-anything-go-music-dl collections

# 删除（不可撤销）
cli-anything-go-music-dl delete                          # 列出下载目录
cli-anything-go-music-dl delete --local-id 123 --yes     # 经后端硬删本地音乐
cli-anything-go-music-dl delete --collection 5 --yes     # 删本地歌单
cli-anything-go-music-dl delete --collection 5 --song SID --source netease --yes  # 歌单移除歌曲
cli-anything-go-music-dl delete --name "歌名" --dir ./out --yes                    # 直接删下载文件
```

## AI/脚本使用指引

1. **先探测**：调用 `server --json` 确认后端可用
2. **先搜索再下载**：`search --json` 拿到歌曲 `id/source`，再 `download --id ...`
3. **用 `--json` 解析结果**：所有命令输出稳定 JSON 结构 `{ok, data}` 或 `{ok, error}`
4. **save_local 下载路径是后端相对路径**：结合 `server --json` 的 `download_dir` 拼接
5. **错误处理**：`{ok:false, error:"..."}`；后端未启动时 error 含启动指引

## 示例

```bash
cli-anything-go-music-dl --json search "周杰伦" --sources netease --limit 3
cli-anything-go-music-dl download --keyword "屋顶" --index 0
```
