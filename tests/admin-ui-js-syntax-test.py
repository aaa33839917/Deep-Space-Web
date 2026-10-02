#!/usr/bin/env python3
# =============================================================================
#  官网管理后台 `_admin/ui.html` 的 **JS 语法自测**（2026-10-02 新增）
# -----------------------------------------------------------------------------
#  为什么要有它：同一天，加速器的面板就因为这个栽过一次 —— 页面 `<script>` 里一个
#  语法错误（重复声明 const）⇒ 浏览器**整段不执行** ⇒ 表头在、一行数据都没有，
#  而接口、数据、日志全都正常。官网后台是**单文件 JS 应用**，风险一模一样：
#  一处引号写错，整个后台就"能打开但什么都不显示"，谁也不会天天开控制台看。
#
#  做法：把 ui.html 里每段 `<script>` 抽出来交给 `node --check`。几毫秒，无假绿空间。
#  跑法： python3 tests/admin-ui-js-syntax-test.py
# =============================================================================
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "..", "_admin", "ui.html")


def main() -> int:
    if not shutil.which("node"):
        print("⚠️ 没有 node ⇒ 这一层没验到")
        return 0
    if not os.path.isfile(UI):
        print("❌ 找不到 %s" % UI)
        return 2
    html = open(UI, encoding="utf-8").read()
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not scripts:
        print("❌ ui.html 里没有 <script> —— 页面是不是被改坏了？")
        return 1
    fails = 0
    for i, js in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
            tmp = f.name
        try:
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        finally:
            os.unlink(tmp)
        if r.returncode == 0:
            print("  ✅ 第%d段脚本语法 OK（%d 字节）" % (i + 1, len(js)))
        else:
            fails += 1
            first = next((ln for ln in r.stderr.split("\n") if ln.strip()), "")
            print("  ❌ 第%d段脚本**语法错误**（浏览器里整段不执行 ⇒ 后台会「能打开但什么都不显示」）" % (i + 1))
            print("        %s" % first[:160])
    print()
    if fails:
        print("❌ 失败 %d 处" % fails)
        return 1
    print("✅ 全部通过（%d 段脚本）" % len(scripts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
