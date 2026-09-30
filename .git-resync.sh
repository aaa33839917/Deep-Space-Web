#!/usr/bin/env bash
# 一次性收尾：把本地对齐到远端。
#
# 背景：github.com 的 git 协议时通时不通。不通时改用 GitHub API 造提交推远端，
# 于是本地"领先 N 个"但推不上去（非快进）。**两边文件内容是一样的**，只是提交对象不同。
# 用法：网络恢复后  bash .git-resync.sh
set -e
cd "$(dirname "$0")"
echo "拉取远端…"
git fetch origin main
echo "对齐（内容相同，不会丢东西）…"
git reset --hard origin/main
echo "✅ 完成。"
git log --oneline -1
git status -sb | head -1
