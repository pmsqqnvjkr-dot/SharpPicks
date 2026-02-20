export default function LoadingState() {
  return (
    <div style={{ padding: '0' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        backgroundColor: '#0B1A2B',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <svg viewBox="0 0 40 40" width="22" height="22" fill="none" style={{ display: 'block', marginRight: '14px', transform: 'translateY(-1px)' }}>
            <path d="M20 2L4 9v12c0 10 6.5 18.5 16 21 9.5-2.5 16-11 16-21V9L20 2z" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none"/>
            <rect x="14" y="16" width="3" height="12" rx="1" fill="rgba(255,255,255,0.85)"/>
            <rect x="19" y="12" width="3" height="16" rx="1" fill="rgba(255,255,255,0.85)"/>
            <rect x="24" y="18" width="3" height="10" rx="1" fill="rgba(255,255,255,0.85)"/>
            <path d="M12 20L20 10L30 6" stroke="rgba(255,255,255,0.85)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
            <path d="M27 5l4 1-1 4" stroke="rgba(255,255,255,0.85)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          </svg>
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 600,
            color: 'rgba(255,255,255,0.9)', letterSpacing: '3.9px', textTransform: 'uppercase',
            lineHeight: 1,
          }}>SHARP<span style={{ opacity: 0.65, margin: '0 0.6em', fontWeight: 500 }}>||</span>PICKS</span>
        </div>
      </div>

      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '60px 20px 40px',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          marginBottom: '28px',
        }}>
          <div style={{
            width: '4px', height: '28px', borderRadius: '2px',
            backgroundColor: 'var(--text-secondary)',
            animation: 'barPulse 1.4s ease-in-out infinite',
          }} />
          <div style={{
            width: '4px', height: '28px', borderRadius: '2px',
            backgroundColor: 'var(--text-secondary)',
            animation: 'barPulse 1.4s ease-in-out infinite 0.2s',
          }} />
        </div>

        <h2 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '20px', fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '10px',
          textAlign: 'center',
        }}>Waiting for model</h2>

        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '14px', fontWeight: 400,
          color: 'var(--text-secondary)',
          textAlign: 'center',
          lineHeight: '1.55',
          maxWidth: '280px',
        }}>
          The system has not processed today's data yet. Signals will update as games are analyzed.
        </p>
      </div>

      <div style={{ padding: '0 20px' }}>
        <SkeletonCard>
          <SkeletonBar width="40%" />
          <SkeletonBar height="48px" radius="10px" />
          <SkeletonBar width="65%" />
          <SkeletonBar width="50%" last />
        </SkeletonCard>

        <SkeletonCard>
          <SkeletonBar width="35%" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <SkeletonBar height="60px" radius="10px" />
            <SkeletonBar height="60px" radius="10px" />
            <SkeletonBar height="60px" radius="10px" />
            <SkeletonBar height="60px" radius="10px" last />
          </div>
        </SkeletonCard>
      </div>

      <style>{`
        @keyframes barPulse {
          0%, 100% { opacity: 1; transform: scaleY(1); }
          50% { opacity: 0.3; transform: scaleY(0.7); }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </div>
  );
}

function SkeletonCard({ children }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '20px',
      border: '1px solid var(--stroke-subtle)', padding: '20px',
      marginBottom: '12px',
    }}>
      {children}
    </div>
  );
}

function SkeletonBar({ width, height = '14px', radius = '6px', last = false }) {
  return (
    <div style={{
      width: width || '100%', height,
      borderRadius: radius,
      background: 'linear-gradient(90deg, var(--surface-2) 25%, rgba(255,255,255,0.06) 50%, var(--surface-2) 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.8s ease-in-out infinite',
      marginBottom: last ? '0' : '12px',
    }} />
  );
}
