#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加速器下载页 · 版本号 / 校验值 **自动同步**（发版脚本调用，别再手抄）

★ 为什么要有它（2026-10-01，第二次栽在同一件事上）：
  官网下载页上的版本号与 sha256 是**手抄**的。加速器项目天天发版，官网没人回头改 ⇒
  一度落后 17 个安卓版本 / 13 个 Windows 版本（见 `check-accel-version.py` 的说明）。
  上一次的修法是"加一个检查器"，但**检查器只能拦住，不会帮你改** ⇒ 每次发版还是得人工去改页面，
  于是迟早再腐化。这次把**写**也自动化：发版脚本在清单上线并自检通过之后调它。
  （配套纪律：**这个页面只由本脚本改**，别再手工动版本号/校验值那几处。）

数据来源（权威，不是抄的）—— 与 `check-accel-version.py` 完全一致：
  <加速器项目>/www/version.json       安卓：versionName（下载页=通用包）/ sha256 / size
  <加速器项目>/www/version-win.json   Windows：versionName / installer.sha256 / installer.size

它改这四处（都在 `accelerator/download/index.html`）：
  ① 两张卡片里的「版本」行；② 「大小」行的「约 N MB」；③ 「文件校验」里的版本 + sha256；
  ④ 维护者注释里那句「★ YYYY-MM-DD 全面更新到 v安卓 / vWindows」。

★ 三条自我约束（都是踩过的坑换来的）：
  1. **改不动就报错退出**，绝不"没匹配到就静静跳过"—— 空集合永远通过；
  2. 写完**回跑 `check-accel-version.py`**，不过就**回滚**（原文件先备份）；
  3. 幂等：内容没变就一个字节都不写（mtime 不变），便于"没变化"和"改坏了"区分开。

用法：
    python3 _build/sync-accel-version.py                 # 同步（写完自检）
    python3 _build/sync-accel-version.py --dry-run       # 只打印将要改什么
    python3 _build/sync-accel-version.py --accel-dir X   # 换权威清单位置（自测用）
    python3 _build/sync-accel-version.py --no-verify     # 跳过回跑检查器（自测回滚路径用）
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(HERE)
DEFAULT_PAGE = os.path.join(WEB_ROOT, "accelerator", "download", "index.html")
CHECK = os.path.join(HERE, "check-accel-version.py")
DEFAULT_ACCEL = os.environ.get(
    "DEEPSPACE_ACCEL_WWW",
    "/vol1/1000/Server_file_002/DeepSpaceProject/Deep_Space_Accelerator/www",
)

ANDROID = "安卓版"
WINDOWS = "Windows 版"


def die(msg):
    print("   ❌ " + msg, file=sys.stderr)
    sys.exit(1)


def mb(n):
    try:
        return max(1, int(round(int(n) / 1024.0 / 1024.0)))
    except Exception:
        return None


def load_want(accel_dir):
    fa = os.path.join(accel_dir, "version.json")
    fw = os.path.join(accel_dir, "version-win.json")
    for f in (fa, fw):
        if not os.path.isfile(f):
            die("读不到权威清单：%s" % f)
    a = json.load(open(fa, encoding="utf-8"))
    w = json.load(open(fw, encoding="utf-8"))
    inst = w.get("installer") or {}
    return {
        ANDROID: {"ver": str(a["versionName"]), "sha": str(a["sha256"]),
                  "mb": mb(a.get("size"))},
        WINDOWS: {"ver": str(w["versionName"]), "sha": str(inst.get("sha256") or ""),
                  "mb": mb(inst.get("size"))},
    }


def section_bounds(html, label):
    """返回 (start, end)：该卡片（`<h2>label</h2>` 到下一个 `<h2>`）在 html 里的区间。"""
    m = re.search(r"<h2>\s*%s\s*</h2>" % re.escape(label), html)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"<h2>", html[start:])
    return (start, start + nxt.start()) if nxt else (start, len(html))


# 「文件校验」卡片里的形状（与检查器同一套正则，别各写一份）
SHA_BLOCK = re.compile(
    r'(class="tip small"[^>]*>\s*(安卓版|Windows 版)\s*)v[\d.]+\s*(</div>\s*'
    r'<code[^>]*>\s*)([0-9a-f]{64})(\s*</code>)',
    re.S,
)
VER_ROW = re.compile(r"(<th>版本</th>\s*<td>\s*<b>)v[\d.]+(</b>)", re.S)
SIZE_ROW = re.compile(r"(<th>大小</th>\s*<td>\s*约\s*)\d+(\s*MB)")
# ⚠️ 尾部那个「（由发版脚本自动同步）」必须**一起吃掉**：不吃的话每跑一次都会再追加一遍
#    —— 那就不是幂等的了（第一次写出来就是这样，跑第二遍才发现）。
COMMENT = re.compile(
    r"★\s*\d{4}-\d{2}-\d{2}\s*全面更新到\s*v[\d.]+\s*/\s*v[\d.]+"
    r"(（由发版脚本自动同步）)?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accel-dir", default=DEFAULT_ACCEL, help="加速器 www/ 目录（权威清单所在）")
    ap.add_argument("--page", default=DEFAULT_PAGE)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-verify", action="store_true", help="跳过回跑检查器（自测用）")
    a = ap.parse_args()

    if not os.path.isfile(a.page):
        die("找不到下载页：%s" % a.page)
    want = load_want(a.accel_dir)
    for label, w in want.items():
        if not w["sha"]:
            die("%s 的 sha256 为空（清单里没有 installer.sha256 / sha256？）" % label)

    orig = open(a.page, encoding="utf-8").read()
    html = orig
    changed = {"版本行": 0, "大小行": 0, "校验块": 0, "注释": 0}

    # ① + ② 两张卡片：版本行 / 大小行（从后往前改，避免偏移错位）
    for label in (WINDOWS, ANDROID):
        b = section_bounds(html, label)
        if b is None:
            die("页面里找不到 `<h2>%s</h2>` 这张卡片 —— 页面结构变了？(本脚本不猜)" % label)
        start, end = b
        sec = html[start:end]

        sec2, n = VER_ROW.subn(lambda m: m.group(1) + "v" + want[label]["ver"] + m.group(2),
                               sec, count=1)
        if n != 1:
            die("%s 卡片里找不到「版本」行（期望恰好 1 处，实际 %d）" % (label, n))
        changed["版本行"] += 1

        if want[label]["mb"]:
            sec3, n = SIZE_ROW.subn(lambda m: m.group(1) + str(want[label]["mb"]) + m.group(2),
                                    sec2, count=1)
            if n != 1:
                die("%s 卡片里找不到「大小 约 N MB」行（期望 1 处，实际 %d）" % (label, n))
            sec2 = sec3
            changed["大小行"] += 1
        html = html[:start] + sec2 + html[end:]

    # ③ 「文件校验」卡片：版本 + sha256（两处一起改，正则里带标签）
    def sha_repl(m):
        label = m.group(2)
        changed["校验块"] += 1
        return m.group(1) + "v" + want[label]["ver"] + m.group(3) + want[label]["sha"] + m.group(5)

    html, n = SHA_BLOCK.subn(sha_repl, html)
    if n != 2:
        die("「文件校验」卡片里应当恰好有 2 个校验块（安卓/Windows），实际匹配 %d 个" % n)

    # ④ 维护者注释那句（找不到只警告，不阻断：它是注释，检查器本来就不看）
    today = datetime.date.today().isoformat()
    newc = "★ %s 全面更新到 v%s / v%s（由发版脚本自动同步）" % (
        today, want[ANDROID]["ver"], want[WINDOWS]["ver"])
    html, n = COMMENT.subn(newc, html, count=1)
    if n == 1:
        changed["注释"] += 1
    else:
        print("   ⚠️ 注释里那句「★ … 全面更新到 …」没匹配到，跳过（不影响页面显示）")

    if html == orig:
        print("   ✅ 官网下载页已是最新（安卓 v%s / Windows v%s），未改动任何字节"
              % (want[ANDROID]["ver"], want[WINDOWS]["ver"]))
        return 0

    summary = "、".join("%s %d 处" % (k, v) for k, v in changed.items() if v)
    if a.dry_run:
        print("   [dry] 会改：%s" % summary)
        print("   [dry] 目标：安卓 v%s / Windows v%s"
              % (want[ANDROID]["ver"], want[WINDOWS]["ver"]))
        return 0

    def write(text):
        """原子写：先写同目录临时文件再 replace（中途失败不会留下半个页面）。"""
        tmp = a.page + ".sync-tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, a.page)

    # ★ 备份**放内存**（orig 本来就在手里），**不落盘**：
    #   落一个 `.sync-bak` 在站点目录里，回滚路径上忘了删就留下了（第一次写就踩了），
    #   而 deploy.sh 是整目录发布的 ⇒ 迟早把这个垃圾文件发出去。
    write(html)
    print("   ✏️  已同步：%s" % summary, flush=True)

    if not a.no_verify:
        r = subprocess.run([sys.executable, CHECK], capture_output=True, text=True)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            write(orig)                      # 回滚（用内存里的原文，不依赖任何备份文件）
            print(out.rstrip(), file=sys.stderr, flush=True)
            die("同步后的页面**没通过检查器** ⇒ 已回滚到原文件（上面是检查器原文）")
        for line in out.strip().splitlines():
            print(line if line.startswith("   ") else "   " + line)
    print("   ℹ️  这一步只改**本地文件**；要上线请另外跑 Deep_Space_Web/deploy.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
