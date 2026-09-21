/* 生词提取器 · Service Worker
 *
 * 作用有两个：
 *  1) 让浏览器认为这是一个「可安装的应用」（Chrome 桌面端弹出安装入口的硬性条件之一）
 *  2) 把应用外壳缓存下来，断网也能打开
 *
 * 策略：导航请求走「网络优先」（保证更新后立刻拿到新版，不会看到旧页面），
 *      静态资源走「缓存优先」（图标/manifest 这类不变的东西不必每次请求）。
 */
const CACHE = "vocab-extractor-v1";

// 应用外壳：这几个文件齐全，装到桌面/主屏才会有图标
const SHELL = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon.svg",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      // 单个文件缺失不应让整个安装失败
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  // 只管同源请求；Tesseract / PDF.js 等 CDN 资源交给它们自己的缓存机制
  if (url.origin !== self.location.origin) return;

  // 导航请求：网络优先，失败时回退到缓存的外壳
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put("./index.html", copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match("./index.html").then((r) => r || Response.error()))
    );
    return;
  }

  // 其余静态资源：缓存优先
  e.respondWith(
    caches.match(req).then(
      (hit) =>
        hit ||
        fetch(req).then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
    )
  );
});
