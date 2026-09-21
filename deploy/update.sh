#!/bin/sh
# vocab-extractor 自动更新：从 GitHub 拉最新代码并重新部署
#
# 用法（服务器上以 root 执行）：
#   sh /opt/vocab-extractor/update.sh
#
# 说明：本机到 github.com:443 为间歇性可达（实测出现过 135s 超时），
#       因此拉取环节带重试。TRIES 可调，默认 5 次。
set -u

SRC="${SRC:-/tmp/vx}"
DST="${DST:-/opt/vocab-extractor}"
REPO="https://github.com/vegetable2bird/vocab-extractor.git"
TRIES="${TRIES:-5}"

# 降低低速连接的超时判定，让失败快速暴露以便重试
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" config http.lowSpeedLimit 1000 2>/dev/null
  git -C "$SRC" config http.lowSpeedTime 20 2>/dev/null
fi

if [ ! -d "$SRC/.git" ]; then
  echo "[1/2] 首次克隆（无本地副本）"
  git clone --depth 1 "$REPO" "$SRC" || { echo "ERROR: 克隆失败"; exit 1; }
else
  echo "[1/2] 拉取最新代码（最多 $TRIES 次尝试）"
  i=1
  while [ "$i" -le "$TRIES" ]; do
    if git -C "$SRC" pull -q; then
      echo "  第 $i 次：拉取成功"
      break
    fi
    echo "  第 $i 次：失败"
    i=$((i + 1))
    if [ "$i" -le "$TRIES" ]; then
      echo "  5 秒后重试…"
      sleep 5
    fi
  done
  if [ "$i" -gt "$TRIES" ]; then
    echo "ERROR: $TRIES 次拉取均失败（github.com 不可达）"
    echo "       服务器上已运行的是上一个版本，未受影响。稍后再试即可。"
    exit 1
  fi
fi

echo "[2/2] 部署"
exec sh "$SRC/deploy/deploy.sh"
