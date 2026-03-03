import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost, apiDelete } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import ResolutionScreen from './ResolutionScreen';

export default function UnifiedDashboard({ embedded = false }) {
  const { user } = useAuth();
  const { sport } = useSport();
  const [stats, setStats] = useState(null);
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showTrackModal, setShowTrackModal] = useState(false);
  const [selectedPick, setSelectedPick] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [resolutionPick, setResolutionPick] = useState(null);

  const loadData = async () => {
    try {
      if (user) {
        const [statsData, betsData] = await Promise.all([
          apiGet(sportQuery('/user/stats', sport)),
          apiGet(sportQuery('/bets', sport)),
        ]);
        setStats(statsData);
        setBets(betsData.bets || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [user, sport]);

  const handleSubmitBet = async (betData) => {
    try {
      const res = await apiPost('/bets', betData);
      if (res.success) {
        setShowTrackModal(false);
        setSelectedPick(null);
        await loadData();
      } else {
        alert(res.error || 'Failed to track bet');
      }
    } catch (e) {
      alert('Failed to track bet');
    }
  };

  const handleDelete = async (betId) => {
    try {
      const res = await apiDelete(`/bets/${betId}`);
      if (res.success) {
        setConfirmDelete(null);
        await loadData();
      }
    } catch (e) {
      alert('Failed to delete bet');
    }
  };

  if (!user) {
    return (
      <div style={{ padding: '0', paddingBottom: embedded ? '0' : '100px' }}>
        {!embedded && <DashHeader />}
        <div style={{ padding: '0 20px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)',
            padding: '40px 24px',
            textAlign: 'center',
          }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              backgroundColor: 'var(--surface-2)', margin: '0 auto 16px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
                <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
              </svg>
            </div>
            <p style={{ color: 'var(--text-primary)', fontSize: '16px', fontWeight: 600, fontFamily: 'var(--font-serif)', margin: '0 0 8px' }}>
              Your Performance
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6', margin: 0 }}>
              Sign in to track your bets and build your personal equity curve, win rate, and discipline metrics.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: '0' }}>
        {!embedded && <DashHeader />}
        <div style={{ padding: '20px' }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{
              height: i === 1 ? '280px' : '120px',
              backgroundColor: 'var(--surface-1)',
              borderRadius: '16px',
              marginBottom: '16px',
              animation: 'shimmer 1.5s ease-in-out infinite',
            }} />
          ))}
          <style>{`@keyframes shimmer { 0%, 100% { opacity: 0.5; } 50% { opacity: 0.3; } }`}</style>
        </div>
      </div>
    );
  }

  if (resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => setResolutionPick(null)} />;
  }

  const behavioral = stats?.behavioral || {};
  const totalPnl = stats?.totalProfit || 0;
  const roi = stats?.roi || 0;
  const wins = stats?.wins || 0;
  const losses = stats?.losses || 0;
  const record = `${wins}-${losses}`;
  const equityCurve = (stats?.equityCurve || []).map(p => ({ ...p, pnl: p.value }));
  const selectivity = behavioral.selectivity || 0;
  const avgDays = behavioral.avg_days_between || 0;
  const capitalPreserved = behavioral.capital_preserved || 0;
  const picksPassed = behavioral.picks_passed || 0;
  const industryAvg = behavioral.industry_avg || 78;
  const hasBets = stats?.totalBets > 0 || bets.length > 0;

  const pendingBets = bets.filter(b => !b.result);
  const settledBets = bets.filter(b => b.result);

  return (
    <div style={{ padding: '0', paddingBottom: embedded ? '0' : '100px' }}>
      {!embedded && <DashHeader />}

      <div style={{ padding: '0 20px' }}>
        <SectionLabel text="YOUR RESULTS" />

        {hasBets ? (
          <PerformanceCard
            totalPnl={totalPnl}
            roi={roi}
            record={record}
            equityCurve={equityCurve}
          />
        ) : (
          <EmptyPerformance />
        )}

        <div style={{ marginBottom: '16px' }}>
          <button onClick={() => setShowTrackModal(true)} style={{
            width: '100%', padding: '14px',
            backgroundColor: 'var(--blue-primary)', color: '#fff',
            border: 'none', borderRadius: '12px',
            fontSize: '14px', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Track a Bet
          </button>
        </div>

        {stats && stats.behavioral && (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '20px',
            border: '1px solid var(--stroke-subtle)', padding: '24px',
            marginBottom: '16px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
              letterSpacing: '2px', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: '16px',
            }}>Discipline Score</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Selectivity Rate</span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '22px',
                    color: 'var(--text-primary)', fontWeight: 700,
                  }}>{stats.behavioral.selectivity || 0}%</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                  Industry Avg: {stats.behavioral.industry_avg || 78}%
                </div>
              </div>
              <div style={{
                width: '56px', height: '56px', borderRadius: '14px',
                background: stats.behavioral.restraint_grade?.startsWith('A')
                  ? 'linear-gradient(135deg, rgba(52,211,153,0.15), rgba(52,211,153,0.05))'
                  : 'linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))',
                border: stats.behavioral.restraint_grade?.startsWith('A')
                  ? '1px solid rgba(52,211,153,0.3)'
                  : '1px solid var(--stroke-subtle)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 800,
                  color: stats.behavioral.restraint_grade?.startsWith('A') ? 'var(--green-profit)' : 'var(--text-primary)',
                }}>{stats.behavioral.restraint_grade || '—'}</span>
              </div>
            </div>
            <div style={{ position: 'relative', height: '28px', marginBottom: '16px' }}>
              <div style={{
                position: 'absolute', left: 0, right: 0, height: '6px', top: '11px',
                backgroundColor: 'var(--surface-2)', borderRadius: '3px',
              }} />
              <div style={{
                position: 'absolute', left: 0, top: '11px',
                width: `${Math.min(Math.max(stats.behavioral.selectivity || 0, 0), 100)}%`,
                height: '6px',
                background: 'linear-gradient(90deg, #34D399, #2563EB)',
                borderRadius: '3px',
              }} />
              <div style={{
                position: 'absolute', left: `${Math.min(Math.max(stats.behavioral.selectivity || 0, 0), 100)}%`,
                top: '5px', width: '3px', height: '18px',
                backgroundColor: 'var(--green-profit)', borderRadius: '2px',
                transform: 'translateX(-50%)',
              }} />
              <div style={{
                position: 'absolute', left: `${stats.behavioral.industry_avg || 78}%`,
                top: 0, transform: 'translateX(-50%)',
                fontSize: '8px', color: 'var(--text-tertiary)', whiteSpace: 'nowrap',
              }}>Industry ({stats.behavioral.industry_avg || 78}%)</div>
              <div style={{
                position: 'absolute', left: `${stats.behavioral.industry_avg || 78}%`,
                top: '11px', width: '1px', height: '6px',
                backgroundColor: 'var(--text-tertiary)', opacity: 0.5,
              }} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
              <div style={{ backgroundColor: 'var(--surface-2)', borderRadius: '10px', padding: '10px 12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>Picks Followed</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>{stats.behavioral.picks_followed || 0}</div>
              </div>
              <div style={{ backgroundColor: 'var(--surface-2)', borderRadius: '10px', padding: '10px 12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>Picks Passed</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>{stats.behavioral.picks_passed || 0}</div>
              </div>
            </div>
            <div style={{ paddingTop: '12px', borderTop: '1px solid var(--stroke-subtle)' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                Capital preserved: <span style={{
                  fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--green-profit)',
                }}>+${(stats.behavioral.capital_preserved || 0).toLocaleString()}</span> from avoided -EV spots
              </p>
            </div>
          </div>
        )}

        {pendingBets.length > 0 && (
          <BetsSection title={`Active (${pendingBets.length})`}>
            {pendingBets.map(bet => (
              <BetRow key={bet.id} bet={bet}
                confirmDelete={confirmDelete}
                setConfirmDelete={setConfirmDelete}
                onDelete={handleDelete}
              />
            ))}
          </BetsSection>
        )}

        {settledBets.length > 0 && (
          <BetsSection title={`Settled (${settledBets.length})`}>
            {settledBets.map(bet => (
              <BetRow key={bet.id} bet={bet}
                confirmDelete={confirmDelete}
                setConfirmDelete={setConfirmDelete}
                onDelete={handleDelete}
                onViewPick={setResolutionPick}
              />
            ))}
          </BetsSection>
        )}

        {hasBets && (
          <>
            <SectionLabel text="BEHAVIORAL EDGE" />

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              <MetricTile
                value={`${Math.round(selectivity)}%`}
                label="SELECTIVITY"
              />
              <MetricTile
                value={bets.length >= 2 ? (avgDays > 0 ? avgDays.toFixed(1) : '< 1') : bets.length === 1 ? '—' : '—'}
                label="DAYS / BET"
                tooltip="Time between bets is a feature, not inactivity. Patience is part of the edge structure."
              />
            </div>

            <CapitalPreservedCard
              amount={capitalPreserved}
              passes={picksPassed}
            />

            <SelectivitySpectrum
              selectivity={selectivity}
              industryAvg={industryAvg}
            />

            <BehavioralEdgeCard
              selectivity={selectivity}
              industryAvg={industryAvg}
            />
          </>
        )}

        <div style={{ padding: '20px 0', textAlign: 'center' }}>
          <p style={{
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: '13px', color: 'var(--text-secondary)',
            lineHeight: '1.5', marginBottom: '4px',
          }}>
            This dashboard measures discipline, not excitement.
          </p>
          <p style={{
            fontSize: '11px',
            color: 'var(--text-tertiary)',
            lineHeight: '1.5',
            fontFamily: 'var(--font-sans)',
            margin: 0,
          }}>
            Past performance does not guarantee future results.
            {'\n'}This analysis reflects probabilities, not certainty.
          </p>
        </div>
      </div>

      {showTrackModal && (
        <TrackBetModal
          initialPick={selectedPick}
          onClose={() => { setShowTrackModal(false); setSelectedPick(null); }}
          onSubmit={handleSubmitBet}
        />
      )}
    </div>
  );
}

function DashHeader() {
  return (
    <div style={{
      padding: '16px 20px 12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'linear-gradient(to bottom, #0E1A2B, #08121F)',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img src="/images/crest.png" alt="" width="26" height="26" style={{ display: 'block', marginRight: '16px', flexShrink: 0, objectFit: 'contain' }} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 600,
          letterSpacing: '3.9px',
          textTransform: 'uppercase',
          color: '#F2F4F8',
          lineHeight: 1,
        }}>
          SHARP<span style={{ opacity: 0.65, margin: '0 0.45em', fontWeight: 500, letterSpacing: '0.18em' }}>||</span>PICKS
        </span>
      </div>
      <div style={{
        width: '32px', height: '32px', borderRadius: '50%',
        backgroundColor: 'var(--surface-2)',
        border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
      </div>
    </div>
  );
}

function EmptyPerformance() {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '32px 24px',
      marginBottom: '16px',
      textAlign: 'center',
    }}>
      <div style={{
        width: '48px', height: '48px', borderRadius: '12px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 16px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <path d="M3 3v18h18"/>
          <path d="M7 16l4-8 4 4 4-8"/>
        </svg>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '2px',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        marginBottom: '8px',
      }}>
        PERFORMANCE
      </div>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)',
        lineHeight: '1.6', margin: 0,
      }}>
        Track your first bet to start building your personal performance dashboard.
      </p>
    </div>
  );
}

function SectionLabel({ text }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '11px',
      fontWeight: 600,
      letterSpacing: '2px',
      textTransform: 'uppercase',
      color: 'var(--green-profit)',
      marginBottom: '14px',
      marginTop: '8px',
    }}>
      {text}
    </div>
  );
}

function StatChip({ value, label, color }) {
  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-secondary)' }}>
      <strong style={{ color: color || 'var(--text-primary)', fontWeight: 700 }}>{value}</strong>{' '}
      <span style={{ fontSize: '12px' }}>{label}</span>
    </span>
  );
}

function InfoTooltip({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', marginLeft: '6px', verticalAlign: 'middle' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '18px', height: '18px', borderRadius: '50%',
          backgroundColor: open ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)',
          border: '1px solid var(--stroke-subtle)',
          color: 'var(--text-tertiary)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 0, fontSize: '11px', fontFamily: 'var(--font-sans)', fontWeight: 600,
          lineHeight: 1, transition: 'background-color 0.15s ease',
        }}
        aria-label="More info"
      >i</button>
      {open && (
        <div style={{
          position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)',
          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '10px', padding: '10px 12px',
          width: '220px', zIndex: 10,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}>
          <p style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '12px', color: 'var(--text-secondary)',
            lineHeight: '1.5', margin: 0,
            textTransform: 'none', letterSpacing: 'normal', fontWeight: 400,
          }}>{text}</p>
        </div>
      )}
    </span>
  );
}

function InfoCallout({ header, text }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: '12px' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0',
          color: 'var(--text-tertiary)', fontFamily: 'var(--font-sans)', fontSize: '12px',
          fontWeight: 500, transition: 'color 0.15s ease',
        }}
      >
        <span style={{
          width: '16px', height: '16px', borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.06)',
          border: '1px solid var(--stroke-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '10px', fontWeight: 600, lineHeight: 1, flexShrink: 0,
        }}>?</span>
        <span>{header}</span>
        <span style={{
          fontSize: '10px', transition: 'transform 0.2s ease',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>▾</span>
      </button>
      <div style={{
        maxHeight: open ? '200px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 0.25s ease',
      }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '10px', padding: '12px 14px', marginTop: '6px',
        }}>
          <p style={{
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: '12px', color: 'var(--text-secondary)',
            lineHeight: '1.6', margin: 0,
          }}>{text}</p>
        </div>
      </div>
    </div>
  );
}

function PerformanceCard({ totalPnl, roi, record, equityCurve }) {
  const isPositive = totalPnl >= 0;
  const color = isPositive ? 'var(--green-profit)' : 'var(--red-loss)';

  const resolved = equityCurve.filter(p => p.result === 'W' || p.result === 'L');
  let unitTotal = 0;
  resolved.forEach(p => { unitTotal += p.result === 'W' ? 0.91 : -1; });
  unitTotal = parseFloat(unitTotal.toFixed(1));
  const unitColor = unitTotal >= 0 ? 'var(--green-profit)' : 'var(--red-loss)';

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '20px',
      border: '1px solid var(--stroke-subtle)',
      padding: '24px',
      marginBottom: '16px',
      overflow: 'hidden',
    }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '42px', fontWeight: 800,
              color,
              lineHeight: 1,
              marginBottom: '8px',
            }}>
              {isPositive ? '+' : '-'}${Math.abs(totalPnl).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px', color: 'var(--text-tertiary)',
              letterSpacing: '0.5px',
              marginBottom: '10px',
            }}>
              Your Tracked Bets · Actual Stakes
            </div>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <StatChip
                value={`${roi >= 0 ? '+' : ''}${roi}%`}
                label="ROI"
                color={roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
              />
              <InfoTooltip text="This reflects your actual execution, not the model's standardized stakes. Stake sizing discipline affects long term performance." />
              <StatChip value={record} label="Record" />
              {resolved.length >= 1 && (
                <StatChip
                  value={`${unitTotal >= 0 ? '+' : ''}${unitTotal}u`}
                  label={`${resolved.length} bets · 1u flat`}
                  color={unitColor}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {equityCurve.length > 1 ? (
        <div style={{ margin: '16px -24px -24px' }}>
          <BloombergChart data={equityCurve} color={color} isPositive={isPositive} />
        </div>
      ) : (
        <div style={{
          height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', fontSize: '11px',
        }}>
          Need 2+ settled bets for chart
        </div>
      )}
    </div>
  );
}

function BloombergChart({ data, color, isPositive }) {
  const height = 200;
  const width = 400;
  const padL = 48;
  const padR = 8;
  const padT = 8;
  const padB = 24;

  const values = data.map(d => d.pnl);
  const allValues = [0, ...values];
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const range = maxVal - minVal || 1;
  const buffer = range * 0.08;

  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const getX = (i) => padL + (i / (data.length - 1)) * chartW;
  const getY = (v) => padT + chartH - ((v - (minVal - buffer)) / (range + buffer * 2)) * chartH;

  const zeroY = getY(0);

  const points = data.map((d, i) => ({ x: getX(i), y: getY(d.pnl) }));

  const pathD = points.map((p, i) => {
    if (i === 0) return `M${p.x},${p.y}`;
    const prev = points[i - 1];
    const tension = 0.3;
    const dx = p.x - prev.x;
    const cp1x = prev.x + dx * tension;
    const cp2x = p.x - dx * tension;
    return `C${cp1x},${prev.y} ${cp2x},${p.y} ${p.x},${p.y}`;
  }).join(' ');

  const lastPt = points[points.length - 1];
  const firstPt = points[0];
  const areaD = pathD +
    ` L${lastPt.x},${zeroY} L${firstPt.x},${zeroY} Z`;

  const ticks = [];
  const nTicks = 5;
  const step = range / (nTicks - 1);
  for (let i = 0; i < nTicks; i++) {
    const v = minVal + step * i;
    const rounded = Math.round(v);
    if (!ticks.find(t => t.value === rounded)) {
      ticks.push({ value: rounded, y: getY(rounded) });
    }
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', display: 'block' }}>
      <defs>
        <linearGradient id="bbgGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" />
          <stop offset="80%" stopColor={color} stopOpacity="0.02" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={padL} y1={t.y} x2={width - padR} y2={t.y}
            stroke="rgba(255,255,255,0.04)" strokeWidth="0.5" />
          <text x={padL - 6} y={t.y + 3}
            textAnchor="end" fill="var(--text-tertiary)"
            fontSize="9" fontFamily="var(--font-mono)" fontWeight="500">
            {t.value >= 0 ? '' : '-'}${Math.abs(t.value)}
          </text>
        </g>
      ))}

      <line x1={padL} y1={zeroY} x2={width - padR} y2={zeroY}
        stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />

      <path d={areaD} fill="url(#bbgGrad)" />

      <path d={pathD} fill="none"
        stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

      <circle cx={lastPt.x} cy={lastPt.y} r="3" fill={color} />
      <circle cx={lastPt.x} cy={lastPt.y} r="6" fill={color} fillOpacity="0.15" />

      {data.length <= 20 && data.map((d, i) => {
        const label = d.date ? d.date.substring(5) : '';
        if (data.length > 10 && i % 2 !== 0 && i !== data.length - 1) return null;
        return (
          <text key={i} x={getX(i)} y={height - 4}
            textAnchor="middle" fill="var(--text-tertiary)"
            fontSize="8" fontFamily="var(--font-mono)">
            {label}
          </text>
        );
      })}
    </svg>
  );
}


function UnitGrowthCard({ equityCurve }) {
  const resolved = equityCurve.filter(p => p.result === 'W' || p.result === 'L');
  if (resolved.length < 2) return null;

  let runningUnits = 0;
  const curveData = resolved.map(p => {
    const unitPnl = p.result === 'W' ? 0.91 : -1;
    runningUnits += unitPnl;
    return { ...p, unitPnl, units: parseFloat(runningUnits.toFixed(2)) };
  });

  const currentUnits = curveData[curveData.length - 1]?.units || 0;
  const isPositive = currentUnits >= 0;
  const color = isPositive ? 'var(--green-profit)' : 'var(--red-loss)';

  const height = 160;
  const width = 400;
  const padL = 48;
  const padR = 8;
  const padT = 8;
  const padB = 24;

  const values = curveData.map(d => d.units);
  const allValues = [0, ...values];
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const range = maxVal - minVal || 1;
  const buffer = range * 0.1;

  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const getX = (i) => padL + (i / (curveData.length - 1)) * chartW;
  const getY = (v) => padT + chartH - ((v - (minVal - buffer)) / (range + buffer * 2)) * chartH;

  const zeroY = getY(0);

  const points = curveData.map((d, i) => ({ x: getX(i), y: getY(d.units) }));

  const pathD = points.map((p, i) => {
    if (i === 0) return `M${p.x},${p.y}`;
    const prev = points[i - 1];
    const tension = 0.3;
    const dx = p.x - prev.x;
    const cp1x = prev.x + dx * tension;
    const cp2x = p.x - dx * tension;
    return `C${cp1x},${prev.y} ${cp2x},${p.y} ${p.x},${p.y}`;
  }).join(' ');

  const lastPt = points[points.length - 1];
  const firstPt = points[0];
  const areaD = pathD +
    ` L${lastPt.x},${zeroY} L${firstPt.x},${zeroY} Z`;

  const ticks = [];
  const nTicks = 4;
  const step = range / (nTicks - 1);
  for (let i = 0; i < nTicks; i++) {
    const v = minVal + step * i;
    const rounded = parseFloat(v.toFixed(1));
    ticks.push({ value: rounded, y: getY(rounded) });
  }

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '20px',
      border: '1px solid var(--stroke-subtle)',
      marginBottom: '16px',
      overflow: 'hidden',
    }}>
      <div style={{ padding: '20px 20px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px', fontWeight: 600,
              letterSpacing: '2px', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: '8px',
            }}>Unit Growth</div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '28px', fontWeight: 800,
              color,
              lineHeight: 1,
            }}>
              {isPositive ? '+' : ''}{currentUnits.toFixed(1)}u
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px', fontWeight: 600,
              color: 'var(--text-tertiary)',
              marginTop: '4px',
            }}>
              {curveData.length} bets · 1u flat
            </div>
          </div>
          <div style={{ display: 'flex', gap: '4px' }}>
            {curveData.slice(-10).map((d, i) => (
              <div key={i} style={{
                width: '6px', height: '16px',
                borderRadius: '2px',
                backgroundColor: d.result === 'W' ? 'rgba(52,211,153,0.4)' : 'rgba(239,68,68,0.4)',
              }} />
            ))}
          </div>
        </div>
      </div>

      <div style={{ margin: '12px 0 0' }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', display: 'block' }}>
          <defs>
            <linearGradient id="unitGrowthGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.15" />
              <stop offset="80%" stopColor={color} stopOpacity="0.02" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>

          {ticks.map((t, i) => (
            <g key={i}>
              <line x1={padL} y1={t.y} x2={width - padR} y2={t.y}
                stroke="rgba(255,255,255,0.04)" strokeWidth="0.5" />
              <text x={padL - 6} y={t.y + 3}
                textAnchor="end" fill="var(--text-tertiary)"
                fontSize="9" fontFamily="var(--font-mono)" fontWeight="500">
                {t.value >= 0 ? '+' : ''}{t.value}u
              </text>
            </g>
          ))}

          <line x1={padL} y1={zeroY} x2={width - padR} y2={zeroY}
            stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />

          <path d={areaD} fill="url(#unitGrowthGrad)" />

          <path d={pathD} fill="none"
            stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

          <circle cx={lastX} cy={lastY} r="3" fill={color} />
          <circle cx={lastX} cy={lastY} r="6" fill={color} fillOpacity="0.15" />

          {curveData.length <= 20 && curveData.map((d, i) => {
            const label = d.date ? d.date.substring(5) : '';
            if (curveData.length > 10 && i % 2 !== 0 && i !== curveData.length - 1) return null;
            return (
              <text key={i} x={getX(i)} y={height - 4}
                textAnchor="middle" fill="var(--text-tertiary)"
                fontSize="8" fontFamily="var(--font-mono)">
                {label}
              </text>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function BetsSection({ title, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '8px',
      }}>
        {title}
      </div>
      <div style={{
        backgroundColor: 'var(--surface-1)',
        borderRadius: '16px',
        border: '1px solid var(--stroke-subtle)',
        overflow: 'hidden',
      }}>
        {children}
      </div>
    </div>
  );
}

function BetRow({ bet, confirmDelete, setConfirmDelete, onDelete, onViewPick }) {
  const isClickable = bet.result && bet.linked_pick;

  const rowRef = useRef(null);
  const startX = useRef(0);
  const currentX = useRef(0);
  const swipingRef = useRef(false);
  const [offset, setOffset] = useState(0);
  const [showConfirm, setShowConfirm] = useState(false);
  const deleteThreshold = 80;

  const onTouchStart = useCallback((e) => {
    startX.current = e.touches[0].clientX;
    currentX.current = 0;
    swipingRef.current = true;
  }, []);

  const onTouchMove = useCallback((e) => {
    if (!swipingRef.current) return;
    const diff = startX.current - e.touches[0].clientX;
    if (diff > 0) {
      const clamped = Math.min(diff, deleteThreshold + 20);
      currentX.current = clamped;
      setOffset(clamped);
    } else {
      currentX.current = 0;
      setOffset(0);
    }
  }, []);

  const onTouchEnd = useCallback(() => {
    swipingRef.current = false;
    if (currentX.current >= deleteThreshold) {
      setOffset(deleteThreshold);
      setShowConfirm(true);
    } else {
      setOffset(0);
      setShowConfirm(false);
    }
  }, []);

  const resetSwipe = () => {
    setOffset(0);
    setShowConfirm(false);
  };

  return (
    <div style={{
      position: 'relative',
      overflow: 'hidden',
      borderBottom: '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        position: 'absolute', right: 0, top: 0, bottom: 0,
        width: `${deleteThreshold + 20}px`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: showConfirm ? '#dc2626' : 'rgba(239, 68, 68, 0.85)',
        transition: showConfirm ? 'background-color 0.2s' : 'none',
      }}>
        {showConfirm ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
            <button onClick={() => { onDelete(bet.id); resetSwipe(); }} style={{
              background: 'none', border: 'none', color: '#fff',
              fontSize: '13px', fontWeight: 700, cursor: 'pointer',
              fontFamily: 'var(--font-sans)', padding: '6px 12px',
            }}>Delete</button>
            <button onClick={resetSwipe} style={{
              background: 'none', border: 'none',
              color: 'rgba(255,255,255,0.7)', fontSize: '11px',
              cursor: 'pointer', fontFamily: 'var(--font-sans)', padding: '2px 8px',
            }}>Cancel</button>
          </div>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        )}
      </div>

      <div
        ref={rowRef}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onClick={() => { if (isClickable && onViewPick && offset === 0) onViewPick(bet.linked_pick); }}
        style={{
          padding: '14px 16px',
          backgroundColor: 'var(--surface-1)',
          transform: `translateX(-${offset}px)`,
          transition: swipingRef.current ? 'none' : 'transform 0.25s ease',
          position: 'relative', zIndex: 1,
          cursor: isClickable ? 'pointer' : 'default',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              {bet.pick}
              {isClickable && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              )}
            </div>
            {bet.game && (
              <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-tertiary)', marginTop: '2px' }}>
                {bet.game}
              </div>
            )}
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
              color: 'var(--text-tertiary)', marginTop: '4px',
            }}>
              ${bet.bet_amount} at {bet.odds != null ? (bet.odds > 0 ? `+${bet.odds}` : bet.odds) : '-110'}
              {bet.to_win ? ` · to win $${bet.to_win}` : ''}
            </div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '12px' }}>
            {bet.result ? (
              <div>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 500,
                  color: bet.result === 'W' ? 'var(--green-profit)' : bet.result === 'L' ? 'var(--red-loss)' : 'var(--text-secondary)',
                }}>
                  {bet.result === 'W' ? `+$${Math.abs(bet.profit || 0).toFixed(0)}` : bet.result === 'L' ? `-$${Math.abs(bet.profit || 0).toFixed(0)}` : 'Push'}
                </span>
              </div>
            ) : (
              <div style={{
                padding: '6px 12px',
                fontSize: '11px', fontWeight: 600,
                fontFamily: 'var(--font-mono)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                backgroundColor: 'rgba(79, 134, 247, 0.08)',
                color: 'var(--blue-primary)',
                border: '1px solid rgba(79, 134, 247, 0.2)',
                borderRadius: '8px',
              }}>Pending</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricTile({ value, label, tooltip }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: '1px solid var(--stroke-subtle)',
      padding: '18px 16px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '28px', fontWeight: 700,
        color: 'var(--text-primary)',
        lineHeight: 1.1, marginBottom: '6px',
      }}>
        {value}
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 600,
        letterSpacing: '1.5px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {label}
        {tooltip && <InfoTooltip text={tooltip} />}
      </div>
    </div>
  );
}

function CapitalPreservedCard({ amount, passes }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '20px',
      marginBottom: '16px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '12px',
      }}>
        CAPITAL PRESERVED
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '36px', fontWeight: 700,
        color: 'var(--green-profit)',
        lineHeight: 1.1, marginBottom: '10px',
      }}>
        +${amount.toLocaleString()}
      </div>

      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '14px',
        color: 'var(--text-secondary)',
        lineHeight: '1.5',
        margin: '0 0 12px 0',
      }}>
        Estimated bankroll saved by passing on {passes} picks you didn't follow this season.
      </p>

      <InfoCallout
        header="Why This Matters"
        text="Money saved by passing low conviction plays compounds just like wins do. Discipline protects downside before upside appears."
      />
    </div>
  );
}

function SelectivitySpectrum({ selectivity, industryAvg }) {
  const position = Math.min(100, Math.max(0, selectivity));
  const avgPosition = Math.min(100, Math.max(0, industryAvg));

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '20px',
      marginBottom: '16px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '16px',
      }}>
        SELECTIVITY SPECTRUM
      </div>

      <div style={{ position: 'relative', marginBottom: '12px' }}>
        <div style={{
          position: 'absolute',
          left: `${avgPosition}%`,
          top: '-18px',
          transform: 'translateX(-50%)',
          fontFamily: 'var(--font-mono)',
          fontSize: '9px',
          color: 'var(--text-tertiary)',
          whiteSpace: 'nowrap',
        }}>
          Industry avg ({industryAvg}%)
        </div>

        <div style={{
          width: '100%', height: '6px',
          backgroundColor: 'var(--surface-2)',
          borderRadius: '3px',
          position: 'relative', overflow: 'visible',
        }}>
          <div style={{
            position: 'absolute',
            left: `${avgPosition}%`,
            top: '-2px',
            width: '1px', height: '10px',
            backgroundColor: 'var(--text-tertiary)',
          }} />

          <div style={{
            position: 'absolute',
            left: `${position}%`,
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: '16px', height: '16px',
            borderRadius: '4px',
            backgroundColor: 'var(--text-primary)',
            border: '2px solid var(--bg-primary)',
          }} />
        </div>
      </div>

      <div style={{
        display: 'flex', justifyContent: 'space-between', marginBottom: '16px',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
          letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--text-tertiary)',
        }}>SHARP (SELECTIVE)</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
          letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--text-tertiary)',
        }}>SQUARE (VOLUME)</span>
      </div>

      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '14px', color: 'var(--text-secondary)',
        lineHeight: '1.5', margin: 0,
      }}>
        You bet on <strong style={{ color: 'var(--text-primary)' }}>{Math.round(selectivity)}%</strong> of opportunities. The industry average is {industryAvg}%. Fewer decisions, better decisions.
      </p>
    </div>
  );
}

function BehavioralEdgeCard({ selectivity, industryAvg }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '20px',
      marginBottom: '8px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--green-profit)', marginBottom: '12px',
      }}>
        BEHAVIORAL EDGE
      </div>

      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '14px', color: 'var(--text-secondary)',
        lineHeight: '1.5', margin: '0 0 12px 0',
      }}>
        Your selectivity rate is <strong style={{ color: 'var(--text-primary)' }}>{Math.round(selectivity)}%</strong> — industry average is {industryAvg}%. This restraint compounds over time.
      </p>

      <InfoCallout
        header="Behavioral Edge"
        text="The average bettor plays 78% of opportunities. You play fewer. Fewer decisions reduce error exposure."
      />
    </div>
  );
}

function TrackBetModal({ initialPick, onClose, onSubmit }) {
  const [step, setStep] = useState(initialPick ? 'wager' : 'picks');
  const [picks, setPicks] = useState([]);
  const [loadingPicks, setLoadingPicks] = useState(!initialPick);
  const [selected, setSelected] = useState(initialPick || null);
  const [amount, setAmount] = useState('100');
  const [odds, setOdds] = useState(initialPick?.market_odds != null ? String(initialPick.market_odds) : '-110');
  const [followType, setFollowType] = useState('exact');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!initialPick) {
      const load = async () => {
        try {
          const data = await apiGet('/bets/trackable');
          setPicks(data.picks || []);
        } catch (e) { console.error(e); }
        finally { setLoadingPicks(false); }
      };
      load();
    }
  }, []);

  const handleSelectPick = (pick) => {
    if (pick.already_tracked) return;
    setSelected(pick);
    setOdds(pick.market_odds != null ? String(pick.market_odds) : '-110');
    setStep('wager');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    await onSubmit({
      pick_id: selected.id,
      bet_amount: parseInt(amount) || 100,
      odds: parseInt(odds) || -110,
      follow_type: followType,
      line_at_bet: selected.line,
    });
    setSubmitting(false);
  };

  const toWin = (() => {
    const amt = parseInt(amount) || 100;
    const o = parseInt(odds) || -110;
    if (o < 0) return (amt * (100 / Math.abs(o))).toFixed(2);
    return (amt * (o / 100)).toFixed(2);
  })();

  const followTypes = [
    { id: 'exact', label: 'Exact' },
    { id: 'partial', label: 'Partial' },
    { id: 'late_line', label: 'Late Line' },
    { id: 'parlayed', label: 'Parlayed' },
  ];

  return (
    <div style={{
      position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
      zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        backgroundColor: 'var(--surface-0, var(--bg-primary))', borderRadius: '20px 20px 0 0',
        padding: '24px 20px 32px', width: '100%', maxWidth: '480px',
        maxHeight: '80vh', overflowY: 'auto',
      }} onClick={e => e.stopPropagation()}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {step === 'wager' && !initialPick && (
              <button onClick={() => { setStep('picks'); setSelected(null); }} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-tertiary)', padding: '4px',
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6"/>
                </svg>
              </button>
            )}
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: '20px',
              fontWeight: 600, color: 'var(--text-primary)', margin: 0,
            }}>{step === 'picks' ? 'Select a Pick' : 'Enter Your Wager'}</h2>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {step === 'picks' ? (
          <div>
            {loadingPicks ? (
              <div style={{ padding: '40px 0', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading picks...</p>
              </div>
            ) : picks.length === 0 ? (
              <div style={{ padding: '40px 0', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6' }}>
                  No picks available to track yet. Picks appear here when the model publishes them.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {picks.map(p => (
                  <button
                    key={p.id}
                    onClick={() => handleSelectPick(p)}
                    disabled={p.already_tracked}
                    style={{
                      width: '100%', textAlign: 'left',
                      padding: '14px 16px',
                      backgroundColor: p.already_tracked ? 'var(--surface-2)' : 'var(--surface-1)',
                      border: '1px solid var(--stroke-subtle)',
                      borderRadius: '12px', cursor: p.already_tracked ? 'default' : 'pointer',
                      opacity: p.already_tracked ? 0.5 : 1,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                          letterSpacing: '1.2px', textTransform: 'uppercase',
                          color: 'var(--text-tertiary)', marginBottom: '4px',
                        }}>{p.game_date}</div>
                        <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                          {p.away_team} @ {p.home_team}
                        </div>
                        <div style={{
                          fontSize: '13px', color: 'var(--blue-primary)', fontWeight: 600, marginTop: '4px',
                        }}>
                          {p.side}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        {p.already_tracked ? (
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                            color: 'var(--text-tertiary)', textTransform: 'uppercase',
                          }}>Tracked</span>
                        ) : (
                          <>
                            {p.result === 'W' || p.result === 'L' ? (
                              <span style={{
                                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                                color: p.result === 'W' ? 'var(--green-primary, #22c55e)' : 'var(--red-primary, #ef4444)',
                                textTransform: 'uppercase',
                                padding: '2px 6px', borderRadius: '4px',
                                backgroundColor: p.result === 'W' ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                              }}>{p.result === 'W' ? 'Won' : 'Lost'}</span>
                            ) : null}
                            <span style={{
                              fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500,
                              color: 'var(--text-tertiary)',
                            }}>
                              {p.edge_pct?.toFixed(1)}% edge
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div>
            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '12px',
              padding: '14px 16px', marginBottom: '16px',
              border: '1px solid var(--stroke-subtle)',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                letterSpacing: '1.2px', textTransform: 'uppercase',
                color: 'var(--text-tertiary)', marginBottom: '4px',
              }}>{selected?.game_date}</div>
              <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                {selected?.away_team} @ {selected?.home_team}
              </div>
              <div style={{
                fontSize: '15px', color: 'var(--blue-primary)', fontWeight: 700, marginTop: '6px',
              }}>
                {selected?.side}
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                    letterSpacing: '1.2px', textTransform: 'uppercase',
                    color: 'var(--text-tertiary)', display: 'block', marginBottom: '6px',
                  }}>Wager ($)</label>
                  <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
                    placeholder="100" style={{
                      width: '100%', padding: '12px 14px',
                      backgroundColor: 'var(--surface-1)',
                      border: '1px solid var(--stroke-subtle)',
                      borderRadius: '10px', color: 'var(--text-primary)',
                      fontSize: '15px', fontFamily: 'var(--font-mono)',
                      outline: 'none', boxSizing: 'border-box',
                    }} />
                </div>
                <div>
                  <label style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                    letterSpacing: '1.2px', textTransform: 'uppercase',
                    color: 'var(--text-tertiary)', display: 'block', marginBottom: '6px',
                  }}>Odds</label>
                  <input type="number" value={odds} onChange={e => setOdds(e.target.value)}
                    placeholder="-110" style={{
                      width: '100%', padding: '12px 14px',
                      backgroundColor: 'var(--surface-1)',
                      border: '1px solid var(--stroke-subtle)',
                      borderRadius: '10px', color: 'var(--text-primary)',
                      fontSize: '15px', fontFamily: 'var(--font-mono)',
                      outline: 'none', boxSizing: 'border-box',
                    }} />
                </div>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                  letterSpacing: '1.2px', textTransform: 'uppercase',
                  color: 'var(--text-tertiary)', display: 'block', marginBottom: '6px',
                }}>Follow Type</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {followTypes.map(ft => (
                    <button key={ft.id} type="button" onClick={() => setFollowType(ft.id)} style={{
                      flex: 1, padding: '8px 4px',
                      backgroundColor: followType === ft.id ? 'rgba(79, 134, 247, 0.15)' : 'var(--surface-1)',
                      border: `1px solid ${followType === ft.id ? 'var(--blue-primary)' : 'var(--stroke-subtle)'}`,
                      borderRadius: '8px', cursor: 'pointer',
                      color: followType === ft.id ? 'var(--blue-primary)' : 'var(--text-secondary)',
                      fontSize: '11px', fontWeight: 600,
                      fontFamily: 'var(--font-mono)',
                    }}>
                      {ft.label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{
                backgroundColor: 'var(--surface-1)', borderRadius: '10px',
                padding: '12px 14px', marginBottom: '16px',
                border: '1px solid var(--stroke-subtle)',
                display: 'flex', justifyContent: 'space-between',
              }}>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>To win</span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '14px',
                  fontWeight: 600, color: 'var(--green-profit)',
                }}>${toWin}</span>
              </div>

              <button type="submit" disabled={submitting} style={{
                width: '100%', padding: '14px',
                backgroundColor: 'var(--blue-primary)', color: '#fff',
                border: 'none', borderRadius: '12px',
                fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                opacity: submitting ? 0.6 : 1,
              }}>
                {submitting ? 'Tracking...' : 'Track This Bet'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
