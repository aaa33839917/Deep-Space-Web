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
