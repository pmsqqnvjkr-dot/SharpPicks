export default function FreeTierDashboard({ onUpgrade }) {
  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
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
        <SectionLabel>Performance</SectionLabel>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px', position: 'relative', overflow: 'hidden',
        }}>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '20px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '8px',
          }}>Performance is tracked</div>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            marginBottom: '20px',
          }}>
            Every pick and pass is logged with full transparency. Upgrade to see quantified results.
          </p>

          <AbstractChart />

          <div style={{
            position: 'absolute', bottom: '0', left: '0', right: '0', height: '80px',
            background: 'linear-gradient(transparent, var(--surface-1))',
            display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
            paddingBottom: '16px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px',
              color: 'var(--text-tertiary)', letterSpacing: '0.05em',
            }}>PRO MEMBERS SEE FULL METRICS</div>
          </div>
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px',
          marginBottom: '16px',
        }}>
          <BlurredStat label="Win Rate" />
          <BlurredStat label="ROI" />
          <BlurredStat label="Record" />
          <BlurredStat label="Streak" />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px',
        }}>
          <SectionLabel>Discipline Index</SectionLabel>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '8px',
          }}>Free teaches why. Pro shows how much.</div>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            marginBottom: '20px',
          }}>
            The model runs daily whether you're a free or Pro user. The difference is access to the full decision — side, line, and edge percentage.
          </p>
          <button onClick={onUpgrade} style={{
            width: '100%', padding: '14px',
            background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
            border: 'none', borderRadius: '12px',
            color: '#fff', fontSize: '15px', fontWeight: 700,
            cursor: 'pointer', fontFamily: 'var(--font-sans)',
          }}>See What Pro Unlocks</button>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '12px',
        }}>
          <SectionLabel>What Free Includes</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
            <FreeFeature text="Know if a pick exists today" />
            <FreeFeature text="See public win/loss record" />
            <FreeFeature text="Discipline metrics and selectivity" />
            <FreeFeature text="Pick history (teams and results only)" />
          </div>
        </div>

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '8px 20px 16px',
        }}>
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px', fontWeight: 600,
      letterSpacing: '2px', textTransform: 'uppercase',
      color: 'var(--text-tertiary)',
      marginBottom: '10px',
    }}>{children}</div>
  );
}

function AbstractChart() {
  const points = [20, 25, 22, 30, 28, 35, 32, 40, 38, 45, 42, 50, 48, 55];
  const h = 100, w = 260;
  const maxV = Math.max(...points);
  const minV = Math.min(...points);
  const range = maxV - minV || 1;

  const pathD = points.map((p, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - ((p - minV) / range) * (h - 20) - 10;
    return `${i === 0 ? 'M' : 'L'}${x},${y}`;
  }).join(' ');

  return (
    <div style={{ opacity: 0.25, filter: 'blur(2px)', marginBottom: '40px' }}>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', display: 'block' }}>
        <defs>
          <linearGradient id="freeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--blue-primary)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--blue-primary)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${pathD} L${w},${h} L0,${h} Z`} fill="url(#freeGrad)" />
        <path d={pathD} fill="none" stroke="var(--blue-primary)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function BlurredStat({ label }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)', padding: '20px',
      textAlign: 'center', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '6px',
        filter: 'blur(8px)', userSelect: 'none',
      }}>--.--%</div>
      <div style={{
        fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.08em',
      }}>{label}</div>
      <div style={{
        position: 'absolute', inset: '0',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
      </div>
    </div>
  );
}

function FreeFeature({ text }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <span style={{ color: 'var(--green-profit)', fontSize: '12px' }}>&#10003;</span>
      <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{text}</span>
    </div>
  );
}
