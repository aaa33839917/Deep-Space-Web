#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协议页渲染 —— **唯一实现**（render-legal.py 写文件 / check-legal.py 查漂移都用它）

单一真源：项目根 `法律文本/服务条款-草案.md` 与 `法律文本/隐私政策-草案.md`
（**只读**；站里一个字都不许手改 —— 手改就会出现"线上条款与源稿两个说法"）。

支持的 markdown 子集（**就是这两份源稿实际用到的**，不多做）：
  `# ` 标题（用作页面标题，会吃掉尾部「（草案 vX.Y）」并在报告里说明）
  行首 `> ` 引用块（开头那一块是**元信息**：状态 / 版本 / 更新时间 / 生效日期）
  `## ` 二级标题（生成锚点 id="sec-N"）
  有序 / 无序列表、多行续行（缩进续行并入上一条）
  行首 `①`–`⑳` 的条目（源稿用它当序号，渲染成列表，否则会被拼成一整段）
  表格（含分隔行）、`---` 分隔线
  行内：`**粗体**`、`` `代码` ``、`[文字](目标)`
  整行加粗（`**…**` 独占一行）⇒ 当作小标题段落（源稿用它当"每条数据的名字"）

★ 链接改写（只改"指向哪"，不改文字）：
   `隐私政策-草案.md` → 站点 `/privacy/`；`服务条款-草案.md` → 站点 `/terms/`
   `README.md` → **不做成链接**（那是内部文档、从不发布；做成链接必然 404），
                 只渲染成 `<code>README.md</code>`，**可见文字一字不动**。
"""
import hashlib
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOCS = [
    {
        "page": "terms/index.html",
        "src": os.path.join("..", "法律文本", "服务条款-草案.md"),
        "title": "服务条款 · 深空",
        "peer_page": "privacy/index.html",
    },
    {
        "page": "privacy/index.html",
        "src": os.path.join("..", "法律文本", "隐私政策-草案.md"),
        "title": "隐私政策 · 深空",
        "peer_page": "terms/index.html",
    },
]

# 站点里这两个目标的相对链接（由 os.path.relpath 按真实层级算）
SITE_TARGETS = {
    "服务条款-草案.md": "terms",
    "隐私政策-草案.md": "privacy",
}
UNPUBLISHED = ("README.md",)          # 内部文档：保留文字，不做成链接

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
CJK_TAIL = "，。；：、）】》」』…！？%,.;:)]}"


# --------------------------------------------------------------------------
#  行内
# --------------------------------------------------------------------------
def _rel_dir(page):
    d = os.path.dirname(page)
    return d if d else "."


def _link_url(target, page):
    """把源稿里的链接目标翻译成站点上的链接；返回 None = 不做成链接。"""
    t = target.strip()
    if t.startswith(("http://", "https://", "mailto:")):
        return t
    base = os.path.basename(t)
    if base in UNPUBLISHED:
        return None
    if base in SITE_TARGETS:
        rel = os.path.relpath(SITE_TARGETS[base], _rel_dir(page))
        return rel.replace(os.sep, "/") + "/"
    return None


def inline(s, page, warn):
    """行内 markdown → HTML。先转义，再用占位符保护 code / link，最后还原。"""
    out = html.escape(s, quote=False)
    stash = []

    def keep(frag):
        stash.append(frag)
        return "\x00%d\x00" % (len(stash) - 1)

    out = re.sub(r"`([^`]+)`", lambda m: keep("<code>%s</code>" % m.group(1)), out)

    def _link(m):
        text, target = m.group(1), m.group(2)
        url = _link_url(target, page)
        if url is None:
            warn.add(os.path.basename(target.strip()))
            return text                                   # 文字保留，只是不成链接
        return keep('<a href="%s">%s</a>' % (html.escape(url, quote=True), text))

    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", out)
    out = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], out)
    return out


# --------------------------------------------------------------------------
#  块
# --------------------------------------------------------------------------
def _join(lines):
    """把软换行的几行拼成一段（中文行尾不补空格，西文行尾补一个）。"""
    buf = ""
    for ln in lines:
        ln = ln.strip()
        if not buf:
            buf = ln
        elif buf[-1] in CJK_TAIL or (ln[:1] and ord(ln[0]) > 0x2E80):
            buf += ln
        else:
            buf += " " + ln
    return buf


def _table(rows, page, warn):
    def cells(line):
        s = line.strip().strip("|")
        return [c.strip() for c in s.split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ["<table>", "<thead><tr>"]
    out += ["<th>%s</th>" % inline(c, page, warn) for c in head]
    out += ["</tr></thead>", "<tbody>"]
    for r in body:
        out.append("<tr>" + "".join("<td>%s</td>" % inline(c, page, warn) for c in r) + "</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def _is_table_sep(line):
    return bool(re.match(r"^\|[\s:|-]+\|$", line.strip()))


def _list_block(lines, i, pattern):
    """解析一个列表块 → (items, next_i)。

    续行（缩进行）并入**上一条**——源稿里 `2. …` 的说明就是这样换行的
    （见服务条款 §五 第 2 条）。⚠️ 第一版这里写错了：每次遇到新条目先塞一个空串，
    于是每个列表里都冒出 `<li></li>`；改成"只在真有续行时并入上一项"。
    """
    items = []
    while i < len(lines):
        cur = lines[i]
        m = re.match(pattern, cur.strip())
        if m:
            items.append(m.group(1))
            i += 1
            continue
        if items and cur.strip() and (cur.startswith("  ") or cur.startswith("\t")):
            items[-1] = _join([items[-1], cur])
            i += 1
            continue
        break
    return items, i


def render_body(md, page, warn):
    lines = md.split("\n")
    out = []
    i = 0
    n_sec = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        s = line.strip()

        if not s:
            i += 1
            continue

        if s == "---":
            out.append("<hr>")
            i += 1
            continue

        if s.startswith("## "):
            n_sec += 1
            out.append('<h2 id="sec-%d">%s</h2>' % (n_sec, inline(s[3:], page, warn)))
            i += 1
            continue

        if s.startswith("|") and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows, page, warn))
            continue

        if s.startswith("> "):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner, buf = [], []
            for b in block:
                if b.strip():
                    buf.append(b)
                elif buf:
                    inner.append(_join(buf)); buf = []
            if buf:
                inner.append(_join(buf))
            out.append("<blockquote>%s</blockquote>" %
                       "".join("<p>%s</p>" % inline(p, page, warn) for p in inner))
            continue

        if re.match(r"^[-*]\s+", s):
            items, i = _list_block(lines, i, r"^[-*]\s+(.*)$")
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(x, page, warn) for x in items))
            continue

        if re.match(r"^\d+\.\s+", s):
            items, i = _list_block(lines, i, r"^\d+\.\s+(.*)$")
            out.append("<ol>%s</ol>" % "".join("<li>%s</li>" % inline(x, page, warn) for x in items))
            continue

        if s[0] in CIRCLED:
            items = []
            # ⚠️ 条件必须**先判非空**：`"" in "①②③"` 恒为 True（空串是任何串的子串），
            #    第一版写成 `lines[i].strip()[:1] in CIRCLED` ⇒ 空行被当成一个空条目，
            #    列表末尾多出一个 `<li></li>`。
            while i < len(lines) and lines[i].strip() and lines[i].strip()[0] in CIRCLED:
                items.append(lines[i].strip())
                i += 1
            out.append('<ul class="legal-circled">%s</ul>' %
                       "".join("<li>%s</li>" % inline(x, page, warn) for x in items))
            continue

        # 整行加粗 ⇒ 小标题段落（源稿用它当"每条数据的名字"）
        if re.match(r"^\*\*[^*]+\*\*$", s):
            out.append('<p class="legal-h">%s</p>' % inline(s, page, warn))
            i += 1
            continue

        # 普通段落：把连续的软换行拼起来
        buf = []
        while i < len(lines):
            cur = lines[i]
            cs = cur.strip()
            if (not cs or cs == "---" or cs.startswith(("## ", "> ", "|", "- ", "* ")) or
                    re.match(r"^\d+\.\s", cs) or cs[:1] in CIRCLED or re.match(r"^\*\*[^*]+\*\*$", cs)):
                break
            buf.append(cur)
            i += 1
        out.append("<p>%s</p>" % inline(_join(buf), page, warn))

    return "\n".join(out), n_sec


# --------------------------------------------------------------------------
#  源稿 → 页面
# --------------------------------------------------------------------------
def read_source(doc):
    path = os.path.join(ROOT, doc["src"])
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")

    title = ""
    title_note = ""
    i = 0
    while i < len(lines):
        if lines[i].startswith("# "):
            raw_title = lines[i][2:].strip()
            title = re.sub(r"[（(]草案\s*v[\d.]+[)）]\s*$", "", raw_title).strip()
            if title != raw_title:
                title_note = ("源稿 H1 仍写「%s」⇒ 页面标题去掉了「（草案 vX.Y）」后缀"
                              "（源稿不在官网写范围，未改）" % raw_title)
            i += 1
            break
        i += 1

    status, version, notes = "", "", []
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip().startswith(">"):
        while i < len(lines) and lines[i].strip().startswith(">"):
            b = re.sub(r"^\s*>\s?", "", lines[i]).strip()
            if b.startswith("**状态："):
                status = b
            elif b.startswith("版本："):
                version = b
            elif b:
                notes.append(b)
            i += 1

    # 跳过紧跟的分隔线
    while i < len(lines) and (not lines[i].strip() or lines[i].strip() == "---"):
        i += 1
    body_md = "\n".join(lines[i:])
    return {
        "title_zh": title,
        "title_note": title_note,
        "status": status,
        "version": version,
        "notes": notes,
        "body_md": body_md,
        "src_path": doc["src"],
        "src_sha": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


PAGE_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<title>{title}</title>
<meta name="theme-color" content="#2B2B2B">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>

<header class="topbar">
  <a class="topbar__logo" href="../"><img src="../assets/mark-white.svg" alt="" width="26" height="26">深空</a>
  <nav class="topbar__links">
<!-- NAV:START -->
<!-- NAV:END -->
  </nav>
</header>

<div class="wrap narrow">

  <h1 class="page-title">{name}</h1>
  <p class="legal-meta">{version}</p>
{status_block}{notes}
  <div class="card legal">

<!-- LEGAL:START -->
<!-- 本页正文由构建流程生成，请勿手改；需要改动请在源稿侧进行并重新构建。 -->
{body}
<!-- LEGAL:END -->

  </div>

</div>

<footer class="foot">
  深空联机工具　|　<a href="../thanks/">鸣谢</a><br>
  本页为静态页面，不收集任何信息。
<!-- FOOTER:START -->
<!-- FOOTER:END -->
</footer>

</body>
</html>
"""


def build(doc):
    warn = set()
    info = read_source(doc)
    body, n_sec = render_body(info["body_md"], doc["page"], warn)
    notes = ""
    if info["notes"]:
        notes = ('  <div class="legal-note">%s</div>\n' %
                 "".join("<p>%s</p>" % inline(t, doc["page"], warn) for t in info["notes"]))
    # 状态行只在源稿**确实有**时渲染（v1.1 源稿已把"状态：已定稿（服主…拍定）"搬去不发布的内部文件；
    # 那时若还照模板输出，页面上会留一个空的 <p class="legal-status"></p>）
    status_block = ('  <p class="legal-status">%s</p>\n' % inline(info["status"], doc["page"], warn)
                    if info["status"].strip() else "")
    page_html = PAGE_HEAD.format(
        title=html.escape(doc["title"], quote=True),
        name=html.escape(info["title_zh"]),
        version=inline(info["version"], doc["page"], warn),
        status_block=status_block,
        notes=notes,
        body=body,
    )
    return page_html, {"sec": n_sec, "src_sha": info["src_sha"],
                       "version": info["version"], "status": info["status"],
                       "title": info["title_zh"], "title_note": info["title_note"],
                       "dropped_links": sorted(warn)}


def norm_for_gate(s):
    """把**别的生成器**合法写进去的东西抹掉，才能跟"刚渲染出来的"逐字节比。

    只抹这五类，每一类都能指名是**哪个脚本**负责的：
      ① `<meta name="dsv" …>` / ② `<script src="…cache-check.js">` → deploy.sh 2d
      ③ `?v=<8位hex>` 指纹                                       → deploy.sh 2b
      ④ `<!-- NAV:START -->…<!-- NAV:END -->`                   → sync-nav.py
      ⑤ `<!-- FOOTER:START -->…<!-- FOOTER:END -->`              → sync-footer.py
    ⚠️ 第一版忘了抹 ④⑤，于是"刚渲染的（页脚还是空标记）"与"盘上已填过页脚的"必然不等 ⇒
       自己把自己判红（假阳性）。判据错一次就够了：这里把每个掩码都标上它的负责人。
    """
    s = re.sub(r'<meta name="dsv" content="[^"]*">\n?', "", s)
    s = re.sub(r'<script src="[^"]*assets/cache-check\.js[^"]*"></script>\n?', "", s)
    s = re.sub(r"\?v=[0-9a-f]{8}", "", s)
    s = re.sub(r"<!-- NAV:START -->.*?<!-- NAV:END -->", "<!-- NAV -->", s, flags=re.S)
    s = re.sub(r"<!-- FOOTER:START -->.*?<!-- FOOTER:END -->", "<!-- FOOTER -->", s, flags=re.S)
    return s


def legal_region(s):
    """取 `<!-- LEGAL:START -->…<!-- LEGAL:END -->` 之间的字节（deploy.sh 从不碰这块）。"""
    m = re.search(r"<!-- LEGAL:START -->(.*?)<!-- LEGAL:END -->", s, re.S)
    return m.group(1) if m else None
