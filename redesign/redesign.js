(function(){
  // 只有一个渐进增强：当前年份
  var y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();
})();
