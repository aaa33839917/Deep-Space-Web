(function(){ document.querySelectorAll('.v6-year, #year').forEach(function(e){ e.textContent = new Date().getFullYear(); }); })();

/* ★ 2026-10-23（服主）：[PRODUCT] 区只放单纯的界面图，可上一张 / 下一张切换（照 TRAE 官网那种）。
   没有自动轮播、没有框 —— 图就是图。
   ⚠️ 只有一张图时按钮不出现（不摆一排点了没反应的东西）；没有 JS 时第一张照样显示，
      第二张靠 hidden 藏着 —— 降级不等于把内容藏没。 */
(function(){
  var box = document.querySelector('.shots');
  if (!box) return;
  var imgs = [].slice.call(box.querySelectorAll('img'));
  if (imgs.length < 2) return;
  var nav = box.parentNode.querySelector('.shots__nav');
  if (!nav) return;
  var i = 0;
  function show(n){
    i = (n + imgs.length) % imgs.length;
    imgs.forEach(function (el, k) { el.hidden = k !== i; });
  }
  nav.querySelectorAll('[data-shot]').forEach(function (b){
    b.addEventListener('click', function (){ show(i + (b.getAttribute('data-shot') === 'next' ? 1 : -1)); });
  });
  show(0);
})();


/* ---------- [ PRODUCT ] 轮播（2026-10-23 服主：照 TRAE 官网那种） ----------
   与 Trae 的差别：不做首尾占位伪循环，三张就到头；按钮到端点直接禁用。
   支持：点箭头、鼠标/手指拖动、窗口尺寸变化重算步长。 */
(function(){
  var root = document.querySelector('[data-pc]');
  if (!root) return;
  var viewport = root.querySelector('.pc__viewport');
  var track = root.querySelector('.pc__track');
  var slides = [].slice.call(root.querySelectorAll('.pc__slide'));
  var prev = root.querySelector('[data-pc-prev]');
  var next = root.querySelector('[data-pc-next]');
  if (!track || slides.length < 2) return;

  var i = 0, step = 0, drag = null;

  function measure(){
    var cs = getComputedStyle(track);
    var gap = parseFloat(cs.columnGap || cs.gap) || 0;
    step = slides[0].getBoundingClientRect().width + gap;
  }
  function paint(animate){
    if (animate === false) track.style.transition = 'none';
    track.style.transform = 'translate3d(' + (-i * step) + 'px,0,0)';
    slides.forEach(function(s, k){
      s.classList.toggle('is-off', k !== i);
      s.classList.toggle('is-prev', k < i);
      s.classList.toggle('is-next', k > i);
    });
    prev.disabled = i === 0;
    next.disabled = i === slides.length - 1;
    if (animate === false){ void track.offsetWidth; track.style.transition = ''; }
  }
  function go(n){
    i = Math.max(0, Math.min(slides.length - 1, n));
    paint(true);
  }

  prev.addEventListener('click', function(){ go(i - 1); });
  next.addEventListener('click', function(){ go(i + 1); });

  viewport.addEventListener('pointerdown', function(e){
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    drag = { x: e.clientX, base: -i * step };
    try { viewport.setPointerCapture(e.pointerId); } catch (err) {}
    track.style.transition = 'none';
  });
  viewport.addEventListener('pointermove', function(e){
    if (!drag) return;
    track.style.transform = 'translate3d(' + (drag.base + e.clientX - drag.x) + 'px,0,0)';
  });
  function endDrag(e){
    if (!drag) return;
    var dx = e.clientX - drag.x;
    var threshold = Math.max(40, step * 0.15);
    track.style.transition = '';
    if (dx <= -threshold) go(i + 1);
    else if (dx >= threshold) go(i - 1);
    else paint(true);
    drag = null;
  }
  viewport.addEventListener('pointerup', endDrag);
  viewport.addEventListener('pointercancel', endDrag);

  window.addEventListener('resize', function(){ measure(); paint(false); });
  measure(); paint(false);
})();


/* ---------- 帮助文档：目录高亮（2026-10-23） ---------- */
(function(){
  var links = [].slice.call(document.querySelectorAll('.docs__side a[href^="#"], .docs__toc a[href^="#"]'));
  if (!links.length) return;
  var heads = [].slice.call(document.querySelectorAll('.docs__body h1[id], .docs__body h2[id]'));
  if (!heads.length) return;
  var ticking = false;
  function paint(){
    ticking = false;
    var y = window.scrollY + 120;
    var cur = heads[0];
    for (var i = 0; i < heads.length; i++) {
      if (heads[i].getBoundingClientRect().top + window.scrollY <= y) cur = heads[i];
    }
    var id = cur ? cur.id : '';
    links.forEach(function(a){ a.classList.toggle('on', a.getAttribute('href') === '#' + id); });
  }
  window.addEventListener('scroll', function(){
    if (!ticking) { ticking = true; requestAnimationFrame(paint); }
  }, { passive: true });
  paint();
})();
