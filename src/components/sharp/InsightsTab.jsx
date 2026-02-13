import { useState, useEffect, useRef } from 'react';
import { apiGet } from '../../hooks/useApi';

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'philosophy', label: 'Philosophy' },
  { id: 'discipline', label: 'Discipline' },
  { id: 'market_notes', label: 'Market Notes' },
  { id: 'how_it_works', label: 'How It Works' },
  { id: 'founder_note', label: 'Founder Notes' },
];

const CATEGORY_LABELS = {
  philosophy: 'Philosophy',
  discipline: 'Discipline',
  market_notes: 'Market Notes',
  how_it_works: 'How It Works',
  founder_note: 'Founder Notes',
};

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function InsightsTab() {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedInsight, setSelectedInsight] = useState(null);

  useEffect(() => {
    loadInsights();
  }, [activeCategory]);

  const loadInsights = async () => {
    setLoading(true);
    try {
      const params = activeCategory !== 'all' ? `?category=${activeCategory}` : '';
      const data = await apiGet(`/insights${params}`);
      setInsights(data.insights || []);
    } catch (e) {
      console.error('Failed to load insights:', e);
    } finally {
      setLoading(false);
    }
  };

  if (selectedInsight) {
    return <InsightDetail insight={selectedInsight} onBack={() => setSelectedInsight(null)} />;
  }

  return (
    <div style={{ padding: '0' }}>
      <div style={{ padding: '20px 20px 0' }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 600,
          letterSpacing: '2px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
          marginBottom: '16px',
        }}>Insights</div>

        <div style={{
          display: 'flex', gap: '8px', overflowX: 'auto',
          paddingBottom: '16px',
          scrollbarWidth: 'none',
        }}>
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              style={{
                padding: '6px 14px',
                borderRadius: '20px',
                border: activeCategory === cat.id ? '1px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
                backgroundColor: activeCategory === cat.id ? 'rgba(79, 134, 247, 0.1)' : 'transparent',
                color: activeCategory === cat.id ? 'var(--blue-primary)' : 'var(--text-secondary)',
                fontSize: '12px', fontWeight: 500,
                fontFamily: 'var(--font-sans)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: '0 20px 100px' }}>
        {loading ? (
          <InsightsSkeleton />
        ) : insights.length === 0 ? (
          <EmptyInsights />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {insights.map(insight => (
              <InsightCard
                key={insight.id}
                insight={insight}
                onTap={() => setSelectedInsight(insight)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function InsightCard({ insight, onTap }) {
  return (
    <button
      onClick={onTap}
      style={{
        width: '100%',
        textAlign: 'left',
        background: 'var(--surface-1)',
        border: '1px solid var(--stroke-subtle)',
        borderRadius: '14px',
        padding: '18px 16px',
        cursor: 'pointer',
        display: 'block',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 600,
          letterSpacing: '0.05em', textTransform: 'uppercase',
          color: 'var(--blue-primary)',
          backgroundColor: 'rgba(79, 134, 247, 0.1)',
          padding: '3px 8px', borderRadius: '4px',
        }}>
          {CATEGORY_LABELS[insight.category] || insight.category}
        </span>
        <span style={{
          fontSize: '11px', color: 'var(--text-tertiary)',
        }}>
          {insight.reading_time_minutes} min
        </span>
      </div>

      <h3 style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '15px', fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '6px',
        lineHeight: '1.4',
      }}>
        {insight.title}
      </h3>

      <p style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: '1.5',
        margin: 0,
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {insight.excerpt}
      </p>

      <div style={{
        marginTop: '12px',
        fontSize: '11px', color: 'var(--text-tertiary)',
      }}>
        {formatDate(insight.publish_date)}
      </div>
    </button>
  );
}

function InsightDetail({ insight, onBack }) {
  const contentRef = useRef(null);

  const paragraphs = (insight.content || '').split('\n\n').filter(p => p.trim());

  return (
    <div style={{ padding: '0', minHeight: '100vh' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        <button
          onClick={onBack}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: '4px',
            display: 'flex', alignItems: 'center',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 600,
          letterSpacing: '2px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>Insights</span>
      </div>

      <div ref={contentRef} style={{ padding: '24px 20px 100px', maxWidth: '600px', margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 600,
            letterSpacing: '0.05em', textTransform: 'uppercase',
            color: 'var(--blue-primary)',
            backgroundColor: 'rgba(79, 134, 247, 0.1)',
            padding: '3px 8px', borderRadius: '4px',
          }}>
            {CATEGORY_LABELS[insight.category] || insight.category}
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
            {insight.reading_time_minutes} min read
          </span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '24px', fontWeight: 600,
          color: 'var(--text-primary)',
          lineHeight: '1.35',
          marginBottom: '12px',
        }}>
          {insight.title}
        </h1>

        <div style={{
          fontSize: '12px', color: 'var(--text-tertiary)',
          marginBottom: '28px',
          paddingBottom: '20px',
          borderBottom: '1px solid var(--stroke-subtle)',
        }}>
          {formatDate(insight.publish_date)}
        </div>

        <div style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '15px',
          color: 'var(--text-secondary)',
          lineHeight: '1.75',
        }}>
          {paragraphs.map((p, i) => {
            if (p.startsWith('## ')) {
              return (
                <h2 key={i} style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: '17px', fontWeight: 600,
                  color: 'var(--text-primary)',
                  margin: '28px 0 12px',
                }}>
                  {p.replace('## ', '')}
                </h2>
              );
            }
            if (p.startsWith('> ')) {
              return (
                <blockquote key={i} style={{
                  borderLeft: '2px solid var(--blue-primary)',
                  paddingLeft: '16px',
                  margin: '20px 0',
                  fontStyle: 'italic',
                  color: 'var(--text-primary)',
                }}>
                  {p.replace('> ', '')}
                </blockquote>
              );
            }
            return <p key={i} style={{ margin: '0 0 16px' }}>{p}</p>;
          })}
        </div>
      </div>
    </div>
  );
}

function InsightsSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {[1, 2, 3].map(i => (
        <div key={i} style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '14px',
          padding: '18px 16px',
          border: '1px solid var(--stroke-subtle)',
        }}>
          <div style={{
            width: '80px', height: '18px', borderRadius: '4px',
            backgroundColor: 'var(--surface-2)', marginBottom: '12px',
          }} />
          <div style={{
            width: '85%', height: '16px', borderRadius: '4px',
            backgroundColor: 'var(--surface-2)', marginBottom: '8px',
          }} />
          <div style={{
            width: '60%', height: '14px', borderRadius: '4px',
            backgroundColor: 'var(--surface-2)',
          }} />
        </div>
      ))}
    </div>
  );
}

function EmptyInsights() {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '40px 24px',
      textAlign: 'center',
    }}>
      <div style={{
        width: '48px', height: '48px', borderRadius: '12px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 16px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
        </svg>
      </div>
      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '16px', fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '8px',
      }}>
        Insights coming soon
      </p>
      <p style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: '1.6',
      }}>
        Educational content on betting discipline, market dynamics, and model methodology.
      </p>
    </div>
  );
}

export function InsightPassDayCTA({ onTap }) {
  const [insight, setInsight] = useState(null);

  useEffect(() => {
    apiGet('/insights/latest?pass_day=true')
      .then(data => { if (data && !data.error) setInsight(data); })
      .catch(() => {});
  }, []);

  if (!insight) return null;

  return (
    <button
      onClick={() => onTap(insight)}
      style={{
        width: '100%',
        textAlign: 'left',
        background: 'var(--surface-1)',
        border: '1px solid var(--stroke-subtle)',
        borderRadius: '14px',
        padding: '16px',
        cursor: 'pointer',
        marginTop: '12px',
        display: 'block',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '36px', height: '36px', borderRadius: '10px',
          backgroundColor: 'rgba(79, 134, 247, 0.08)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="1.5">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: '11px', color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.05em', textTransform: 'uppercase',
            fontWeight: 600, marginBottom: '3px',
          }}>
            Today's Insight
          </div>
          <div style={{
            fontSize: '14px', fontWeight: 500,
            color: 'var(--text-primary)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {insight.title}
          </div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </button>
  );
}
