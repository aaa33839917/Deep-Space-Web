#!/usr/bin/env python3
# =============================================================================
#  下载页两个「下载」按钮的链接同步（2026-10-02 新增）
# -----------------------------------------------------------------------------
#  背景（服主原话）：「我的这个加速器的 Windows 版和安卓版的下载链接，（飞牛）链接
#  有的时候是会变的。我希望能够在官网管理后台加上一个两个链接管理，我还可以编辑那两个
#  下载链接。」
#
#  所以：链接的**唯一真源**是 `_build/download-links.json`；
#     · 官网管理后台的「下载链接」页写它；
#     · 本脚本把它同步进 `accelerator/download/index.html`；
#     · `deploy.sh` 发布前跑本脚本 + `--check`，**页面与配置不一致就不许发**。
#
#  为什么不能直接改 HTML：下载页还有另一条自动同步（`sync-accel-version.py` 改版本号/校验值，
#  发版时跑）。两处都手改必然有一天互相冲掉 —— 把"能变的东西"收进一个文件，才是根治。
#
#  用法:
#     python3 _build/sync-download-links.py            # 同步（幂等）
#     python3 _build/sync-download-links.py --check    # 只校验：页面与配置是否一致（不一致退出 1）
#     python3 _build/sync-download-links.py --dry-run  # 只说会改什么，不落盘
# =============================================================================
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
CONF = os.path.join(HERE, "download-links.json")
PAGE = os.path.join(SITE, "accelerator", "download", "index.html")

# 卡片区间：`<h2>安卓版</h2>` 到下一个 `<h2>`（与 sync-accel-version.py 同一套办法）
def section_bounds(html, label):
    m = re.search(r"<h2>\s*%s\s*</h2>" % re.escape(label), html)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"<h2>", html[start:])
    return (start, start + nxt.start()) if nxt else (start, len(html))


# 卡片里那颗按钮：`<a class="btn" href="…"` —— 只认带 class="btn" 的，不去碰正文里的别的链接
BTN = re.compile(r'(<a\s+class="btn"\s+href=")([^"]*)(")', re.S)


def load_conf(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("❌ 读不了 %s：%s" % (path, e), file=sys.stderr)
        sys.exit(2)
    out = {}
    for key in ("android", "windows"):
        node = d.get(key) or {}
        url = str(node.get("url") or "").strip()
        label = str(node.get("label") or ("安卓版" if key == "android" else "Windows 版")).strip()
        if not re.match(r"^https?://", url):
            print("❌ %s.url 不是 http(s) 链接：%r" % (key, url), file=sys.stderr)
            sys.exit(2)
        out[key] = {"label": label, "url": url}
    return out


def patch(html, want):
    """把两张卡片里的按钮链接换掉。返回 (新 html, 改动清单)。"""
    changed = []
    for key, w in want.items():
        b = section_bounds(html, w["label"])
        if b is None:
            print("❌ 下载页里找不到「%s」这张卡片（页面结构变了？）" % w["label"], file=sys.stderr)
            sys.exit(2)
        seg = html[b[0]:b[1]]
        m = BTN.search(seg)
        if not m:
            print("❌ 「%s」卡片里没有 <a class=\"btn\" href=…> 按钮" % w["label"], file=sys.stderr)
            sys.exit(2)
        cur = m.group(2)
        if cur == w["url"]:
            continue
        new_seg = seg[:m.start(2)] + w["url"] + seg[m.end(2):]
        html = html[:b[0]] + new_seg + html[b[1]:]
        changed.append((w["label"], cur, w["url"]))
    return html, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写文件（不一致退出 1）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--conf", default=CONF)
    ap.add_argument("--page", default=PAGE)
    a = ap.parse_args()

    want = load_conf(a.conf)
    if not os.path.isfile(a.page):
        print("❌ 找不到下载页：%s" % a.page, file=sys.stderr)
        return 2
    orig = open(a.page, encoding="utf-8").read()
    html, changed = patch(orig, want)

    if a.check:
        for label, cur, new in changed:
            print("   ❌ 「%s」的下载按钮指向 %s，但配置里是 %s" % (label, cur, new))
        if changed:
            print("   （跑 python3 _build/sync-download-links.py 同步，或到管理后台改）")
            return 1
        print("   ✅ 两个下载按钮与 download-links.json 一致")
        return 0

    if not changed:
        print("   ✅ 下载按钮已是最新（安卓 / Windows 都与配置一致）")
        return 0

    for label, cur, new in changed:
        print("   ✏️  %s：%s → %s" % (label, cur, new))
    if a.dry_run:
        print("   [dry] 未写盘")
        return 0

    tmp = a.page + ".links-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, a.page)
    print("   ✅ 已写入 %s" % os.path.relpath(a.page, SITE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
