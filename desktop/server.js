/**
 * 生词提取器 · 本地离线版服务
 * 仅监听 127.0.0.1（本机），不对外网开放。由「启动.cmd」调起。
 * 打开后浏览器地址是 http://127.0.0.1:8787/ —— localhost 属于安全上下文，
 * 因此可以像正常网站一样「安装为应用」。
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

// 同目录若有 index.html 就用同目录（独立分发包形态）；
// 否则回退到上一级（直接运行仓库里的 desktop/ 时，站点文件在项目根）。
const LOCAL_DIR = __dirname;
const ROOT = fs.existsSync(path.join(LOCAL_DIR, "index.html"))
  ? LOCAL_DIR
  : path.resolve(LOCAL_DIR, "..");
const HOST = "127.0.0.1";
const PORT = Number(process.env.PORT || 8787);

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
  // 防目录穿越：只能访问本目录内的文件
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

server.on("error", (e) => {
  if (e.code === "EADDRINUSE") {
    console.log("端口 " + PORT + " 已被占用 —— 本地服务应该已经在运行了。");
    process.exit(0);
  }
  throw e;
});

server.listen(PORT, HOST, () => {
  console.log("生词提取器已就绪：" + "http://" + HOST + ":" + PORT + "/");
  console.log("关闭本窗口即停止本地服务。");
});

// systemd / 任务管理器结束进程时优雅退出
["SIGTERM", "SIGINT"].forEach((sig) =>
  process.on(sig, () => server.close(() => process.exit(0)))
);
