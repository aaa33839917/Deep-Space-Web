/*
  深空官网背景：按 Trae 首页 EffectMaterial 的实际实现移植（2D 两段式）
  pass1: simplex FBM 流体纹理（绿 #32F08C → 白）
  pass2: 5px 方块 + 2px 缝隙，按同一流场位移 35px，亮度阈值 0.87，随机双色
  参数来自实测 uniform：speed .18 / density .5 / frequency 4 / greenRatio .49
*/
(function () {
  var canvas = document.getElementById('wave');
  if (!canvas) return;
  var gl = canvas.getContext('webgl2', { alpha: true, antialias: false, depth: false, powerPreference: 'low-power' });
  if (!gl) { canvas.style.display = 'none'; return; }
  var hero = canvas.parentElement;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var VS = `#version 300 es
  in vec2 aPos;
  void main(){ gl_Position = vec4(aPos, 0.0, 1.0); }`;

  var NOISE = `
  vec2 hash2(vec2 p){
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
  }
  float snoise(vec2 p){
    const float K1 = 0.366025404;
    const float K2 = 0.211324865;
    vec2 i = floor(p + (p.x + p.y) * K1);
    vec2 a = p - i + (i.x + i.y) * K2;
    vec2 o = (a.x > a.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec2 b = a - o + K2;
    vec2 c = a - 1.0 + 2.0 * K2;
    vec3 h = max(0.5 - vec3(dot(a,a), dot(b,b), dot(c,c)), 0.0);
    vec3 n = h*h*h*h * vec3(dot(a, hash2(i + 0.0)), dot(b, hash2(i + o)), dot(c, hash2(i + 1.0)));
    return dot(n, vec3(70.0));
  }
  float fbm(vec2 p){
    float v = 0.0, amp = 0.5, freq = 1.0;
    for (int i = 0; i < 3; i++){ v += amp * snoise(p * freq); freq *= 2.0; amp *= 0.5; }
    return v * 0.5 + 0.5;
  }`;

  var FLUID = `#version 300 es
  precision highp float;
  uniform float uTime;
  uniform vec2 uRes;
  uniform vec3 uColor1;
  uniform vec3 uColor2;
  out vec4 outColor;
  ` + NOISE + `
  void main(){
    vec2 st = gl_FragCoord.xy / uRes;
    float t = uTime * 0.18;
    vec2 q = vec2(
      fbm(st * 0.5 + vec2(0.0, 0.2 * t)),
      fbm(st * 0.5 + vec2(1.2, -0.3 * t))
    );
    float n = fbm(st * 0.5 + q * 4.0);
    outColor = vec4(mix(uColor1, uColor2, n), 1.0);
  }`;

  var PIXEL = `#version 300 es
  precision highp float;
  uniform sampler2D uFluid;
  uniform vec2 uRes;
  uniform float uTime;
  uniform vec2 uMouse;
  uniform float uPixelSize;
  uniform float uPixelGap;
  uniform float uThreshold;
  uniform float uGreenRatio;
  uniform vec3 uGreen;
  uniform vec3 uWhite;
  out vec4 outColor;
  ` + NOISE + `
  float rand2(vec2 st){ return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123); }
  vec2 fluidFlow(vec2 uv, float time){
    float speed = 0.15, density = 1.5, frequency = 2.5;
    vec2 q = vec2(
      fbm(uv * density + vec2(0.0, 0.2 * time * speed)),
      fbm(uv * density + vec2(1.2, -0.3 * time * speed))
    );
    vec2 f = vec2(q.x * 0.3, q.y * 0.7) * 2.0;
    f.x *= 0.5;
    f.y *= 1.5;
    return f;
  }
  void main(){
    vec2 pixelCoord = gl_FragCoord.xy;
    float totalSize = uPixelSize + uPixelGap;
    vec2 blockId = floor(pixelCoord / totalSize);
    vec2 blockCenterUV = (blockId * totalSize + vec2(uPixelSize * 0.5)) / uRes;
    vec2 flow = fluidFlow(blockCenterUV, uTime) * 35.0;
    vec2 blockPos = blockId * totalSize;
    vec2 posInBlock = pixelCoord - blockPos;
    if (posInBlock.x > uPixelSize || posInBlock.y > uPixelSize) discard;

    vec2 offsetBlockCenter = blockPos - flow + vec2(uPixelSize * 0.5);
    vec2 blockUv = offsetBlockCenter / uRes;
    vec4 color = texture(uFluid, blockUv);
    float brightness = (color.r + color.g + color.b) / 3.0;

    float rnd = rand2(blockId);
    float dynamicThreshold = uThreshold - 0.08 * rnd;
    if (brightness <= dynamicThreshold) discard;

    float dist = distance(blockCenterUV, uMouse);
    float mouseFactor = 1.0 - smoothstep(0.0, 0.3, dist);
    mouseFactor *= 1.3;

    vec3 col;
    if (rnd < uGreenRatio) {
      col = uGreen;
      if (mouseFactor > 0.0) col = mix(col, uWhite, mouseFactor);
    } else {
      col = uWhite;
      if (mouseFactor > 0.0) col = mix(col, uGreen, mouseFactor);
    }
    outColor = vec4(col, 1.0);
  }`;

  function compile(type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.warn('wave shader:', gl.getShaderInfoLog(s)); return null; }
    return s;
  }
  function program(fsSrc) {
    var vs = compile(gl.VERTEX_SHADER, VS), fs = compile(gl.FRAGMENT_SHADER, fsSrc);
    if (!vs || !fs) return null;
    var p = gl.createProgram();
    gl.attachShader(p, vs); gl.attachShader(p, fs); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { console.warn('wave link:', gl.getProgramInfoLog(p)); return null; }
    return p;
  }

  var pFluid = program(FLUID), pPixel = program(PIXEL);
  if (!pFluid || !pPixel) { canvas.style.display = 'none'; return; }

  var buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

  var fbo = gl.createFramebuffer();
  var fluidTex = gl.createTexture();
  var fw = 0, fh = 0;

  function resize() {
    var w = Math.max(1, hero.clientWidth);
    var h = Math.max(1, hero.clientHeight);
    canvas.width = w; canvas.height = h;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    gl.viewport(0, 0, w, h);
    fw = Math.max(2, Math.round(w * 0.5)); fh = Math.max(2, Math.round(h * 0.5));
    gl.bindTexture(gl.TEXTURE_2D, fluidTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, fw, fh, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, fluidTex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  var mouse = { x: 0.5, y: 0.5 };
  hero.addEventListener('pointermove', function (e) {
    var r = canvas.getBoundingClientRect();
    mouse.x = (e.clientX - r.left) / r.width;
    mouse.y = 1.0 - (e.clientY - r.top) / r.height;
  }, { passive: true });

  var t0 = performance.now(), raf = 0, visible = true, lastDraw = 0;

  function frame(now) {
    if (!visible || document.hidden) return;
    if (now - lastDraw < 32) { raf = requestAnimationFrame(frame); return; }
    lastDraw = now;
    var time = reduced ? 3.2 : (now - t0) / 1000;

    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.viewport(0, 0, fw, fh);
    gl.useProgram(pFluid);
    gl.uniform1f(gl.getUniformLocation(pFluid, 'uTime'), time);
    gl.uniform2f(gl.getUniformLocation(pFluid, 'uRes'), fw, fh);
    gl.uniform3f(gl.getUniformLocation(pFluid, 'uColor1'), 0.196, 0.941, 0.549);
    gl.uniform3f(gl.getUniformLocation(pFluid, 'uColor2'), 1.0, 1.0, 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.useProgram(pPixel);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, fluidTex);
    gl.uniform1i(gl.getUniformLocation(pPixel, 'uFluid'), 0);
    gl.uniform1f(gl.getUniformLocation(pPixel, 'uTime'), time);
    gl.uniform2f(gl.getUniformLocation(pPixel, 'uRes'), canvas.width, canvas.height);
    gl.uniform2f(gl.getUniformLocation(pPixel, 'uMouse'), mouse.x, mouse.y);
    gl.uniform1f(gl.getUniformLocation(pPixel, 'uPixelSize'), 5.0);
    gl.uniform1f(gl.getUniformLocation(pPixel, 'uPixelGap'), 2.0);
    gl.uniform1f(gl.getUniformLocation(pPixel, 'uThreshold'), 0.87);
    gl.uniform1f(gl.getUniformLocation(pPixel, 'uGreenRatio'), 0.49);
    gl.uniform3f(gl.getUniformLocation(pPixel, 'uGreen'), 50.0/255.0, 240.0/255.0, 140.0/255.0);
    gl.uniform3f(gl.getUniformLocation(pPixel, 'uWhite'), 1.0, 1.0, 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);

    if (!reduced) raf = requestAnimationFrame(frame);
  }

  function start() { cancelAnimationFrame(raf); lastDraw = 0; raf = requestAnimationFrame(frame); }

  if ('ResizeObserver' in window) new ResizeObserver(resize).observe(hero);
  else window.addEventListener('resize', resize);

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      visible = es[0].isIntersecting;
      if (visible) start(); else cancelAnimationFrame(raf);
    }, { threshold: 0.02 }).observe(hero);
  }

  resize();
  start();
})();
