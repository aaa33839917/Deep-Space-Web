#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加速器版本一致性自检 —— 防止「官网写的版本」与「实际发布的版本」再次脱节。

★ 为什么要有这个（2026-10-01 服主反馈）：
  服主让我「自己看看加速器迭代到什么版本了」。一查发现官网下载页还写着
  **安卓 v2.7.5 / Windows v1.0.0**，而实际早就到了 **v2.7.22 / v1.7.13** ——
  落后 17 个安卓版本、13 个 Windows 版本，而且 Windows 那段
  「不含 EasyTier 核心，请把官方版本解压到同一个文件夹」从 v1.2.0 起就不成立了
  （现在是自带核心的安装包）。

  根因：版本号是**手抄**进 HTML 的，加速度器项目那边天天发版，没人回头改官网。
  ⇒ 让机器每次发布前对着**权威清单**（加速器项目自己的 version.json）核一遍。

数据来源（权威，不是抄的）：
  <加速器项目>/www/version.json       安卓：versionName / sha256 / size
  <加速器项目>/www/version-win.json   Windows：versionName / installer.sha256 / installer.size

找不到加速器目录时**软跳过**（不阻断发布）—— 因为官网仓库本身不该依赖兄弟目录存在。
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(HERE)
PAGE = os.path.join(WEB_ROOT, "accelerator", "download", "index.html")
ACCEL = "/vol1/1000/Server_file_002/DeepSpaceProject/Deep_Space_Accelerator/www"

# 「文件校验」卡片里的形状：<div class="tip small" ...>安卓版 v2.7.22</div>  <code ...>sha</code>
SHA_BLOCK = re.compile(
    r'class="tip small"[^>]*>\s*(安卓版|Windows 版)\s*(v[\d.]+)\s*</div>\s*'
    r'<code[^>]*>\s*([0-9a-f]{64})\s*</code>',
    re.S,
)
VER_ROW = re.compile(r"<th>版本</th>\s*<td>\s*<b>(v[\d.]+)</b>", re.S)


def fail(msg):
    print("   ❌ " + msg, file=sys.stderr)
    return 1


def main():
    if not os.path.isdir(ACCEL):
        print("   ⏭  找不到加速器目录，跳过版本核对：%s" % ACCEL)
        return 0
    if not os.path.isfile(PAGE):
        return fail("找不到下载页：%s" % PAGE)

    try:
        android = json.load(open(os.path.join(ACCEL, "version.json"), encoding="utf-8"))
        windows = json.load(open(os.path.join(ACCEL, "version-win.json"), encoding="utf-8"))
    except Exception as e:
        print("   ⏭  读不到加速器的版本清单（%s），跳过核对" % e)
        return 0

    want = {
        "安卓版": (android["versionName"], android["sha256"], android.get("size")),
        "Windows 版": (
            windows["versionName"],
            windows["installer"]["sha256"],
            windows["installer"].get("size"),
        ),
    }

    html = open(PAGE, encoding="utf-8").read()
    rc = 0

    # ① 核对「文件校验」卡片：版本号 + sha256 必须逐字对上
    found = {label: (ver.lstrip("v"), sha) for label, ver, sha in SHA_BLOCK.findall(html)}
    for label, (ver, sha, size) in want.items():
        if label not in found:
            rc |= fail("下载页的「文件校验」卡片里找不到 %s 的校验块" % label)
            continue
        got_ver, got_sha = found[label]
        if got_ver != ver:
            rc |= fail("%s 版本不一致：页面写 v%s，实际是 v%s" % (label, got_ver, ver))
        if got_sha != sha:
            rc |= fail("%s sha256 不一致：\n        页面 %s\n        实际 %s" % (label, got_sha, sha))
        if not rc:
            print("   ✅ %-11s v%s  sha256 一致" % (label, ver))

    # ② 核对卡片顶部的「版本」行（顺序固定：先安卓后 Windows）
    rows = [v.lstrip("v") for v in VER_ROW.findall(html)]
    expect_rows = [want["安卓版"][0], want["Windows 版"][0]]
    if rows[:2] != expect_rows:
        rc |= fail("顶部「版本」行与清单不一致：页面 %s，实际 %s" % (rows[:2], expect_rows))

    # ③ 任何一处残留的旧版本号都要揪出来（这正是上次漏掉的地方）
    #    ⚠️ 必须先去掉 HTML 注释：注释是写给维护者看的，里面**故意**会提旧版本号
    #    （比如「上一版还停在 v2.7.5」）。第一版没去掉，结果被自己的注释绊倒了。
    visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    stale = [v.lstrip("v") for v in re.findall(r"v(\d+\.\d+\.\d+)", visible)]
    known = set(expect_rows)
    leftover = sorted({v for v in stale if v not in known})
    if leftover:
        rc |= fail("页面里还有不在清单里的版本号：%s（很可能是没改干净的旧版本）" % ", ".join(leftover))

    if rc == 0:
        print("   ✅ 下载页与加速器版本清单完全一致（安卓 v%s / Windows v%s）"
              % (want["安卓版"][0], want["Windows 版"][0]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
