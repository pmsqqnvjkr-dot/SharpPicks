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

export default function InsightsTab({ onNavigate }) {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedInsight, setSelectedInsight] = useState(null);
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    loadInsights();
  }, [activeCategory]);

  useEffect(() => {
    setAnimateIn(false);
    const t = setTimeout(() => setAnimateIn(true), 50);
    return () => clearTimeout(t);
  }, [loading]);

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
    return (
      <InsightDetail
        insight={selectedInsight}
        allInsights={insights}
        onBack={() => setSelectedInsight(null)}
        onSelectInsight={setSelectedInsight}
        onNavigate={onNavigate}
      />
    );
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
        }}>Sharp Journal</div>

        <div style={{
          display: 'flex', gap: '8px', overflowX: 'auto',
          paddingBottom: '16px',
          scrollbarWidth: 'none',
        }}>
          {CATEGORIES.map(cat => {
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '20px',
                  border: isActive ? '1px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
                  backgroundColor: isActive ? 'rgba(79, 134, 247, 0.12)' : 'transparent',
                  color: isActive ? 'var(--blue-primary)' : 'var(--text-secondary)',
                  fontSize: '12px', fontWeight: 500,
                  fontFamily: 'var(--font-sans)',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  transition: 'all 0.25s ease',
                  boxShadow: isActive ? '0 0 12px rgba(79, 134, 247, 0.15)' : 'none',
                }}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{
        padding: '0 20px 100px',
        opacity: animateIn ? 1 : 0,
        transform: animateIn ? 'translateY(0)' : 'translateY(8px)',
        transition: 'opacity 0.35s ease, transform 0.35s ease',
      }}>
        {loading ? (
          <InsightsSkeleton />
        ) : insights.length === 0 ? (
          <EmptyInsights />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {activeCategory === 'all' && <StartHereCard onTap={() => {
              const philosophy = insights.find(i => i.slug === 'not-every-edge-is-worth-taking') || insights[0];
              if (philosophy) setSelectedInsight(philosophy);
            }} />}
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

function StartHereCard({ onTap }) {
  return (
    <button
      onClick={onTap}
      style={{
        width: '100%',
        textAlign: 'left',
        background: 'linear-gradient(135deg, rgba(79, 134, 247, 0.08) 0%, rgba(52, 211, 153, 0.06) 100%)',
        border: '1px solid rgba(79, 134, 247, 0.2)',
        borderRadius: '14px',
        padding: '20px 18px',
        cursor: 'pointer',
        display: 'block',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 6px 20px rgba(79, 134, 247, 0.1)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '10px',
          backgroundColor: 'rgba(79, 134, 247, 0.12)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="1.5">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px', fontWeight: 700,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--blue-primary)',
            marginBottom: '4px',
          }}>Start Here</div>
          <div style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '16px', fontWeight: 600,
            color: 'var(--text-primary)',
            lineHeight: '1.3',
          }}>The Sharp Picks Philosophy</div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </button>
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
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-1px)';
        e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.15)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px', flexWrap: 'wrap' }}>
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
        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>·</span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.03em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>Founder Journal</span>
        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>·</span>
        <span style={{
          fontSize: '10px', color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)',
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

function InsightDetail({ insight, allInsights, onBack, onSelectInsight, onNavigate }) {
  const contentRef = useRef(null);
  const [fadeIn, setFadeIn] = useState(false);

  useEffect(() => {
    setFadeIn(false);
    const t = setTimeout(() => setFadeIn(true), 50);
    if (contentRef.current) contentRef.current.scrollTop = 0;
    return () => clearTimeout(t);
  }, [insight.id]);

  const paragraphs = (insight.content || '').split('\n\n').filter(p => p.trim());

  const currentIndex = allInsights.findIndex(i => i.id === insight.id);
  const nextInsight = currentIndex >= 0 && currentIndex < allInsights.length - 1
    ? allInsights[currentIndex + 1]
    : null;

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
        }}>Sharp Journal</span>
      </div>

      <div ref={contentRef} style={{
        padding: '24px 20px 100px',
        maxWidth: '600px', margin: '0 auto',
        opacity: fadeIn ? 1 : 0,
        transform: fadeIn ? 'translateY(0)' : 'translateY(12px)',
        transition: 'opacity 0.4s ease, transform 0.4s ease',
      }}>
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
          <span style={{
            fontSize: '10px', color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)', letterSpacing: '0.05em',
          }}>·</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.05em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>Founder Journal</span>
          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
            {insight.reading_time_minutes} min read
          </span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '27px', fontWeight: 700,
          color: 'var(--text-primary)',
          lineHeight: '1.3',
          marginBottom: '12px',
          letterSpacing: '-0.01em',
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
          lineHeight: '2.0',
        }}>
          {paragraphs.map((p, i) => {
            if (p.trim() === '---') {
              return <div key={i} style={{ margin: '24px 0', borderTop: '1px solid var(--stroke-subtle)' }} />;
            }
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
              return <SharpPrincipleBlock key={i} text={p.replace('> ', '')} />;
            }
            if (p.startsWith('– ') || p.startsWith('— ')) {
              return (
                <div key={i}>
                  <div style={{
                    margin: '28px 0 16px',
                    borderTop: '1px solid var(--stroke-subtle)',
                  }} />
                  <p style={{
                    margin: '0',
                    fontSize: '14px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-serif)',
                    fontStyle: 'italic',
                  }}>
                    {p}
                  </p>
                </div>
              );
            }
            const extraBreath = (i > 0 && i % 3 === 0);
            const isClosingPunch = p === 'Discipline compounds. Impulse erodes.' ||
              p === 'Fewer bets. Higher quality.\nThat is how ROI survives.' ||
              p === 'Short term streaks are noise.\nLong term expectancy is signal.' ||
              p === 'Survival is step one.\nCompounding is step two.';
            if (isClosingPunch) {
              return <p key={i} style={{
                margin: '4px 0 20px',
                fontSize: '16px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: '1.7',
              }}>{p}</p>;
            }
            const isShort = p.length < 60;
            return <p key={i} style={{ margin: isShort ? '0 0 22px' : (extraBreath ? '0 0 28px' : '0 0 18px') }}>{p}</p>;
          })}
        </div>

        <WhyThisMatters insight={insight} />

        <FounderSignature />

        <div style={{
          margin: '32px 0',
          padding: '16px 18px',
          background: 'var(--surface-1)',
          border: '1px solid var(--stroke-subtle)',
          borderRadius: '12px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'border-color 0.2s ease',
        }}
          onClick={() => onNavigate && onNavigate('performance', 'model')}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(79, 134, 247, 0.3)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--stroke-subtle)'}
        >
          <p style={{
            fontSize: '13px',
            color: 'var(--text-secondary)',
            margin: 0,
            lineHeight: '1.5',
          }}>
            See how this discipline performs in real picks{' '}
            <span style={{ color: 'var(--blue-primary)', fontWeight: 500 }}>&rarr;</span>
          </p>
        </div>

        {nextInsight && (
          <button
            onClick={() => onSelectInsight(nextInsight)}
            style={{
              width: '100%',
              textAlign: 'left',
              background: 'var(--surface-1)',
              border: '1px solid var(--stroke-subtle)',
              borderRadius: '12px',
              padding: '16px 18px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              transition: 'transform 0.2s ease, border-color 0.2s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.borderColor = 'rgba(79, 134, 247, 0.3)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'var(--stroke-subtle)';
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '9px', fontWeight: 700,
                letterSpacing: '2px', textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
                marginBottom: '6px',
              }}>Next Read</div>
              <div style={{
                fontSize: '14px', fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: '1.4',
              }}>
                {nextInsight.title}
              </div>
            </div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

function SharpPrincipleBlock({ text }) {
  return (
    <div style={{
      margin: '36px 0',
      padding: '28px 24px',
      background: 'rgba(52, 211, 153, 0.05)',
      borderLeft: '3px solid var(--green-profit)',
      borderRadius: '0 12px 12px 0',
      textAlign: 'center',
      boxShadow: '-3px 0 12px rgba(52, 211, 153, 0.08)',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '9px', fontWeight: 700,
        letterSpacing: '2.5px', textTransform: 'uppercase',
        color: 'var(--green-profit)',
        marginBottom: '14px',
      }}>Sharp Principle</div>
      <div style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '19px',
        fontWeight: 500,
        color: 'var(--text-primary)',
        lineHeight: '1.55',
        fontStyle: 'italic',
      }}>
        {text}
      </div>
    </div>
  );
}

function WhyThisMatters({ insight }) {
  const mattersMap = {
    'discipline': 'This is why Sharp Picks passes most games. The goal is not activity. The goal is capital preservation. Discipline compounds. Impulse erodes.',
    'philosophy': 'This principle shapes every decision the model makes. It is not strategy — it is structure.',
    'how_it_works': 'Understanding how the system works builds the trust needed to follow it through variance.',
    'market_notes': 'The market is your competition. Understanding it is the first step toward finding real edge.',
    'founder_note': 'These are the convictions behind the code. The model is a reflection of these beliefs.',
  };

  const text = mattersMap[insight.category] || mattersMap['philosophy'];

  return (
    <div style={{
      margin: '32px 0 0',
      padding: '20px',
      borderTop: '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '9px', fontWeight: 700,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        marginBottom: '10px',
      }}>Why This Matters</div>
      <p style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
        lineHeight: '1.65',
        margin: 0,
        fontFamily: 'var(--font-sans)',
      }}>
        {text}
      </p>
    </div>
  );
}

function FounderSignature() {
  return (
    <div style={{
      margin: '28px 0 0',
      padding: '24px 0 0',
      borderTop: '1px solid var(--stroke-subtle)',
    }}>
      <img
        src="/evan-signature.png"
        alt="Evan"
        style={{
          height: '140px',
          width: 'auto',
          display: 'block',
          marginBottom: '4px',
          filter: 'brightness(1.1)',
        }}
      />
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        marginBottom: '14px',
      }}>
        <div style={{
          width: '44px', height: '44px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(79, 134, 247, 0.15) 0%, rgba(52, 211, 153, 0.1) 100%)',
          border: '1px solid rgba(79, 134, 247, 0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-serif)',
          fontSize: '16px', fontWeight: 600,
          color: 'var(--blue-primary)',
          flexShrink: 0,
        }}>EC</div>
        <div>
          <div style={{
            fontSize: '17px', fontWeight: 600,
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-sans)',
            marginBottom: '2px',
          }}>Evan Cole</div>
          <div style={{
            fontSize: '13px',
            color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.03em',
          }}>Founder, Sharp Picks</div>
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
