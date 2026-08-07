# 发布指南

本项目的发布流程：改代码 → 构建 → 发 PyPI → 打 tag → 发 GitHub Release。

## 前置准备

```bash
pip install build twine
```

PyPI 认证通过 `~/.pypirc` 配置（`username = __token__`，`password = pypi-xxx`），
或使用环境变量 `TWINE_USERNAME=__token__` + `TWINE_PASSWORD=pypi-xxx`。

## 发布步骤

### 1. 更新版本号

改两处，保持一致：

- `pyproject.toml` → `[project] version = "X.Y.Z"`
- `cli_anything/go_music_dl/__init__.py` → `__version__ = "X.Y.Z"`

版本规则建议遵循 [语义化版本](https://semver.org/lang/zh-CN/)：修复 `1.0.1`、新功能 `1.1.0`、破坏性 `2.0.0`。

### 2. 构建

```bash
rm -rf dist build *.egg-info
python -m build
```

产物在 `dist/`：`.whl`（预编译轮子）+ `.tar.gz`（源码包）。

### 3. 校验

```bash
twine check dist/*
```

### 4. 发布到 PyPI

```bash
# 正式发布（走 ~/.pypirc 或环境变量认证）
python -m twine upload dist/*
```

> Windows 终端若遇编码报错，加 `PYTHONIOENCODING=utf-8` 前缀。

### 5. 提交并打 tag

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin master --tags
```

### 6. 发布 GitHub Release

```bash
gh release create vX.Y.Z \
  "dist/<pkg>-X.Y.Z-py3-none-any.whl" \
  "dist/<pkg>-X.Y.Z.tar.gz" \
  --title "vX.Y.Z" \
  --notes "变更说明..."
```

## 发布前自检清单

- [ ] 版本号两处一致
- [ ] 单元测试通过：`pytest cli_anything/go_music_dl/tests/test_core.py`
- [ ] `twine check dist/*` 通过
- [ ] 全新环境安装：`pip install dist/*.whl` 后可导入、命令可用
- [ ] skill（`skills/SKILL.md`）已同步最新内容
- [ ] 包内 README（PyPI 展示）与顶层 README 无过时信息

## 常见问题

- **403 Forbidden 上传失败**：确认 `~/.pypirc` 里 username 是 `__token__`，password 是完整 token（含 `pypi-` 前缀）
- **400 版本已存在**：PyPI 不允许重复版本，需升版本号
- **wheel 里缺文件**：检查 `pyproject.toml` 的 `[tool.setuptools.package-data]` 是否包含 `skills/*.md`
