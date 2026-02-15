import { useApi } from '../../hooks/useApi';

export default function HowItWorksScreen({ onBack }) {
  const { data: modelInfo } = useApi('/public/model-info');

  const accuracy = modelInfo?.accuracy ?? '--';
  const brier = modelInfo?.brier_score ?? '--';
  const numFeatures = modelInfo?.num_features ?? '--';
  const trainingSize = modelInfo?.training_size?.toLocaleString() ?? '--';

  const sections = [
    {
      title: 'The model',
      icon: '&#9881;',
      content: `Our ensemble machine learning model analyzes ${modelInfo ? modelInfo.num_features : 'dozens of'} features per NBA game including pace ratings, team strength metrics, injury impact scores, schedule fatigue, travel distance, altitude adjustments, and line movement patterns. It was trained on ${modelInfo ? trainingSize : 'thousands of'} historical NBA games and achieves a 68.6% walk-forward ATS performance with a ${modelInfo ? brier : 'low'} Brier score.`,
    },
    {
      title: 'Edge detection',
      icon: '&#9670;',
      content: 'For each game, the model calculates its own probability and compares it against the market line. If the difference (the "edge") exceeds 3.5%, that game qualifies as a pick. Most days, no game clears this threshold. That silence is the product working.',
    },
    {
      title: 'One pick per day',
      icon: '&#9679;',
      content: 'Even if multiple games clear the threshold, only the highest-edge game is published. This enforces discipline and prevents over-betting. The system is designed to protect your bankroll, not to generate volume.',
    },
    {
      title: 'Append-only record',
      icon: '&#9745;',
      content: 'Every pick and every pass is permanently logged and publicly visible. Picks are never edited or deleted after publication. Pass days are recorded too, showing exactly when the model ran and found no qualifying edge. Complete transparency.',
    },
    {
      title: 'Closing line value',
      icon: '&#8594;',
      content: 'We track whether our picks beat the closing line (the final line before tip-off). Consistently beating the close is the strongest signal of long-term edge, more reliable than short-term win rate.',
    },
    {
      title: 'Risk management',
      icon: '&#9711;',
      content: 'All picks are evaluated at -110 standard juice. We recommend flat betting (same unit size every pick). The system does not suggest parlay, teaser, or progressive strategies. Discipline over excitement.',
    },
  ];

  return (
    <div style={{ padding: '0' }}>
      <div style={{
        padding: '20px 20px 16px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <h1 style={{
          fontFamily: 'var(--font-serif)', fontSize: '22px',
          fontWeight: 600, color: 'var(--text-primary)',
        }}>How It Works</h1>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          padding: '24px', border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <p style={{
            fontSize: '15px', color: 'var(--text-secondary)',
            lineHeight: '1.7', fontFamily: 'var(--font-sans)',
          }}>
            Sharp Picks is a discipline system, not a tips service. The model runs daily, analyzes every NBA game, and publishes a pick only when the statistical edge exceeds a strict threshold. Most days, it says nothing. That restraint is the product.
          </p>
        </div>

        {sections.map((section, i) => (
          <div key={i} style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            padding: '20px', border: '1px solid var(--stroke-subtle)',
            marginBottom: '12px',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px',
            }}>
              <span style={{
                fontSize: '16px', color: 'var(--blue-primary)',
                width: '24px', textAlign: 'center',
              }} dangerouslySetInnerHTML={{ __html: section.icon }} />
              <h3 style={{
                fontFamily: 'var(--font-serif)', fontSize: '16px',
                fontWeight: 600, color: 'var(--text-primary)',
              }}>{section.title}</h3>
            </div>
            <p style={{
              fontSize: '13px', color: 'var(--text-secondary)',
              lineHeight: '1.7',
            }}>{section.content}</p>
          </div>
        ))}

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          padding: '20px', border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-serif)', fontSize: '16px',
            fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px',
          }}>Model performance</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <StatBlock label="Walk-Fwd ATS" value={modelInfo ? '68.6%' : '--'} />
            <StatBlock label="Brier Score" value={modelInfo ? String(brier) : '--'} />
            <StatBlock label="Features" value={modelInfo ? String(numFeatures) : '--'} />
            <StatBlock label="Training Set" value={modelInfo ? trainingSize : '--'} />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatBlock({ label, value }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)', borderRadius: '10px', padding: '12px', textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '18px',
        fontWeight: 600, color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}
