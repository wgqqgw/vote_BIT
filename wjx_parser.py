from __future__ import annotations

import re


# 问卷星排序列在不同导出/复制场景下，分隔符可能出现多种字符
# 额外覆盖常见竖线字符：┃丨∣ 等
RANK_SEP_PATTERN = r"\s*(?:→|->|➜|➡|⇢|┋|┇|│|┃|丨|｜|∣|\||/|／|;|；)\s*"
# 单个候选项里“姓名”和“单位”之间也可能是多种分隔符
NAME_UNIT_SEP_PATTERN = r"[，,\-—–－]"


def _normalize_name(name: str) -> str:
    # 去掉零宽字符、全角空格、普通空白
    name = name.replace("\u200b", "").replace("\u3000", "")
    name = re.sub(r"\s+", "", name)
    return name.strip()


def parse_wjx_ranking_text(text: str) -> list[str]:
    """解析问卷星排序文本，返回候选人姓名顺序。"""
    text = (text or "").strip()
    if not text:
        return []

    parts = [p.strip() for p in re.split(RANK_SEP_PATTERN, text) if p.strip()]
    names: list[str] = []
    for p in parts:
        # 去掉可能出现的序号前缀，如“1、张三-单位”
        p = re.sub(r"^\s*\d+[\.、)）:]\s*", "", p)
        # 支持“姓名，单位”与“姓名-单位”等形式
        name = re.split(NAME_UNIT_SEP_PATTERN, p, maxsplit=1)[0].strip()
        name = _normalize_name(name)
        if not name:
            raise ValueError(f"无法解析排序项：{p}")
        names.append(name)
    return names
