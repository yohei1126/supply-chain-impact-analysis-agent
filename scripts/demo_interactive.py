from __future__ import annotations

import os
import sys
from pprint import pprint
from typing import Any


def interactive_enabled() -> bool:
    """Pause for input only on a TTY when DEMO_NONINTERACTIVE is unset."""
    if os.getenv("DEMO_NONINTERACTIVE", "").lower() in ("1", "true", "yes"):
        return False
    return sys.stdin.isatty()


def section(title: str, *, intro: str = "") -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)
    if intro:
        print(intro)


def explain(text: str) -> None:
    for line in text.strip().splitlines():
        print(f"  -> {line}")


def wait(prompt: str = "Press Enter to continue") -> None:
    if not interactive_enabled():
        return
    try:
        input(f"\n{prompt}... ")
    except EOFError:
        print()


def prompt(label: str, default: str) -> str:
    if not interactive_enabled():
        return default
    try:
        raw = input(f"{label} [{default}]: ").strip()
    except EOFError:
        return default
    return raw or default


def show(title: str, data: Any, *, commentary: str) -> None:
    print(f"\n--- {title} ---")
    pprint(data)
    explain(commentary)
