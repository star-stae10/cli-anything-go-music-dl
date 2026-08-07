"""repl_skin.py — 统一的 REPL 界面皮肤（轻量无依赖实现）。

提供 banner / prompt / help / 成功 / 错误 / 警告 / 信息 / 状态 / 表格 输出。
不依赖 prompt_toolkit；REPL 用内置 input()。
"""

from __future__ import annotations

import os
import sys

# Windows 控制台默认 GBK 无法输出 ✓/⚠ 等符号，强制 UTF-8
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass

from typing import Any, Dict, Iterable, List, Optional

try:
    from colorama import init, Fore, Style

    init()
    _COLOR = True
except ImportError:  # pragma: no cover
    _COLOR = False

    class _Fake:
        def __getattr__(self, _):
            return ""

    Fore = _Fake()
    Style = _Fake()


class ReplSkin:
    """REPL 界面皮肤。"""

    def __init__(self, name: str, version: str = "1.0.0", skill_path: str = ""):
        self.name = name
        self.version = version
        self.skill_path = skill_path

    def print_banner(self) -> None:
        border = "=" * 58
        print(border)
        print(f"  {self.name} CLI  v{self.version}")
        print("  在 cli-anything 体系下通过真实 go-music-dl 后端操作")
        print(border)
        if self.skill_path:
            print(f"  Skill: {self.skill_path}")
            print(border)

    def create_prompt_session(self):  # pragma: no cover - 无依赖
        return None

    def get_input(self, _session=None, project_name: str = "", modified: bool = False) -> str:
        prefix = "music"
        if project_name:
            prefix += f"[{project_name}]"
            if modified:
                prefix += "*"
        try:
            return input(f"{prefix}> ").strip()
        except (EOFError, KeyboardInterrupt):
            return "exit"

    def help(self, commands: Dict[str, str]) -> None:
        print("可用命令：")
        for cmd, desc in commands.items():
            print(f"  {cmd:<28} {desc}")

    def success(self, message: str) -> None:
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

    def error(self, message: str) -> None:
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

    def warning(self, message: str) -> None:
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

    def info(self, message: str) -> None:
        print(f"{Fore.CYAN}● {message}{Style.RESET_ALL}")

    def status(self, key: str, value: Any) -> None:
        print(f"  {key:<22} {value}")

    def table(self, headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
        headers = list(headers)
        rows = [list(r) for r in rows]
        widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(cell)))
        header_line = "  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
        print(header_line)
        print("  " + "  ".join("-" * w for w in widths))
        for row in rows:
            line = "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row))
            print(line)

    def progress(self, done: int, total: int, label: str = "") -> None:
        pct = (done / total * 100) if total else 0
        bar_len = 20
        filled = int(bar_len * done / total) if total else bar_len
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"\r  [{bar}] {pct:5.1f}% {label}", end="", flush=True)
        if done >= total:
            print()

    def print_goodbye(self) -> None:
        print(f"\n{Fore.CYAN}再见，感谢使用 {self.name} CLI。{Style.RESET_ALL}")
