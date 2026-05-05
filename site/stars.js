/* Game of Cards — constellation field
   Vanilla, no dependencies. Drawn into <canvas class="starfield">.
   ============================================================ */
(function () {
  const canvas = document.querySelector('.starfield');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const DENSITY = 0.5;          // 0..1 — number of stars
  const ACCENT  = '#c9a875';    // gold

  let raf, dpr;
  const points = [];

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = window.innerWidth;
    const H = Math.max(window.innerHeight, 700);
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);

    const count = Math.round(40 + DENSITY * 110);
    points.length = 0;
    for (let i = 0; i < count; i++) {
      points.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.08,
        vy: (Math.random() - 0.5) * 0.08,
        r: Math.random() * 1.2 + 0.4,
      });
    }
  }

  function frame() {
    const W = canvas.width / dpr;
    const H = canvas.height / dpr;
    ctx.clearRect(0, 0, W, H);

    const maxDist = 130;
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;

      for (let j = i + 1; j < points.length; j++) {
        const q = points[j];
        const dx = p.x - q.x, dy = p.y - q.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < maxDist) {
          const a = (1 - d / maxDist) * 0.18;
          ctx.strokeStyle = 'rgba(201, 207, 219, ' + a + ')';
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(q.x, q.y);
          ctx.stroke();
        }
      }
    }
    for (const p of points) {
      ctx.fillStyle = 'rgba(201, 207, 219, 0.45)';
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = ACCENT;
    for (let i = 0; i < points.length; i += 17) {
      const p = points[i];
      ctx.globalAlpha = 0.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    raf = requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener('resize', resize);
  frame();
})();
