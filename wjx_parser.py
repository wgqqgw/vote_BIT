from __future__ import annotations

import re


def parse_wjx_ranking_text(text: str) -> list[str]:
    """解析问卷星排序文本：A，单位→B，单位→C，单位 ... 返回姓名顺序。"""
    parts = [p.strip() for p in re.split(r"→|->", text) if p.strip()]
    names: list[str] = []
    for p in parts:
        name = re.split(r"[，,]", p, maxsplit=1)[0].strip()
        if not name:
            raise ValueError(f"无法解析排序项：{p}")
        names.append(name)
    return names
