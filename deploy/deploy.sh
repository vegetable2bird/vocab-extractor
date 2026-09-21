#!/bin/sh
# vocab-extractor 部署脚本（服务器上以 root 执行）
#
# 前置：仓库已克隆到 /tmp/vx
#   git clone --depth 1 https://github.com/vegetable2bird/vocab-extractor.git /tmp/vx
#
# 用法：
#   sh /tmp/vx/deploy/deploy.sh          # 首次部署或更新
set -e

SRC="${SRC:-/tmp/vx}"
DST="${DST:-/opt/vocab-extractor}"
UNIT=/etc/systemd/system/vocab-extractor.service

[ -d "$SRC" ] || { echo "ERROR: 仓库未克隆到 $SRC"; exit 1; }

mkdir -p "$DST/web"
cp "$SRC/index.html"                     "$DST/web/index.html"
cp "$SRC/deploy/server.js"               "$DST/server.js"
cp "$SRC/deploy/vocab-extractor.service" "$UNIT"

systemctl daemon-reload
systemctl enable vocab-extractor >/dev/null 2>&1 || true

if systemctl is-active --quiet vocab-extractor; then
  systemctl restart vocab-extractor
else
  systemctl start vocab-extractor
fi

sleep 1
echo "STATUS : $(systemctl is-active vocab-extractor)"
echo "MD5    : $(md5sum "$DST/web/index.html")"
echo "LISTEN :"
ss -ltn | head -12
