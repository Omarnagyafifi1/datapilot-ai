import { useEffect, useRef } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export function Layout({ children, activeView, setActiveView, selectedSource, selectedSourceId, dataSources, onSelectSource, themeMode, onChangeTheme }) {
  const isDark = themeMode === 'dark';
  const dotCanvasRef = useRef(null);

  useEffect(() => {
    if (!isDark) return undefined;

    const canvas = dotCanvasRef.current;
    if (!canvas) return undefined;

    const context = canvas.getContext('2d');
    if (!context) return undefined;

    const pointer = { x: -1000, y: -1000, active: false };
    const dots = [];
    let frameId = 0;
    let width = 0;
    let height = 0;
    let pixelRatio = 1;

    const buildDots = () => {
      dots.length = 0;

      const spacing = 24;
      const columns = Math.ceil(width / spacing) + 2;
      const rows = Math.ceil(height / spacing) + 2;

      for (let row = 0; row < rows; row += 1) {
        for (let column = 0; column < columns; column += 1) {
          const baseX = column * spacing - spacing;
          const baseY = row * spacing - spacing;
          dots.push({
            baseX,
            baseY,
            x: baseX,
            y: baseY,
            vx: 0,
            vy: 0,
            size: (column + row) % 5 === 0 ? 1.35 : 1,
          });
        }
      }
    };

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.max(1, Math.floor(width * pixelRatio));
      canvas.height = Math.max(1, Math.floor(height * pixelRatio));
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      buildDots();
    };

    const draw = () => {
      context.clearRect(0, 0, width, height);

      for (const dot of dots) {
        const pointerDx = dot.x - pointer.x;
        const pointerDy = dot.y - pointer.y;
        const pointerDistance = Math.hypot(pointerDx, pointerDy);
        const influence = pointer.active ? Math.max(0, 1 - pointerDistance / 110) : 0;

        if (influence > 0) {
          const angle = Math.atan2(pointerDy, pointerDx);
          const push = influence * influence * 3.4;
          dot.vx += Math.cos(angle) * push;
          dot.vy += Math.sin(angle) * push;
        }

        dot.vx += (dot.baseX - dot.x) * 0.035;
        dot.vy += (dot.baseY - dot.y) * 0.035;
        dot.vx *= 0.82;
        dot.vy *= 0.82;
        dot.x += dot.vx;
        dot.y += dot.vy;

        const drift = Math.min(1, Math.hypot(dot.x - dot.baseX, dot.y - dot.baseY) / 24);
        const opacity = 0.2 + drift * 0.34;
        context.beginPath();
        context.fillStyle = `rgba(226, 232, 240, ${opacity})`;
        context.arc(dot.x, dot.y, dot.size + drift * 0.45, 0, Math.PI * 2);
        context.fill();
      }

      frameId = window.requestAnimationFrame(draw);
    };

    const updatePointer = (event) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
      pointer.active = pointer.x >= 0 && pointer.x <= rect.width && pointer.y >= 0 && pointer.y <= rect.height;
    };

    const resetPointer = () => {
      pointer.active = false;
      pointer.x = -1000;
      pointer.y = -1000;
    };

    const resizeObserver = new ResizeObserver(resizeCanvas);
    resizeCanvas();
    resizeObserver.observe(canvas);
    window.addEventListener('pointermove', updatePointer, { passive: true });
    window.addEventListener('pointerleave', resetPointer);
    frameId = window.requestAnimationFrame(draw);

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      window.removeEventListener('pointermove', updatePointer);
      window.removeEventListener('pointerleave', resetPointer);
    };
  }, [isDark]);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      <Sidebar activeView={activeView} setActiveView={setActiveView} themeMode={themeMode} onChangeTheme={onChangeTheme} />
      <div className="flex-1 flex flex-col relative overflow-hidden">
        <Header 
          selectedSource={selectedSource} 
          selectedSourceId={selectedSourceId} 
          dataSources={dataSources} 
          onSelectSource={onSelectSource} 
        />
        <main className="flex-1 overflow-hidden relative">
          <div
            className="absolute inset-0 pointer-events-none transition-colors duration-300"
            style={{
              zIndex: 0,
              background: isDark
                ? 'radial-gradient(circle at 50% 0%, rgba(15, 23, 42, 0.78) 0%, rgba(2, 6, 23, 0.98) 42%, rgba(0, 0, 0, 1) 100%)'
                : 'radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.92) 0%, rgba(246, 247, 251, 0.98) 65%)',
            }}
          />
          {isDark ? (
            <canvas
              ref={dotCanvasRef}
              className="absolute inset-0 h-full w-full pointer-events-none transition-opacity duration-300"
              style={{
                zIndex: 2,
                opacity: 0.82,
                mixBlendMode: 'screen',
              }}
            />
          ) : (
            <div
              className="absolute inset-0 pointer-events-none transition-opacity duration-300"
              style={{
                backgroundImage: 'radial-gradient(circle, rgba(15,23,42,0.18) 1px, transparent 0.95px)',
                backgroundSize: '40px 40px',
                opacity: 0.04,
                zIndex: 2,
              }}
            />
          )}
          
          <div className="relative z-10 h-full overflow-y-auto no-scrollbar">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
