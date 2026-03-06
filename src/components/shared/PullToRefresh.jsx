import { useState, useRef, useCallback } from 'react';

export default function PullToRefresh({ onRefresh, children }) {
  const [pulling, setPulling] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startY = useRef(0);
  const containerRef = useRef(null);
  const threshold = 60;

  const onTouchStart = useCallback((e) => {
    if (containerRef.current && containerRef.current.scrollTop === 0) {
      startY.current = e.touches[0].clientY;
      setPulling(true);
    }
  }, []);

  const onTouchMove = useCallback((e) => {
    if (!pulling || refreshing) return;
    const diff = e.touches[0].clientY - startY.current;
    if (diff > 0) {
      setPullDistance(Math.min(diff * 0.4, threshold + 20));
    }
  }, [pulling, refreshing]);

  const onTouchEnd = useCallback(async () => {
    if (!pulling) return;
    if (pullDistance >= threshold && onRefresh) {
      setRefreshing(true);
      try { await onRefresh(); } catch {}
      setRefreshing(false);
    }
    setPullDistance(0);
    setPulling(false);
  }, [pulling, pullDistance, onRefresh]);

  const progress = Math.min(pullDistance / threshold, 1);

  return (
    <div
      ref={containerRef}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      style={{ position: 'relative', minHeight: '100%' }}
    >
      {(pullDistance > 0 || refreshing) && (
        <div style={{
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          height: refreshing ? '40px' : `${pullDistance}px`,
          transition: refreshing ? 'none' : 'height 0.1s',
          overflow: 'hidden',
        }}>
          <div style={{
            width: '24px', height: '24px', borderRadius: '50%',
            border: '2.5px solid var(--stroke-subtle)',
            borderTopColor: 'var(--blue-primary)',
            opacity: refreshing ? 1 : progress,
            transform: `rotate(${progress * 360}deg)`,
            animation: refreshing ? 'ptr-spin 0.8s linear infinite' : 'none',
            transition: 'opacity 0.15s',
          }} />
        </div>
      )}
      <style>{`@keyframes ptr-spin { to { transform: rotate(360deg); } }`}</style>
      {children}
    </div>
  );
}
