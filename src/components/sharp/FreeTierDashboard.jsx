import { useApi } from '../../hooks/useApi';

export default function FreeTierDashboard({ onUpgrade }) {
  const { data: todayData } = useApi('/picks/today');
  const todayIsPick = todayData?.type === 'pick';
  const todayIsPass = todayData?.type === 'pass';

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
          marginBottom: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
            marginBottom: '16px',
          }}>Model Performance</div>

          <StepChart />

          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            marginTop: '16px',
          }}>
            The Sharp Picks model prioritizes restraint over volume. Full performance metrics are available for{' '}
            <span onClick={onUpgrade} style={{
              color: 'var(--blue-primary)', cursor: 'pointer', textDecoration: 'underline',
            }}>Pro members</span>.
          </p>
        </div>

        <SectionLabel>Behavioral Edge</SectionLabel>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--green-profit)',
            marginBottom: '16px',
          }}>Discipline Profile</div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <DisciplineBullet text="Selectivity: Lower than industry average" />
            <DisciplineBullet text="Passes > Picks most days" />
            <DisciplineBullet text="Days without a bet are intentional" />
          </div>

          <div style={{
            marginTop: '20px', paddingTop: '16px',
            borderTop: '1px solid var(--stroke-subtle)',
          }}>
            <p style={{
              fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5',
            }}>
              Discipline metrics are fully quantified in{' '}
              <span onClick={onUpgrade} style={{
                color: 'var(--green-profit)', cursor: 'pointer', fontWeight: 600,
              }}>Pro</span>.
            </p>
          </div>
        </div>

        <SectionLabel>Today</SectionLabel>

        {todayIsPick && (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '20px',
            border: '1px solid rgba(52, 211, 153, 0.25)', padding: '20px',
            marginBottom: '16px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px', fontWeight: 700,
              letterSpacing: '2px', textTransform: 'uppercase',
              color: 'var(--green-profit)',
              marginBottom: '10px',
            }}>Qualified Edge Detected</div>
            <div style={{
              fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px',
            }}>
              {todayData.away_team} @ {todayData.home_team}
            </div>
            <div style={{
              marginTop: '16px', padding: '14px',
              background: 'rgba(255,255,255,0.02)',
              border: '1px dashed var(--stroke-muted)',
              borderRadius: '12px', textAlign: 'center',
            }}>
              <div style={{ fontSize: '14px', marginBottom: '8px', opacity: 0.5 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" style={{ verticalAlign: 'middle' }}>
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0110 0v4"/>
                </svg>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.5' }}>
                Side, line, and edge available for Pro members
              </p>
            </div>
            <button onClick={onUpgrade} style={{
              width: '100%', padding: '14px', marginTop: '14px',
              background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
              border: 'none', borderRadius: '12px',
              color: '#fff', fontSize: '14px', fontWeight: 700,
              cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}>Unlock This Pick</button>
          </div>
        )}

        {todayIsPass && (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '20px',
            border: '1px solid var(--stroke-subtle)', padding: '20px',
            marginBottom: '16px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px', fontWeight: 700,
              letterSpacing: '2px', textTransform: 'uppercase',
              color: 'var(--text-tertiary)',
              marginBottom: '10px',
            }}>No Pick Today</div>
            <p style={{
              fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            }}>
              Model analyzed {todayData.games_analyzed} games. No edge above threshold.
              This is the discipline working as intended.
            </p>
          </div>
        )}

        {!todayIsPick && !todayIsPass && (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '20px',
            border: '1px solid var(--stroke-subtle)', padding: '20px',
            marginBottom: '16px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px', fontWeight: 700,
              letterSpacing: '2px', textTransform: 'uppercase',
              color: todayData?.type === 'allstar_break' ? 'rgba(99,102,241,0.8)' : 'var(--gold-pro)',
              marginBottom: '10px',
            }}>{todayData?.type === 'allstar_break' ? 'All-Star Break' : todayData?.type === 'off_day' ? 'No Games' : 'Waiting'}</div>
            <p style={{
              fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            }}>
              {todayData?.message || 'The model has not run yet today. Check back when games are available.'}
            </p>
          </div>
        )}

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

function StepChart() {
  const steps = [
    { x: 0, y: 70 }, { x: 40, y: 70 },
    { x: 40, y: 55 }, { x: 80, y: 55 },
    { x: 80, y: 60 }, { x: 120, y: 60 },
    { x: 120, y: 45 }, { x: 160, y: 45 },
    { x: 160, y: 35 }, { x: 200, y: 35 },
    { x: 200, y: 25 }, { x: 240, y: 25 },
    { x: 240, y: 20 }, { x: 280, y: 20 },
  ];

  const pathD = steps.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');

  return (
    <div style={{ opacity: 0.35 }}>
      <svg viewBox="0 0 280 80" style={{ width: '100%', display: 'block' }}>
        <line x1="0" y1="75" x2="280" y2="75" stroke="var(--stroke-subtle)" strokeWidth="0.5" />
        <path d={pathD} fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function DisciplineBullet({ text }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        backgroundColor: 'var(--text-tertiary)',
        marginTop: '6px', flexShrink: 0,
      }} />
      <span style={{ fontSize: '14px', color: 'var(--text-primary)', lineHeight: '1.5' }}>{text}</span>
    </div>
  );
}
