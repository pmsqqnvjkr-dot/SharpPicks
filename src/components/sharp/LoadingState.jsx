export default function LoadingState() {
  return (
    <div style={{ padding: 0 }}>
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '60px 20px 40px',
      }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: 'var(--color-signal)',
          animation: 'live-pulse 2s ease-in-out infinite',
          marginBottom: '28px',
        }} />

        <h2 style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-label-size)', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-secondary)',
          marginBottom: '10px', textAlign: 'center',
        }}>Market Scan Active</h2>

        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--text-metric)', fontWeight: 400,
          color: 'var(--text-tertiary)',
          textAlign: 'center', lineHeight: '1.55', maxWidth: '280px',
        }}>
          Evaluating today's games...
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
        @keyframes skeleton-shimmer {
          0%, 100% { opacity: 0.06; }
          50% { opacity: 0.12; }
        }
      `}</style>
    </div>
  );
}

function SkeletonCard({ children }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      border: '1px solid var(--color-border)', padding: '20px',
      marginBottom: '12px',
    }}>
      {children}
    </div>
  );
}

function SkeletonBar({ width, height = '14px', radius = '6px', last = false }) {
  return (
    <div style={{
      width: width || '100%', height, borderRadius: radius,
      background: 'var(--surface-2)',
      animation: 'skeleton-shimmer 1.5s ease-in-out infinite',
      marginBottom: last ? 0 : '12px',
    }} />
  );
}
