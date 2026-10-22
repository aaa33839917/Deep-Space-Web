(function(){
  var els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) { els.forEach(function(e){e.classList.add('on')}); return; }
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(en){ if (en.isIntersecting) { en.target.classList.add('on'); io.unobserve(en.target); } });
  }, {threshold: 0.12, rootMargin: '0px 0px -40px 0px'});
  els.forEach(function(e){ io.observe(e); });
})();
