/**
 * vocab-extractor 独立静态站点服务
 * 零依赖（仅 Node 内置模块），由 systemd 托管，与服务器上其他项目完全隔离。
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = process.env.WEB_ROOT || "/opt/vocab-extractor/web";
const PORT = Number(process.env.PORT || 8080);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8",
};

const server = http.createServer((req, res) => {
  let p = decodeURIComponent((req.url || "/").split("?")[0]);
  if (p === "/") p = "/index.html";

  const file = path.join(ROOT, path.normalize(p));

  // 防目录穿越：解析后的路径必须仍在 ROOT 内
  if (!file.startsWith(ROOT)) {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    return res.end("403 forbidden");
  }

  fs.readFile(file, (err, buf) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      return res.end("404 not found");
    }
    res.writeHead(200, {
      "Content-Type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    res.end(buf);
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`vocab-extractor serving ${ROOT} on :${PORT}`);
});

// 让 systemd 的 stop/restart 能优雅退出
["SIGTERM", "SIGINT"].forEach((sig) =>
  process.on(sig, () => server.close(() => process.exit(0)))
);
