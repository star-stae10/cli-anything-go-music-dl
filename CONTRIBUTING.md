# 贡献指南

感谢你对 cli-anything-go-music-dl 感兴趣！任何形式的贡献都欢迎：提 bug、加功能、
改文档、写测试。

## 开发环境

```bash
git clone https://github.com/star-stae10/cli-anything-go-music-dl.git
cd cli-anything-go-music-dl
python -m pip install -e . pytest
```

运行测试：

```bash
# 单元测试（无外部依赖，CI 用）
python -m pytest cli_anything/go_music_dl/tests/test_core.py -v

# 全部测试（含真实后端 E2E，需要本机运行 go-music-dl 软件）
python -m pytest cli_anything/go_music_dl/tests/ -v
```

## 代码结构

```
cli_anything/go_music_dl/
├── go_music_dl_cli.py     # Click CLI 入口 + REPL（命令注册）
├── core/                  # 业务逻辑（song/playlist/settings/delete 等）
├── utils/                 # 后端封装、HTML 解析、目录记忆、REPL 皮肤
└── tests/                 # 单元测试 + E2E 测试
```

## 提交约定

- Commit message 用简洁的中文描述改动，如 `feat: 支持 xxx`、`fix: 修复 xxx`、`docs: 补充 xxx`
- 涉及核心逻辑的改动，请在 PR 里附带对应测试
- 涉及 `skills/SKILL.md` 的改动，需同步 `docs/AGENT_GUIDE.md`

## 提 PR 流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/xxx`
3. 提交改动，跑通测试
4. Push 分支并创建 Pull Request
5. 描述清楚改了什么、为什么改、如何验证

## 发布

见 [RELEASING.md](RELEASING.md)。
