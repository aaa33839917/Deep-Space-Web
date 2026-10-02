#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「卡片信息」的读写 —— 全站唯一的数据来源。

★ 设计原则（用户 2026-09-29 定的）：
   **没有配置文件。** 每个项目的卡片信息就写在它自己的详情页里。
   谁都不会和谁冲突，因为只有一份。

判定规则：
   · 一个目录下有 index.html，且里面有 CARD-META 块 ⇒ **它是一个项目**
   · 没有这个块 ⇒ 只是个普通页面（比如 products/ 和 thanks/），不是项目
   · 块里的 "visible": false ⇒ **隐藏**：详情页照常上传，只是不出现在
     产品页和首页上（仍然可以靠 URL 直接访问）
"""
import json
import os
import re

MARK_A = "<!-- CARD-META:START -->"
MARK_B = "<!-- CARD-META:END -->"

SCRIPT_RE = re.compile(
    r'<script\s+type="application/json"\s+data-card-meta\s*>(.*?)</script>',
    re.S,
)

# 卡片信息的字段与默认值（新增项目时按这个填）
FIELDS = {
    "order": 99,
    "visible": True,
    "name": "",
    "en": "",
    "href": "",
    "desc": "",
    "tags": [],
    "cta": "了解更多 →",
    "home_desc": "",
    "about": "",
}


def read_meta(page_path):
    """从页面里读出卡片信息；没有就返回 None。"""
    try:
        s = open(page_path, encoding="utf-8").read()
    except OSError:
        return None
    m = SCRIPT_RE.search(s)
    if not m:
        return None
    try:
        meta = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(meta, dict):
        return None
    return meta


def write_meta(page_path, meta):
    """把卡片信息写回页面。没有标记就插在 <body> 之后。"""
    # 只保留已知字段，缺的补默认值（免得页面上留着一堆没用的键）
    clean = {k: meta.get(k, default) for k, default in FIELDS.items()}
    meta = clean
    block = (MARK_A + "\n"
             '<script type="application/json" data-card-meta>\n'
             + json.dumps(meta, ensure_ascii=False, indent=2)
             + "\n</script>\n" + MARK_B)
    s = open(page_path, encoding="utf-8").read()
    if MARK_A in s and MARK_B in s:
        s = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B),
                   lambda m: block, s, flags=re.S)
    else:
        s, n = re.subn(r"(<body>\n)", lambda m: m.group(1) + "\n" + block + "\n",
                       s, count=1)
        if n != 1:
            raise RuntimeError("插不进去：%s 里找不到 <body>" % page_path)
    open(page_path, "w", encoding="utf-8").write(s)


def remove_meta(page_path):
    """把卡片信息块摘掉 —— 这个页面就不再是「项目」了（页面本身不删）。"""
    s = open(page_path, encoding="utf-8").read()
    if MARK_A not in s:
        return False
    s = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B), "", s, flags=re.S)
    s = re.sub(r"\n{3,}", "\n\n", s)
    open(page_path, "w", encoding="utf-8").write(s)
    return True


def validate_meta(meta, pid, allids):
    """校验卡片信息。★ 2026-10-02：从 `_admin/server.py` 挪到这里 ——
    控制台（DeepSpaceConsole）也要用它写卡片，规则**必须只有一处**，
    否则迟早出现"后台放行、控制台拦下"这种两套真相。
    返回 None 表示通过，否则返回一句人能看懂的错误。"""
    if not isinstance(meta, dict):
        return "数据格式不对"
    if not str(meta.get("name", "")).strip():
        return "名称不能为空"
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", pid or ""):
        return "id 只能用字母 / 数字 / 下划线 / 连字符"
    if pid in allids:
        return "id「%s」已经被另一个项目占用" % pid
    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        return "标签必须是数组"
    for t in tags:
        if not isinstance(t, dict):
            return "标签格式不对"
        if t.get("kind", "") not in ("", "live", "dev"):
            return "标签类型只能是 普通/已开放/开发中"
    try:
        int(meta.get("order", 99))
    except (TypeError, ValueError):
        return "排序值必须是整数"
    return None


def scan(root, skip=("products",)):
    """扫出全站所有项目。返回 [{id, dir, page, meta}, ...]，按 order 排序。"""
    out = []
    for name in sorted(os.listdir(root)):
        if name.startswith((".", "_")) or name in skip:
            continue
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        page = os.path.join(d, "index.html")
        if not os.path.exists(page):
            continue
        meta = read_meta(page)
        if meta is None:
            continue
        meta.setdefault("href", name + "/")
        out.append({"id": name, "dir": d, "page": page, "meta": meta})
    out.sort(key=lambda x: (x["meta"].get("order", 999), x["id"]))
    return out
