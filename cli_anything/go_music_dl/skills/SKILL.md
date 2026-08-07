---
name: go-music-dl-cli
description: 用 cli-anything-go-music-dl 命令行工具帮用户下载/管理音乐。当用户要求下载歌曲、搜索音乐、下歌词/封面、管理下载目录、删除歌曲、查询下载记录、配置音源或 Cookie、解析歌单/专辑链接时使用。这是操纵 go-music-dl 软件（GUI 版 music-dl-desktop-go.exe 或其他暴露 Web API 的版本）的唯一命令行入口。
---

# go-music-dl CLI 使用指南

`cli-anything-go-music-dl` 是 go-music-dl（聚合音乐搜索下载工具）的命令行封装，
通过 HTTP API 操纵真实软件后端（桌面版/Web 版）。**所有功能通过它完成，无需
读源码。** 每条命令都可带全局选项 `--server`（后端地址）和 `--json`（机器可读输出）。

## ⚠ 最重要：操作前必须先确保软件在运行

**CLI 是遥控器，软件是真正干活的引擎。软件不启动，任何操作都会失败。**

**Agent 标准动作（每次开始任务前必做）：**

1. **探测后端是否在运行**：
   ```bash
   cli-anything-go-music-dl server
   ```
   - 返回 `ok: true` 且有 base_url → 软件在运行，直接开始任务
   - 报"找不到后端" → 执行下一步

2. **软件不在运行 → 启动它**：
   - **如果已经配过 exe 路径**（之前用过 `server --exe`），CLI 会自动静默启动软件，
     等几秒后重新探测即可：
     ```bash
     sleep 5
     cli-anything-go-music-dl server
     ```
   - **如果知道软件 exe 路径**（如 `D:\go music\music-dl-desktop-go.exe`）：
     用 `server --exe` 告诉 CLI，它会记住并自动启动（推荐，一劳永逸）：
     ```bash
     cli-anything-go-music-dl server --exe "D:\go music\music-dl-desktop-go.exe"
     ```
     此命令会：记住 exe 位置 → 自动后台静默启动软件（无 GUI 窗口）→ 等待就绪 → 返回连接成功。
   - **如果不知道软件 exe 在哪 → 必须询问人类用户**，不要乱猜路径：
     > "go-music-dl 软件没有在运行。请问它的 .exe 文件（music-dl-desktop-go.exe）
     > 在哪个目录？"

3. **等待软件就绪后确认**（启动后等几秒再探测）：
   ```bash
   sleep 5
   cli-anything-go-music-dl server
   ```

**记住**：软件是硬依赖。用户装了软件、用户知道 exe 在哪，Agent 不知道时必须问。
这是操作前第一件事，顺序不能乱。

## 初次使用（第一次拿到包时）

```bash
# 1. 安装（在 agent-harness 目录）
cd <包所在目录>/agent-harness
pip install -e .

# 2. 验证安装成功
cli-anything-go-music-dl --version

# 3. 确认后端在运行（软件已启动则自动探测）
cli-anything-go-music-dl server
# 探测不到时手动指定：
cli-anything-go-music-dl --server http://127.0.0.1:37777 server
# server 输出里有 base_url 和下载目录即说明连接成功

# 4. 指定下载目录（目录必须已存在；指定一次后永久记住）
cli-anything-go-music-dl download --keyword "测试" --stream --dir "D:\go music\data\downloads"
```

**初始化三步**：装包 → server 确认后端 → 用 --dir 指定一次下载位置。
之后 Agent 就能直接下歌，无需再指定目录。

## 全局选项（放在子命令前）

| 选项 | 说明 |
|------|------|
| `--server <url>` | 后端地址，缺省自动探测（桌面版 18901/37777 等端口） |
| `--json` | JSON 输出，供脚本/AI 消费 |

## 核心工作流

### 1. 搜索（先搜索拿 ID，再下载）

**搜索策略（先判断是否知道音源，再决定传不传参数）：**

- **知道歌曲在哪个音源**（如网易云独有/用户指定）→ 传入音源名，只搜它，快且准：
  ```bash
  cli-anything-go-music-dl search "歌名" --sources netease --limit 10
  cli-anything-go-music-dl search "歌名" --sources qq,kugou --limit 10   # 多个源
  ```
- **不知道音源** → **不要传 --sources**，让软件用全部 12+1 个源聚合搜索，
  能从结果里看到各源都找到了什么版本，再挑最优：
  ```bash
  cli-anything-go-music-dl search "歌名 歌手" --limit 20
  ```
- **搜索不到时**：尝试加歌手名、换关键词写法（简体/繁体/日文原版名）、或
  分源逐一试 `--sources kugou` / `--sources kuwo` 等

支持音源名：`netease`（网易云）、`qq`（QQ音乐）、`kugou`（酷狗）、`kuwo`（酷我）、
`migu`（咪咕）、`qianqian`（千千）、`soda`（汽水）、`fivesing`、`jamendo`、`joox`、
`bilibili`、`apple`、`local`（本地）。

```bash
# JSON 输出拿结构化结果（含 id/source/name/artist）
cli-anything-go-music-dl --json search "歌名" --limit 5
```

搜索结果形如 `[0] 歌手 - 歌名 [音源] (ID)`。**用 --json 拿 ID 最可靠。**

### 2. 探测音质（下载前必做）

```bash
cli-anything-go-music-dl --json inspect <歌曲ID> <音源>
# 返回 {"valid": true/false, "size": "5.6 MB", "url": "..."}
# valid=false 说明该源下不了（需会员/失效/临时故障），换源重试
```

**音源建议（踩坑总结）**：同一首歌不同源可用性差异巨大：
- **kuwo（酷我）通常最稳**，无需登录即可下载完整版
- netease（网易云）免费歌可下，但**高频访问会被限流**（搜索返回空/下载 502），等一会再试
- qq（QQ音乐）**无 Cookie 只能拿 0.2MB 试听版**（URL 前缀 M500、`uin=` 为空即未登录）
- kugou（酷狗）部分歌 404/502，不稳定，换别的版本（同一首歌有多个条目）试
- migu（咪咕）/soda（汽水）很多歌 **仅会员**（inspect 返回 valid=false）
- 探测失败不代表没有，**多试几个源**再放弃

**换源重试顺序**：`kuwo → kugou → netease → migu → qq → 其他`

### 3. 下载（记忆目录机制）

```bash
# 指定下载目录（目录必须存在，否则报错；指定后永久记住）
cli-anything-go-music-dl download --id <ID> --source <SRC> --name "歌名" --artist "歌手" --stream --dir "D:\go music\data\downloads"

# 之后不指定 --dir，自动用上次记住的目录
cli-anything-go-music-dl download --id <ID> --source <SRC> --name "歌名" --artist "歌手" --stream

# 按关键词直接下载搜索第一条
cli-anything-go-music-dl download --keyword "歌名" --index 0 --stream
```

**下载位置规则**：
- `--dir` 指定 → 校验目录存在（**不存在则报错，不会自动创建**）→ 记住该目录
- 不指定 → 用记住的目录 → 无记忆则扫描默认位置 → 都无则报错要求 `--dir`
- 记忆存用户配置目录 `~/.config/cli-anything-go-music-dl/config.json`，
  **换目录/换项目后仍生效**

**⚠ 重要（踩坑）**：不加 `--stream` 时是 **save_local 模式**，文件由软件保存到
软件配置的下载目录（相对路径，实际在软件进程工作目录下），**不在你指定的 --dir**。
要下载到指定目录必须加 `--stream`。

### 4. 歌词 / 封面

```bash
cli-anything-go-music-dl lyrics --id <ID> --source <SRC> --dir <目录>
cli-anything-go-music-dl cover  --id <ID> --source <SRC> --dir <目录>
```

### 5. 歌单 / 专辑 / 链接解析

```bash
cli-anything-go-music-dl playlist-detail <歌单ID> <音源>   # 歌单内歌曲
cli-anything-go-music-dl album-detail <专辑ID> <音源>      # 专辑内歌曲
cli-anything-go-music-dl parse-link <音乐链接URL>          # 解析单曲/歌单/专辑链接
```

链接解析走后端接口，能识别网易云/QQ/汽水等平台的歌单/专辑/单曲链接。

### 6. 删除（不可撤销，危险操作）

```bash
cli-anything-go-music-dl delete --dir <目录>              # 列出下载目录文件（先看再删）
cli-anything-go-music-dl delete --name "歌名" --artist "歌手" --dir <目录> --yes   # 删指定歌曲
cli-anything-go-music-dl delete --local-id <ID> --yes     # 删本地音乐（后端）
cli-anything-go-music-dl delete --collection <ID> --yes   # 删歌单
```

**⚠ 删除安全（血泪教训）**：
- `--artist` 是**精确匹配**整个歌手字段，`--name` 是歌名模糊匹配
- **删除前必须先 `delete --dir` 列出文件，确认要删的文件名与歌手字段完全对应**
- 反例：`--artist 黄诗扶` 会匹配歌手字段**恰好等于**"黄诗扶"的文件；
  若字段是"恋恋故人难、黄诗扶、王敬轩（妖扬）"，则需传完整字段才匹配，
  传"黄诗扶"是删不到它的（安全），但传错字段也可能误删同字段多文件——务必先列表

### 7. 管理

```bash
cli-anything-go-music-dl records                       # 下载记录
cli-anything-go-music-dl settings                      # 查看设置
cli-anything-go-music-dl settings-set --key downloadConcurrency --value 5   # 改设置
cli-anything-go-music-dl cookies                       # 查看各源 Cookie
cli-anything-go-music-dl cookies-set --key qq --value "cookie"   # 配 Cookie（解锁高音质/会员）
cli-anything-go-music-dl local                         # 本地音乐
cli-anything-go-music-dl collections                   # 我的歌单
```

## 踩坑记录（全部踩过，别再来一次）

1. **`--json` 是全局选项，必须放子命令前**：`cli-anything-go-music-dl --json search "xx"` ✓
   `cli-anything-go-music-dl search "xx" --json` ✗（会报 No such option）
2. **下载到指定目录必须加 `--stream`**，否则走 save_local 存到软件目录（见上文）
3. **QQ 无 Cookie 只有 0.2MB 试听版**：URL 含 `M500`、`uin=` 为空即未登录；
   要完整版需 `cookies-set --key qq --value "<cookie>"` 或用其他源
4. **网易云/QQ 会被限流**：搜索空结果、下载 502 都是临时现象，**等一下重试**或换源
5. **下载目录必须已存在**：`--dir` 指向不存在目录会报错，先 mkdir 再用
6. **save_local 下载的文件在软件进程工作目录下**（不在你的 cwd），路径是相对的，
   配合 `server --json` 的 `download_dir` 理解实际位置
7. **inspect 返回的 url 是带时效签名的直链**，几十分钟后失效属正常
8. **Windows 终端中文乱码**：CMD 默认 GBK，运行命令前设 `PYTHONIOENCODING=utf-8`
   或改用 PowerShell/Windows Terminal；乱码是显示问题，文件本身无损
9. **多个同名歌曲**：搜索"歌名"可能返回翻唱/混音/DJ版，注意认歌手和版本，
   原版往往在结果靠后位置，用 `--json` 看清 artist 再选
10. **汽水/咪咕仅会员歌**：inspect valid=false 不代表坏，是该歌 VIP 限制
11. **`--server` 传裸地址**（`http://127.0.0.1:37777`）会自动补 `/music` 前缀；
    自动探测时优先 18901/37777，若连的是别的实例需手动 `--server`
12. **CLI 不是重实现**：它调的是真实软件的 HTTP API，软件没启动就报"找不到后端"，
    请先启动桌面版/Web 版
13. **自动启动软件**：`server --exe <exe路径>` 会记住软件位置并自动后台启动；
    配过一次后，以后软件没运行时 CLI 会自动拉起，无需手动开软件
14. **exe 路径只在配置里记一次**：换机器/换软件位置后需要重新 `server --exe` 配置

## Agent 使用要点

1. **每步用 `--json`** 拿稳定结构，不要解析人类表格
2. **搜索 → inspect → download** 三步走，inspect 确认 valid 再下载
3. **音源失效很正常**（平台限流/需会员），换源重试，不要放弃
4. **下载目录记忆**：第一次用 `--dir` 指定后，后续默认沿用，除非用户要求改
5. **删除前必须列目录确认**，防止误删
6. **`--help` 随时可用**：`cli-anything-go-music-dl <命令> --help` 看具体参数
7. **音质优先策略**：同一首歌多个源都有时，inspect 后选 size 最大的（通常音质最好）

## 常见问题速查

- **后端找不到**：确认桌面版/Web 版在运行，或用 `--server http://127.0.0.1:<端口>` 指定；
  或首次用 `server --exe <exe路径>` 让 CLI 记住并自动启动软件
- **下载 502/404**：该源临时失效或需会员，换 `--source kuwo` 等重试
- **`--dir` 报目录不存在**：先创建目录或用已存在的
- **VIP 歌下不了**：需对应平台 Cookie（`cookies-set`），无 Cookie 只能试其他源
- **搜索空结果**：限流或关键词问题，加歌手名/换写法/分源重试
