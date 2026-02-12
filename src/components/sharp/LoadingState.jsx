export default function LoadingState() {
  return (
    <div style={{ padding: '0' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <svg viewBox="0 0 40 40" width="24" height="24" fill="none">
            <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
            <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
            <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
            <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
            <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 700,
            color: 'var(--text-primary)', letterSpacing: '2px', textTransform: 'uppercase',
          }}>Sharp Picks</span>
        </div>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          marginBottom: '20px',
        }}>
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            backgroundColor: 'var(--blue-primary)',
            animation: 'loadingPulse 1.5s ease-in-out infinite',
          }} />
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '12px',
            color: 'var(--text-secondary)', letterSpacing: '0.02em',
          }}>Checking today's model output...</span>
        </div>

        <SkeletonCard>
          <SkeletonBar width="40%" />
          <SkeletonBar height="48px" radius="10px" />
          <SkeletonBar width="65%" />
          <SkeletonBar width="50%" />
          <SkeletonBar height="80px" radius="10px" last />
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

        <SkeletonCard>
          <SkeletonBar width="45%" />
          <SkeletonBar width="80%" />
          <SkeletonBar width="60%" last />
        </SkeletonCard>
      </div>

      <style>{`
        @keyframes loadingPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
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
