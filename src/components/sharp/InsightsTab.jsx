import { useState, useEffect, useRef } from 'react';
import { apiGet } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import { trackEvent } from '../../utils/eventTracker';

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'philosophy', label: 'Philosophy' },
  { id: 'discipline', label: 'Discipline' },
  { id: 'market_notes', label: 'Market Notes' },
  { id: 'how_it_works', label: 'How It Works' },
  { id: 'founder_note', label: 'Signal Notes' },
];

const CATEGORY_LABELS = {
  philosophy: 'Philosophy',
  discipline: 'Discipline',
  market_notes: 'Market Notes',
  how_it_works: 'How It Works',
  founder_note: 'Signal Notes',
};

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function InsightsTab({ onNavigate, initialInsight, onInitialInsightConsumed }) {
  const { sport } = useSport();
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedInsight, setSelectedInsight] = useState(null);
  const [animateIn, setAnimateIn] = useState(false);

  const selectAndTrack = (insight) => {
    setSelectedInsight(insight);
    if (insight) trackEvent('view_article', { article_slug: insight.slug, category: insight.category });
  };

  useEffect(() => {
    if (initialInsight) {
      selectAndTrack(initialInsight);
      if (onInitialInsightConsumed) onInitialInsightConsumed();
    }
  }, [initialInsight]);

  useEffect(() => {
    loadInsights();
  }, [activeCategory, sport]);

  useEffect(() => {
    setAnimateIn(false);
    const t = setTimeout(() => setAnimateIn(true), 50);
    return () => clearTimeout(t);
  }, [loading]);

  const loadInsights = async () => {
    setLoading(true);
    try {
      const base = activeCategory !== 'all' ? `/insights?category=${activeCategory}` : '/insights';
      const data = await apiGet(sportQuery(base, sport));
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
        onSelectInsight={(insight) => { selectAndTrack(insight); }}
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
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
          marginBottom: '16px',
        }}>Sharp Journal</div>

        <div style={{
          position: 'relative',
          marginBottom: '0',
        }}>
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
          <div style={{
            position: 'absolute',
            top: 0, right: 0, bottom: '16px', width: '32px',
            background: 'linear-gradient(to left, var(--bg-primary) 60%, transparent)',
            pointerEvents: 'none',
          }} />
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
            {(activeCategory === 'all' || activeCategory === 'how_it_works') && <StartHereCard onTap={() => {
              const guide = insights.find(i => i.slug === 'beginners-guide');
              if (guide) selectAndTrack(guide);
            }} />}
            {insights.map(insight => (
              <InsightCard
                key={insight.id}
                insight={insight}
                onTap={() => selectAndTrack(insight)}
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
            fontSize: '10px', fontWeight: 700,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'var(--blue-primary)',
            marginBottom: '4px',
          }}>Start Here</div>
          <div style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '16px', fontWeight: 600,
            color: 'var(--text-primary)',
            lineHeight: '1.3',
          }}>A Beginner's Guide to SharpPicks</div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            marginTop: '3px',
          }}>5 min read &middot; Evan Cole</div>
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
        {insight.slug === 'beginners-guide' && (
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px', fontWeight: 700,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            color: '#5A9E72',
            backgroundColor: 'rgba(90,158,114,0.12)',
            border: '1px solid rgba(90,158,114,0.2)',
            padding: '3px 8px', borderRadius: '4px',
          }}>Start Here</span>
        )}
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
        }}>Sharp Journal</span>
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
        {(insight.title || '').replace(/—/g, '-')}
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

function parseMarketNote(content) {
  const sections = {};
  let currentSection = '';
  for (const line of (content || '').split('\n')) {
    if (line.startsWith('## ')) {
      currentSection = line.replace('## ', '').trim().toLowerCase();
      sections[currentSection] = '';
    } else if (currentSection) {
      sections[currentSection] += (sections[currentSection] ? '\n' : '') + line;
    }
  }

  const obs = (sections['observation'] || '').trim().replace(/—/g, '-');
  const rawImpl = (sections['implication'] || '').trim();
  const impl = rawImpl.replace(/\*?[-–—]\s*Evan\s*Cole\*?/gi, '').replace(/—/g, '-').trim();

  let edges = 0, signals = 0, density = 0;
  const struct = sections['market structure'] || '';
  const edgesM = struct.match(/Edges detected:\s*(\d+)/);
  const signalsM = struct.match(/Signals generated:\s*(\d+)/);
  const densityM = struct.match(/Signal density:\s*([\d.]+)/);
  if (edgesM) edges = parseInt(edgesM[1]);
  if (signalsM) signals = parseInt(signalsM[1]);
  if (densityM) density = parseFloat(densityM[1]);

  let favEdges = 0, dogEdges = 0;
  const bias = sections['bias'] || '';
  const favM = bias.match(/(\d+)\s*favorite/);
  const dogM = bias.match(/(\d+)\s*underdog/);
  if (favM) favEdges = parseInt(favM[1]);
  if (dogM) dogEdges = parseInt(dogM[1]);

  const whyText = (sections['why this matters'] || '').trim().replace(/—/g, '-');

  return { obs, impl, edges, signals, density, favEdges, dogEdges, whyText };
}

function MarketNoteContent({ insight }) {
  const data = parseMarketNote(insight.content);
  const total = data.favEdges + data.dogEdges;
  const favPct = total > 0 ? Math.round(data.favEdges / total * 100) : 50;
  const dogPct = total > 0 ? 100 - favPct : 50;
  const densityStr = data.density % 1 === 0 ? `${Math.round(data.density)}%` : `${data.density}%`;

  const brandGreen = '#5A9E72';
  const brandRed = '#C4686B';
  const textMuted = '#7A8494';
  const textSecondary = '#9EAAB8';
  const textPrimary = '#E8ECF4';
  const bgCard = '#0F1424';
  const border = 'rgba(255,255,255,0.06)';
  const greenDim = 'rgba(90,158,114,0.15)';
  const accentBlue = '#4A7FBA';

  const sectionLabel = {
    fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
    fontSize: '10px', fontWeight: 500, letterSpacing: '1.5px',
    textTransform: 'uppercase', color: brandGreen, marginBottom: '8px',
  };

  const mono = "'IBM Plex Mono', var(--font-mono), monospace";
  const serifFont = "'IBM Plex Serif', var(--font-serif), serif";
  const sans = "'Inter', var(--font-sans), sans-serif";

  return (
    <>
      {/* Meta row */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        marginBottom: '16px', flexWrap: 'wrap',
      }}>
        <span style={{
          fontFamily: mono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: accentBlue, background: 'rgba(74,127,186,0.1)',
          border: '1px solid rgba(74,127,186,0.2)',
          padding: '4px 10px', borderRadius: '3px',
        }}>Market Notes</span>
        <span style={{ fontSize: '10px', color: textMuted }}>·</span>
        <span style={{
          fontFamily: mono, fontSize: '10px', letterSpacing: '1px',
          textTransform: 'uppercase', color: textMuted,
        }}>Sharp Journal</span>
        <span style={{ fontSize: '10px', color: textMuted }}>·</span>
        <span style={{
          fontFamily: mono, fontSize: '10px', letterSpacing: '1px',
          textTransform: 'uppercase', color: textMuted,
        }}>{insight.reading_time_minutes || 2} min read</span>
      </div>

      {/* Title */}
      <h1 style={{
        fontFamily: serifFont, fontSize: '26px', fontWeight: 600,
        lineHeight: 1.25, color: textPrimary, marginBottom: '6px',
      }}>{(insight.title || '').replace(/—/g, '-')}</h1>

      {/* Date */}
      <div style={{
        fontFamily: mono, fontSize: '11px', color: textMuted,
        letterSpacing: '0.5px', marginBottom: '6px',
      }}>{formatDate(insight.publish_date)}</div>

      {/* Byline */}
      <div style={{
        fontFamily: sans, fontSize: '13px', fontWeight: 500,
        color: textSecondary, marginBottom: '28px',
      }}>
        Evan Cole <span style={{ fontWeight: 400, color: textMuted }}>· Head of Signal Intelligence</span>
      </div>

      {/* Divider */}
      <div style={{ height: '1px', background: border, marginBottom: '28px' }} />

      {/* Observation */}
      {data.obs && (
        <div style={{ marginBottom: '28px' }}>
          <div style={sectionLabel}>Observation</div>
          <p style={{
            fontFamily: serifFont, fontSize: '17px', lineHeight: 1.55,
            color: textPrimary, margin: 0,
          }}>{data.obs}</p>
        </div>
      )}

      {/* Market Structure — Stat Grid */}
      <div style={{
        background: bgCard, border: `1px solid ${border}`,
        borderRadius: '8px', padding: '20px', marginBottom: '24px',
      }}>
        <div style={{ ...sectionLabel, marginBottom: '16px' }}>Market Structure</div>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0,
        }}>
          <StatItem value={data.edges} label="Edges" isLast={false} />
          <StatItem value={data.signals} label="Signals" isLast={false} />
          <StatItem value={densityStr} label="Density" isLast={true} />
        </div>
      </div>

      {/* Bias — Visual Bar */}
      {total > 0 && (
        <div style={{
          background: bgCard, border: `1px solid ${border}`,
          borderRadius: '8px', padding: '20px', marginBottom: '24px',
        }}>
          <div style={sectionLabel}>Bias</div>
          <div style={{ marginTop: '14px' }}>
            {/* Labels row */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: brandRed }} />
                <span style={{ fontFamily: mono, fontSize: '10px', letterSpacing: '0.5px', color: textSecondary }}>Favorites</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontFamily: mono, fontSize: '10px', letterSpacing: '0.5px', color: textSecondary }}>Underdogs</span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: brandGreen }} />
              </div>
            </div>
            {/* Bar */}
            <div style={{
              height: '4px', background: '#141A2E', borderRadius: '2px',
              overflow: 'hidden', display: 'flex',
            }}>
              <div style={{ height: '100%', width: `${favPct}%`, background: brandRed, borderRadius: '2px 0 0 2px' }} />
              <div style={{ height: '100%', width: `${dogPct}%`, background: brandGreen, borderRadius: '0 2px 2px 0' }} />
            </div>
            {/* Counts */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
              <span style={{ fontFamily: mono, fontSize: '11px', color: textSecondary }}>
                {data.favEdges} edge{data.favEdges !== 1 ? 's' : ''}
              </span>
              <span style={{ fontFamily: mono, fontSize: '11px', color: textSecondary }}>
                {data.dogEdges} edge{data.dogEdges !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Implication — Callout */}
      {data.impl && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: '12px',
          marginBottom: '28px', padding: '16px',
          background: greenDim, borderLeft: `3px solid ${brandGreen}`,
          borderRadius: '0 6px 6px 0',
        }}>
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: brandGreen, marginTop: '5px', flexShrink: 0,
            boxShadow: '0 0 8px rgba(90,158,114,0.4)',
          }} />
          <div>
            <div style={{
              fontFamily: mono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '1.5px', textTransform: 'uppercase',
              color: brandGreen, marginBottom: '4px',
            }}>Implication</div>
            <div style={{
              fontFamily: sans, fontSize: '14px', fontWeight: 500,
              color: textPrimary,
            }}>{data.impl}</div>
          </div>
        </div>
      )}

      {/* Why This Matters */}
      <div style={{
        borderTop: `1px solid ${border}`,
        borderBottom: `1px solid ${border}`,
        padding: '20px 0', marginBottom: '40px',
      }}>
        <div style={{
          fontFamily: mono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: textMuted, marginBottom: '10px',
        }}>Why This Matters</div>
        <p style={{
          fontFamily: serifFont, fontSize: '14px', lineHeight: 1.6,
          color: textSecondary, margin: 0,
        }}>
          {data.whyText || 'The market is your competition. Understanding it is the first step toward finding real edge.'}
        </p>
      </div>
    </>
  );
}

function StatItem({ value, label, isLast }) {
  return (
    <div style={{
      textAlign: 'center', position: 'relative',
      borderRight: isLast ? 'none' : '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{
        fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
        fontSize: '28px', fontWeight: 500, color: '#E8ECF4',
        lineHeight: 1, marginBottom: '6px',
      }}>{value}</div>
      <div style={{
        fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
        fontSize: '10px', letterSpacing: '1.2px', textTransform: 'uppercase',
        color: '#7A8494',
      }}>{label}</div>
    </div>
  );
}

function JournalTermCard({ name, definition }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      onClick={() => setOpen(!open)}
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10, padding: '14px 18px', margin: '8px 0',
        cursor: 'pointer', transition: 'border-color 0.2s ease',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace", fontSize: 14,
          fontWeight: 600, color: '#5A9E72',
        }}>{name}</span>
        <span style={{
          fontSize: 10, color: 'rgba(232,234,237,0.3)',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s ease',
        }}>▼</span>
      </div>
      <div style={{
        fontSize: 14, color: 'rgba(232,234,237,0.5)', lineHeight: 1.6,
        marginTop: open ? 8 : 0,
        maxHeight: open ? 200 : 0, overflow: 'hidden',
        transition: 'max-height 0.3s ease, margin-top 0.2s ease',
      }}>
        {parseInlineMarkdown(definition)}
      </div>
    </div>
  );
}

function JournalScreenshot({ tabName, description, src }) {
  return (
    <div style={{ margin: '24px 0', textAlign: 'center' }}>
      <img
        src={src}
        alt={`${tabName} screenshot`}
        loading="lazy"
        style={{
          width: '100%', maxWidth: 320,
          borderRadius: 12,
          border: '1px solid rgba(90,158,114,0.15)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
        }}
      />
      <div style={{
        marginTop: 10,
        fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
        fontWeight: 500, color: '#5A9E72', letterSpacing: '0.5px',
      }}>{tabName}</div>
      <div style={{ fontSize: 12, color: 'rgba(232,234,237,0.35)', marginTop: 2 }}>{description}</div>
    </div>
  );
}

const SCREENSHOT_META = {
  signals: { name: 'Signals Tab', desc: 'Your daily dashboard with live signal, edge %, and tier badge', src: '/journal/signals.png' },
  market: { name: 'Market Tab', desc: 'Full slate overview with MEI score, edges, and model vs. market deltas', src: '/journal/market.png' },
  results: { name: 'Results Tab', desc: 'Personal scoreboard with equity curve and discipline score', src: '/journal/results.png' },
  insights: { name: 'Insights Tab', desc: 'Sharp Journal articles organized by category', src: '/journal/insights.png' },
};

function InsightDetail({ insight, allInsights, onBack, onSelectInsight, onNavigate }) {
  const scrollRef = useRef(null);
  const contentRef = useRef(null);
  const [fadeIn, setFadeIn] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const isMarketNote = insight.category === 'market_notes' && /^market-note-\d{4}/.test(insight.slug);

  useEffect(() => {
    setFadeIn(false);
    setScrollProgress(0);
    const t = setTimeout(() => setFadeIn(true), 50);
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
    return () => clearTimeout(t);
  }, [insight.id]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const scrollable = el.scrollHeight - el.clientHeight;
    if (scrollable <= 0) { setScrollProgress(0); return; }
    setScrollProgress(Math.min(1, el.scrollTop / scrollable));
  };

  const paragraphs = (insight.content || '').split('\n\n').filter(p => p.trim());

  const currentIndex = allInsights.findIndex(i => i.id === insight.id);
  const nextInsight = currentIndex >= 0 && currentIndex < allInsights.length - 1
    ? allInsights[currentIndex + 1]
    : null;

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'var(--bg-primary)',
        zIndex: 200,
        overflowY: 'auto', WebkitOverflowScrolling: 'touch',
      }}
    >
      {/* Scroll progress bar */}
      <div style={{
        position: 'sticky', top: 0, left: 0, right: 0, height: '2px',
        zIndex: 2, backgroundColor: 'rgba(255,255,255,0.04)',
      }}>
        <div style={{
          height: '100%',
          width: `${scrollProgress * 100}%`,
          backgroundColor: 'var(--blue-primary)',
          transition: 'width 0.05s linear',
        }} />
      </div>

      <div style={{ maxWidth: '480px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        position: 'sticky', top: '2px', zIndex: 1,
        backgroundColor: 'var(--bg-primary)',
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        <button
          onClick={onBack}
          aria-label="Go back"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#7A8494', padding: '4px',
            minWidth: '44px', minHeight: '44px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <span style={{
          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
          fontSize: '11px', fontWeight: 500,
          letterSpacing: '2.5px', textTransform: 'uppercase',
          color: '#7A8494',
        }}>Sharp Journal</span>
      </div>

      <div ref={contentRef} style={{
        padding: '24px 20px 100px',
        maxWidth: '600px', margin: '0 auto',
        opacity: fadeIn ? 1 : 0,
        transform: fadeIn ? 'translateY(0)' : 'translateY(12px)',
        transition: 'opacity 0.4s ease, transform 0.4s ease',
      }}>
        {isMarketNote ? (
          <MarketNoteContent insight={insight} />
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              {insight.slug === 'beginners-guide' && (
                <span style={{
                  display: 'inline-block',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '11px', fontWeight: 700,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  color: '#E8EAED',
                  backgroundColor: 'rgba(90,158,114,0.25)',
                  border: '1px solid rgba(90,158,114,0.35)',
                  padding: '4px 12px', borderRadius: '5px',
                }}>Start Here</span>
              )}
              <span style={{
                display: 'inline-block',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '11px', fontWeight: 600,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: '#5A9E72',
                backgroundColor: 'rgba(90,158,114,0.12)',
                border: '1px solid rgba(90,158,114,0.2)',
                padding: '4px 12px', borderRadius: '5px',
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
              }}>Sharp Journal</span>
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
              {(insight.title || '').replace(/—/g, '-')}
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
              fontSize: '15.5px',
              color: 'var(--text-secondary)',
              lineHeight: '1.85',
              letterSpacing: '0.01em',
            }}>
              {paragraphs.map((p, i) => {
                const trimmed = p.trim();
                const isHowItWorks = insight.category === 'how_it_works' || insight.story_type === 'how_it_works';
                const isGlossarySection = isHowItWorks && /^## Key Concepts/.test(trimmed);

                if (trimmed === '---') {
                  return (
                    <div key={i} style={{
                      border: 'none', height: 1, margin: '32px 0',
                      background: 'linear-gradient(to right, transparent, rgba(90,158,114,0.3), transparent)',
                    }} />
                  );
                }

                if (/^\[screenshot:\s*(.+?)\]$/.test(trimmed)) {
                  const id = trimmed.match(/^\[screenshot:\s*(.+?)\]$/)[1].toLowerCase();
                  const meta = SCREENSHOT_META[id];
                  if (meta) return <JournalScreenshot key={i} tabName={meta.name} description={meta.desc} src={meta.src} />;
                  return null;
                }

                if (/^\[term:\s*(.+?)\]\s*([\s\S]*)/.test(trimmed)) {
                  const m = trimmed.match(/^\[term:\s*(.+?)\]\s*([\s\S]*)/);
                  return <JournalTermCard key={i} name={m[1]} definition={m[2].trim()} />;
                }

                if (isHowItWorks && isGlossarySection) {
                  return (
                    <h2 key={i} style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '18px', fontWeight: 600,
                      color: 'var(--text-primary)',
                      margin: '36px 0 16px',
                      paddingTop: 24,
                      borderTop: '1px solid rgba(90,158,114,0.15)',
                    }}>
                      {parseInlineMarkdown(trimmed.replace('## ', ''))}
                    </h2>
                  );
                }

                if (isHowItWorks && /^\*\*(.+?):\*\*\s(.+)/.test(trimmed)) {
                  const inGlossary = paragraphs.slice(0, i).some(pp => /^## Key Concepts/.test(pp.trim()));
                  if (inGlossary) {
                    const m = trimmed.match(/^\*\*(.+?):\*\*\s([\s\S]+)/);
                    return <JournalTermCard key={i} name={m[1]} definition={m[2].trim()} />;
                  }
                }

                const tabMatch = trimmed.match(/^## (\d+)\.\s+(.+)/);
                if (isHowItWorks && tabMatch) {
                  return (
                    <div key={i} style={{
                      borderTop: '1px solid rgba(90,158,114,0.15)',
                      paddingTop: 24, marginTop: 32,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                        <div style={{
                          width: 28, height: 28, borderRadius: 8,
                          background: 'rgba(90,158,114,0.1)', color: '#5A9E72',
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 13, fontWeight: 600,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>{tabMatch[1]}</div>
                        <span style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 18, fontWeight: 600,
                          color: '#E8EAED',
                        }}>{tabMatch[2]}</span>
                      </div>
                    </div>
                  );
                }

                if (p.startsWith('## ')) {
                  return (
                    <h2 key={i} style={{
                      fontFamily: 'var(--font-sans)',
                      fontSize: '17px', fontWeight: 600,
                      color: 'var(--text-primary)',
                      margin: '28px 0 12px',
                    }}>
                      {parseInlineMarkdown(p.replace('## ', ''))}
                    </h2>
                  );
                }

                if (p.startsWith('> ')) {
                  const quoteText = p.split('\n').map(line => line.replace(/^>\s*/, '')).join('\n');
                  const labelMatch = quoteText.match(/^\*\*(.+?)\*\*\n?([\s\S]*)/);
                  if (labelMatch) {
                    return <SharpPrincipleBlock key={i} label={labelMatch[1]} text={labelMatch[2].trim()} />;
                  }
                  return (
                    <div key={i} style={{
                      borderLeft: '2px solid rgba(90,158,114,0.4)',
                      padding: '16px 20px', margin: '24px 0',
                      fontSize: 15, color: 'rgba(232,234,237,0.55)',
                      lineHeight: 1.6,
                      fontFamily: "'IBM Plex Serif', Georgia, serif",
                      fontStyle: 'italic',
                    }}>
                      {parseInlineMarkdown(quoteText)}
                    </div>
                  );
                }

                if (p.startsWith('– ') || p.startsWith('— ')) {
                  if (/Evan\s*Cole/i.test(p)) return null;
                  return (
                    <div key={i}>
                      <div style={{
                        margin: '28px 0 16px',
                        borderTop: '1px solid var(--stroke-subtle)',
                      }} />
                      <p style={{
                        margin: '0', fontSize: '14px', fontWeight: 600,
                        color: 'var(--text-primary)',
                        fontFamily: 'var(--font-serif)', fontStyle: 'italic',
                      }}>
                        {parseInlineMarkdown(p)}
                      </p>
                    </div>
                  );
                }

                if (/^\*[A-Z][a-z]+(\s+[A-Z][a-z]+)*\*$/.test(trimmed)) return null;
                if (/^\*?[-–—]?\s*Evan\s*Cole/i.test(trimmed) || /^Evan Cole/i.test(trimmed) || /^(Founder|Head of Signal Intelligence),?\s*Sharp\s*Picks$/i.test(trimmed)) return null;

                const isClosingPunch = p === 'Discipline compounds. Impulse erodes.' ||
                  p === 'Fewer bets. Higher quality.\nThat is how ROI survives.' ||
                  p === 'Short term streaks are noise.\nLong term expectancy is signal.' ||
                  p === 'Survival is step one.\nCompounding is step two.';
                if (isClosingPunch) {
                  return <p key={i} style={{
                    margin: '4px 0 16px', fontSize: '16px', fontWeight: 600,
                    color: 'var(--text-primary)', lineHeight: '1.7',
                  }}>{parseInlineMarkdown(p)}</p>;
                }

                return <p key={i} style={{ margin: '0 0 20px' }}>{parseInlineMarkdown(p)}</p>;
              })}
            </div>

            <WhyThisMatters insight={insight} />

            <FounderSignature />
          </>
        )}

        {!isMarketNote && (
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
        )}

        {insight.has_related_picks && (
          <RelatedPicksSection insightId={insight.id} />
        )}

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
                fontSize: '10px', fontWeight: 700,
                letterSpacing: '1.5px', textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
                marginBottom: '6px',
              }}>Next Read</div>
              <div style={{
                fontSize: '14px', fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: '1.4',
              }}>
                {(nextInsight.title || '').replace(/—/g, '-')}
              </div>
            </div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        )}
      </div>
      </div>
    </div>
  );
}

function parseInlineMarkdown(text) {
  if (!text) return text;
  const parts = [];
  let key = 0;
  const regex = /(\[stat:\s*(.+?)\s*\/\s*(.+?)\])|(\*\*(.+?)\*\*)|(\*(.+?)\*)/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[1]) {
      parts.push(
        <span key={key++} style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'rgba(255,255,255,0.04)', borderRadius: 8,
          padding: '6px 14px', fontFamily: "'JetBrains Mono', monospace",
          margin: '0 4px', verticalAlign: 'middle',
        }}>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#5A9E72' }}>{match[2]}</span>
          <span style={{ fontSize: 12, color: 'rgba(232,234,237,0.4)' }}>{match[3]}</span>
        </span>
      );
    } else if (match[4]) {
      parts.push(<strong key={key++} style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{match[5]}</strong>);
    } else if (match[6]) {
      parts.push(<em key={key++} style={{ fontStyle: 'italic' }}>{match[7]}</em>);
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length > 0 ? parts : text;
}

function SharpPrincipleBlock({ text, label }) {
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
        fontSize: '10px', fontWeight: 700,
        letterSpacing: '2.5px', textTransform: 'uppercase',
        color: 'var(--green-profit)',
        marginBottom: '14px',
      }}>{label || 'Sharp Principle'}</div>
      <div style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '19px',
        fontWeight: 500,
        color: 'var(--text-primary)',
        lineHeight: '1.55',
        fontStyle: 'italic',
      }}>
        {parseInlineMarkdown(text)}
      </div>
    </div>
  );
}

function WhyThisMatters({ insight }) {
  const mattersMap = {
    'discipline': 'This is why SharpPicks passes most games. The goal is not activity. The goal is capital preservation. Discipline compounds. Impulse erodes.',
    'philosophy': 'This principle shapes every decision the model makes. It is not strategy - it is structure.',
    'how_it_works': 'Understanding how the system works builds the trust needed to follow it through variance.',
    'market_notes': 'The market is your competition. Understanding it is the first step toward finding real edge.',
    'founder_note': 'These are the convictions behind the code. The model is a reflection of these beliefs.',
  };

  const text = mattersMap[insight.category] || mattersMap['philosophy'];

  return (
    <div style={{
      margin: '20px 0 0',
      padding: '16px',
      borderTop: '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 700,
        letterSpacing: '1.5px', textTransform: 'uppercase',
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
      margin: '12px 0 0',
      padding: '16px 0 0',
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
          marginLeft: '-20px',
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
          }}>Head of Signal Intelligence</div>
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
  const { sport } = useSport();
  const [insight, setInsight] = useState(null);

  useEffect(() => {
    apiGet(sportQuery('/insights/latest?pass_day=true', sport))
      .then(data => { if (data && !data.error) setInsight(data); })
      .catch(() => {});
  }, [sport]);

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
            {(insight.title || '').replace(/—/g, '-')}
          </div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </button>
  );
}

function RelatedPicksSection({ insightId }) {
  const { sport } = useSport();
  const [data, setData] = useState(null);
  useEffect(() => {
    apiGet(sportQuery(`/insights/${insightId}/picks`, sport)).then(setData).catch(() => {});
  }, [insightId, sport]);

  if (!data || !data.picks?.length) return null;

  return (
    <div style={{
      background: 'var(--surface-1)', borderRadius: '12px',
      border: '1px solid var(--stroke-subtle)', padding: '16px 18px',
      marginBottom: '16px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
        letterSpacing: '1.5px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '12px',
      }}>Related Picks</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {data.picks.map(p => (
          <div key={p.id} style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '8px 10px', borderRadius: '8px',
            background: 'rgba(255,255,255,0.02)',
          }}>
            <span style={{ fontSize: '14px', width: '20px', textAlign: 'center', flexShrink: 0 }}>
              {p.result === 'win' ? '✅' : p.result === 'loss' ? '❌' : p.result === 'push' ? '➖' : '⏳'}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                color: 'var(--text-primary)', overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>{p.side}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-tertiary)' }}>{p.game_date}</div>
            </div>
            {p.profit_units != null && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                color: p.profit_units > 0 ? 'var(--green-profit)' : p.profit_units < 0 ? 'var(--red-loss)' : 'var(--text-secondary)',
                flexShrink: 0,
              }}>{p.profit_units > 0 ? '+' : ''}{p.profit_units.toFixed(2)}u</span>
            )}
          </div>
        ))}
      </div>
      {data.summary && (
        <div style={{
          marginTop: '10px', paddingTop: '10px',
          borderTop: '1px solid var(--stroke-subtle)',
          display: 'flex', justifyContent: 'center', gap: '16px',
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {data.summary.total} picks
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {data.summary.wins}-{data.summary.losses}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
            color: data.summary.units >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
          }}>{data.summary.units >= 0 ? '+' : ''}{data.summary.units}u</span>
        </div>
      )}
    </div>
  );
}
