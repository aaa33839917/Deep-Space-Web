/* ============================================================================
   页面陈旧自检 —— 发现自己这份 HTML 是旧的，就自动刷新一次。

   为什么需要它：
     GitHub Pages 给 HTML 发 `cache-control: max-age=600`，也就是**这 10 分钟内
     浏览器根本不会去问服务器**。于是"后台改完发布成功了，浏览器里却还是旧的"，
     看着就像没生效。（这个误会 2026-09-29 一天之内发生了三次。）

   怎么工作：
     deploy.sh 给每个页面注入一行 <meta name="dsv" content="构建号">，
     这里把它和站点根目录的 site-version.json 比一下。
     不一样 ⇒ 说明手里这份是旧的 ⇒ 自动 reload() 一次。
     （reload 会让浏览器重新校验主文档，等于替你按了一次 F5。）

   防循环：同一个构建号，每个会话只自动刷一次。
   ========================================================================== */
(function () {
  var el = document.currentScript;
  var meta = document.querySelector('meta[name="dsv"]');
  if (!meta || !window.fetch) return;

  var mine = meta.getAttribute('content') || '';
  // 从自己这个 script 的地址推出站点根前缀（首页是 ./，子页面是 ../）
  var base = (el && el.src) ? el.src.replace(/assets\/cache-check\.js.*$/, '') : './';

  fetch(base + 'site-version.json', { cache: 'no-store' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (!d || !d.build || d.build === mine) return;
      var k = 'dsv-reloaded-' + d.build;
      try {
        if (sessionStorage.getItem(k)) return;   // 这个版本已经自动刷过了
        sessionStorage.setItem(k, '1');
      } catch (e) { /* 无痕模式等，忽略 */ }
      location.reload();
    })
    .catch(function () { /* 拿不到就算了，不影响页面 */ });
})();
