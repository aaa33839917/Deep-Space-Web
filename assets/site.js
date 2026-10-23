(function(){ document.querySelectorAll('.v6-year, #year').forEach(function(e){ e.textContent = new Date().getFullYear(); }); })();

/* ★ 2026-10-23（服主）：[PRODUCT] 区的界面图，一处放两张，用图下面那排按钮切换。
   同一时刻只显示一张（另一张用 hidden 属性藏起来；CSS 里有 display:none!important 兜底）。
   ⚠️ 没有 JS 时第一张照样显示 —— 降级不等于把内容藏没。
   判据按 data 属性走（不依赖元素顺序，R4.9 那条教训）。 */
(function(){
  var box = document.querySelector('.shots');
  if (!box) return;
  var imgs = [].slice.call(box.querySelectorAll('img[data-shot-view]'));
  var btns = [].slice.call(document.querySelectorAll('.shots__nav [data-shot]'));
  if (imgs.length < 2 || !btns.length) return;
  function show(key){
    var hit = false;
    imgs.forEach(function (el){
      var on = el.getAttribute('data-shot-view') === key;
      el.hidden = !on;
      if (on) hit = true;
    });
    if (!hit) return;                       // 找不到对应图就不动，别把两张都藏掉
    btns.forEach(function (b){
      var on = b.getAttribute('data-shot') === key;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
  }
  btns.forEach(function (b){
    b.addEventListener('click', function (){ show(b.getAttribute('data-shot')); });
  });
  show(btns[0].getAttribute('data-shot'));
})();
