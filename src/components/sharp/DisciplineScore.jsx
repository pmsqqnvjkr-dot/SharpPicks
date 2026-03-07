import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

const label = {
  fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)',
  fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
  color: 'var(--text-tertiary)', lineHeight: 1,
};

const metricNum = {
  fontFamily: 'var(--font-mono)', fontWeight: 700,
  fontVariantNumeric: 'tabular-nums', lineHeight: 1,
};

export default function DisciplineScore() {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/public/discipline', sport));

  if (loading || !data) return null;

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-md)',
      marginBottom: 'var(--space-md)',
    }}>
      <div style={{ ...label, marginBottom: 'var(--space-md)' }}>
        Discipline Score
      </div>

      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 'var(--space-sm)',
        marginBottom: 'var(--space-md)',
      }}>
        <span style={{
          ...metricNum, fontSize: 'var(--text-hero)',
          color: 'var(--text-primary)',
        }}>{data.grade}</span>
        <GradeLabel grade={data.grade} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
            Selectivity
          </span>
          <span style={{ ...metricNum, fontSize: 'var(--text-metric)', color: 'var(--text-primary)' }}>
            {data.selectivity}%
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
            Industry Avg
          </span>
          <span style={{ ...metricNum, fontSize: 'var(--text-metric)', color: 'var(--text-tertiary)' }}>
            {data.industry_avg}%
          </span>
        </div>
      </div>

      <div style={{
        height: '1px', background: 'var(--color-border)',
        margin: 'var(--space-md) 0',
      }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
          Est. Capital Preserved
        </span>
        <span style={{
          ...metricNum, fontSize: '16px', color: 'var(--color-signal)',
        }}>
          +${data.capital_preserved}
        </span>
      </div>
    </div>
  );
}

function GradeLabel({ grade }) {
  const labels = {
    'A+': 'Elite discipline', 'A': 'Sharp bettor', 'B+': 'Strong discipline',
    'B': 'Improving', 'C': 'Casual bettor', 'D': 'Overbetting',
  };
  return (
    <span style={{
      fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)',
    }}>{labels[grade] || ''}</span>
  );
}
