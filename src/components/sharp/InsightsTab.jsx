import { useState, useEffect, useRef } from 'react';
import { apiGet } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import { trackEvent } from '../../utils/eventTracker';
import OnboardingCard from './OnboardingCard';

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

const CATEGORY_ABBR = {
  market_notes: 'MN',
  philosophy: 'PH',
  how_it_works: 'HW',
  discipline: 'DS',
  founder_note: 'SN',
};

const CATEGORY_BADGE_STYLES = {
  market_notes: { bg: 'rgba(90,158,114,0.15)', color: '#5A9E72' },
  philosophy:   { bg: 'rgba(212,160,84,0.12)', color: '#D4A054' },
  how_it_works: { bg: 'rgba(130,160,210,0.12)', color: '#82A0D2' },
  discipline:   { bg: 'rgba(196,104,107,0.12)', color: '#C4686B' },
  founder_note: { bg: 'rgba(90,158,114,0.15)', color: '#5A9E72' },
};

const COMPACT_LIMIT = 8;

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

  const [showAll, setShowAll] = useState(false);
  const mountAnimDone = useRef(false);

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
    if (!loading && !mountAnimDone.current) {
      setAnimateIn(true);
      const t = setTimeout(() => { mountAnimDone.current = true; }, 1200);
      return () => clearTimeout(t);
    } else if (!loading && mountAnimDone.current) {
      setAnimateIn(true);
    } else {
      setAnimateIn(false);
    }
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

  const featured = insights.length > 0 ? insights[0] : null;
  const remaining = insights.slice(1);
  const compactList = showAll ? remaining : remaining.slice(0, COMPACT_LIMIT);
  const hasMore = remaining.length > COMPACT_LIMIT;
  const shouldAnimate = !mountAnimDone.current;

  return (
    <div style={{ padding: '0' }}>
      <style>{`
        @keyframes insightsFadeUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div style={{ padding: '20px 20px 0' }}>
        <OnboardingCard cardId="journal" title="THE SHARP JOURNAL">
          Articles on model philosophy, market structure, and discipline. Market Notes are daily reports for Pro members. Everything else is open to all.
        </OnboardingCard>

        {/* Section label */}
        <div style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '10px',
          fontWeight: 500,
          letterSpacing: '2.5px', textTransform: 'uppercase',
          color: '#454B5C',
          marginBottom: '12px',
        }}>Sharp Journal</div>

        {/* Category filter pills */}
        <div style={{
          display: 'flex', gap: '6px', overflowX: 'auto',
          paddingBottom: '2px',
          marginBottom: '20px',
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}>
          {CATEGORIES.map(cat => {
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => { setActiveCategory(cat.id); setShowAll(false); }}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: isActive ? 'rgba(90,158,114,0.15)' : '#131720',
                  color: isActive ? '#5A9E72' : '#626878',
                  fontSize: '12px', fontWeight: 500,
                  fontFamily: "'Inter', var(--font-sans), sans-serif",
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  transition: 'all 0.15s ease',
                }}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ padding: '0 0 100px' }}>
        {loading ? (
          <div style={{ padding: '0 20px' }}><InsightsSkeleton /></div>
        ) : insights.length === 0 ? (
          <div style={{ padding: '0 20px' }}>
            <PinnedGuideCard onTap={() => { loadInsights(); }} animDelay="0.05s" />
            <EmptyInsights category={activeCategory} />
          </div>
        ) : (
          <>
            <PinnedGuideCard onTap={() => {
              const guide = insights.find(i => i.slug === 'beginners-guide');
              if (guide) selectAndTrack(guide);
              else { setActiveCategory('all'); loadInsights(); }
            }} animDelay={shouldAnimate ? '0.05s' : undefined} />

            {featured && (
              <FeaturedArticleCard
                insight={featured}
                onTap={() => selectAndTrack(featured)}
                animDelay={shouldAnimate ? '0.12s' : undefined}
              />
            )}

            {remaining.length > 0 && (
              <div style={{
                padding: '0 20px', marginBottom: '16px',
                display: 'flex', alignItems: 'center', gap: '12px',
                animation: shouldAnimate ? 'insightsFadeUp 0.35s ease 0.18s both' : 'none',
              }}>
                <div style={{ flex: 1, height: '1px', background: '#1C2130' }} />
                <span style={{
                  fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
                  fontSize: '9px', fontWeight: 500,
                  color: '#454B5C',
                  letterSpacing: '2px', textTransform: 'uppercase',
                  flexShrink: 0,
                }}>Recent</span>
                <div style={{ flex: 1, height: '1px', background: '#1C2130' }} />
              </div>
            )}

            {compactList.length > 0 && (
              <div style={{ padding: '0 20px' }}>
                {compactList.map((insight, i) => (
                  <CompactArticleRow
                    key={insight.id}
                    insight={insight}
                    isLast={i === compactList.length - 1}
                    onTap={() => selectAndTrack(insight)}
                    animDelay={shouldAnimate ? `${0.22 + i * 0.04}s` : undefined}
                    animateIn={shouldAnimate}
                  />
                ))}
              </div>
            )}

            {hasMore && !showAll && (
              <div style={{ padding: '16px 20px 24px', textAlign: 'center' }}>
                <button
                  onClick={() => setShowAll(true)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
                    fontSize: '12px',
                    color: '#5A9E72',
                    letterSpacing: '0.5px',
                  }}
                >
                  View all articles ›
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function PinnedGuideCard({ onTap, animDelay }) {
  return (
    <button
      onClick={onTap}
      style={{
        width: 'calc(100% - 40px)',
        margin: '0 20px 16px',
        textAlign: 'left',
        background: 'rgba(90,158,114,0.04)',
        border: '1px solid rgba(90,158,114,0.12)',
        borderRadius: '10px',
        padding: '14px 16px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        transition: 'border-color 0.2s, background 0.2s',
        animation: animDelay ? `insightsFadeUp 0.35s ease ${animDelay} both` : 'none',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(90,158,114,0.25)'; e.currentTarget.style.background = 'rgba(90,158,114,0.08)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(90,158,114,0.12)'; e.currentTarget.style.background = 'rgba(90,158,114,0.04)'; }}
    >
      <div style={{
        width: '36px', height: '36px', borderRadius: '8px',
        backgroundColor: 'rgba(90,158,114,0.15)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5A9E72" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '9px', fontWeight: 600,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: '#5A9E72',
          marginBottom: '3px',
        }}>Start Here</div>
        <div style={{
          fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
          fontSize: '14px', fontWeight: 500,
          color: '#E2E4E8',
          lineHeight: 1.3,
        }}>A beginner's guide to SharpPicks</div>
        <div style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '10px',
          color: '#454B5C',
          marginTop: '2px',
        }}>5 min read · Evan Cole</div>
      </div>
      <span style={{ color: '#454B5C', fontSize: '14px', flexShrink: 0 }}>›</span>
    </button>
  );
}

function CategoryBadge({ category, abbreviated = false }) {
  const badgeStyle = CATEGORY_BADGE_STYLES[category] || { bg: 'rgba(232,234,237,0.08)', color: 'rgba(232,234,237,0.5)' };
  const label = abbreviated
    ? (CATEGORY_ABBR[category] || '??')
    : (CATEGORY_LABELS[category] || category);

  if (abbreviated) {
    return (
      <div style={{
        width: '28px', height: '28px', borderRadius: '6px',
        backgroundColor: badgeStyle.bg, color: badgeStyle.color,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
        fontSize: '8px', fontWeight: 700,
        letterSpacing: '0.5px',
        marginTop: '1px',
      }}>
        {label}
      </div>
    );
  }

  return (
    <span style={{
      fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
      fontSize: '9px', fontWeight: 600,
      letterSpacing: '1.2px',
      textTransform: 'uppercase',
      padding: '3px 8px',
      borderRadius: '4px',
      backgroundColor: badgeStyle.bg,
      color: badgeStyle.color,
      flexShrink: 0,
    }}>
      {label}
    </span>
  );
}

function FeaturedArticleCard({ insight, onTap, animDelay }) {
  return (
    <button
      onClick={onTap}
      style={{
        width: 'calc(100% - 40px)',
        margin: '0 20px 28px',
        textAlign: 'left',
        background: '#131720',
        border: '1px solid #1C2130',
        borderRadius: '12px',
        padding: '20px',
        cursor: 'pointer',
        display: 'block',
        position: 'relative',
        overflow: 'hidden',
        transition: 'border-color 0.2s',
        animation: animDelay ? `insightsFadeUp 0.35s ease ${animDelay} both` : 'none',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = '#2A3040'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = '#1C2130'; }}
    >
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '1px',
        background: 'linear-gradient(90deg, #5A9E72, transparent 60%)',
        opacity: 0.4,
      }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <CategoryBadge category={insight.category} />
        <span style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '10px', color: '#454B5C',
          letterSpacing: '0.3px',
        }}>
          Sharp Journal · {insight.reading_time_minutes || 2} min
        </span>
      </div>

      <div style={{
        fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
        fontSize: '19px', fontWeight: 600,
        color: '#E2E4E8',
        lineHeight: 1.35,
        letterSpacing: '-0.2px',
        marginBottom: '10px',
      }}>
        {(insight.title || '').replace(/—/g, '-')}
      </div>

      {insight.excerpt && (
        <div style={{
          fontFamily: "'Inter', var(--font-sans), sans-serif",
          fontSize: '13px',
          color: '#626878',
          lineHeight: 1.6,
          marginBottom: '14px',
        }}>
          {insight.excerpt}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '10px', color: '#454B5C',
          letterSpacing: '0.3px',
        }}>
          {formatDate(insight.publish_date)}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '10px', fontWeight: 500,
          color: '#5A9E72',
          letterSpacing: '0.5px',
          display: 'flex', alignItems: 'center', gap: '4px',
        }}>
          Read →
        </span>
      </div>
    </button>
  );
}

function formatDateShort(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function CompactArticleRow({ insight, isLast, onTap, animDelay, animateIn = false }) {
  return (
    <button
      onClick={onTap}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '13px 0',
        background: 'none',
        border: 'none',
        borderBottom: isLast ? 'none' : '1px solid rgba(28,33,48,0.5)',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'opacity 0.15s',
        animation: animateIn && animDelay ? `insightsFadeUp 0.3s ease ${animDelay} both` : 'none',
      }}
      onPointerDown={e => { e.currentTarget.style.opacity = '0.7'; }}
      onPointerUp={e => { e.currentTarget.style.opacity = '1'; }}
      onPointerLeave={e => { e.currentTarget.style.opacity = '1'; }}
    >
      <CategoryBadge category={insight.category} abbreviated />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: "'Inter', var(--font-sans), sans-serif",
          fontSize: '13px', fontWeight: 500,
          color: '#9DA1AC',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: 1.4,
        }}>
          {(insight.title || '').replace(/—/g, '-')}
        </div>
      </div>
      <span style={{
        fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
        fontSize: '10px',
        color: '#454B5C',
        flexShrink: 0,
        letterSpacing: '0.3px',
        marginTop: '2px',
      }}>
        {formatDateShort(insight.publish_date)}
      </span>
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

  // Top Edge Breakdown
  let topEdge = null;
  const teSection = (sections['top edge'] || '').trim();
  if (teSection) {
    const field = (key) => { const m = teSection.match(new RegExp(`^- ${key}:\\s*(.+)$`, 'm')); return m ? m[1].trim() : null; };
    const reasons = [];
    for (const line of teSection.split('\n')) {
      const rm = line.match(/^- reason:\s*(.+)$/);
      if (rm) reasons.push(rm[1].trim());
    }
    topEdge = {
      pick: field('pick'), edge: field('edge'), matchup: field('matchup'),
      modelLine: field('model_line'), marketLine: field('market_line'),
      gap: field('gap'), status: field('status'), reasons,
    };
  }

  // Edge Map
  let edgeMap = [];
  const emSection = (sections['edge map'] || '').trim();
  if (emSection) {
    for (const line of emSection.split('\n')) {
      const m = line.match(/^- (.+?) \| ([+-]?[\d.]+)% \| (.+)$/);
      if (m) edgeMap.push({ game: m[1].trim(), edge: parseFloat(m[2]), status: m[3].trim() });
    }
  }

  // Near Misses
  let nearMisses = [];
  const nmSection = (sections['near misses'] || '').trim();
  if (nmSection) {
    for (const line of nmSection.split('\n')) {
      const m = line.match(/^- (.+?) \| \+?([\d.]+)% \| (.+)$/);
      if (m) nearMisses.push({ game: m[1].trim(), edge: parseFloat(m[2]), reason: m[3].trim() });
    }
  }

  return { obs, impl, edges, signals, density, favEdges, dogEdges, whyText, topEdge, edgeMap, nearMisses };
}

function MarketNoteContent({ insight }) {
  const data = parseMarketNote(insight.content);
  const total = data.favEdges + data.dogEdges;
  const favPct = total > 0 ? Math.round(data.favEdges / total * 100) : 50;
  const dogPct = total > 0 ? 100 - favPct : 50;
  const densityStr = data.density % 1 === 0 ? `${Math.round(data.density)}%` : `${data.density}%`;

  const brandGreen = '#5A9E72';
  const brandRed = '#8B6F70';
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

      {/* Top Edge Breakdown */}
      {data.topEdge && (
        <div style={{
          background: bgCard, border: `1px solid ${border}`,
          borderRadius: '8px', padding: '20px', marginBottom: '24px',
        }}>
          <div style={sectionLabel}>Top Edge</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
            <span style={{ fontFamily: sans, fontSize: '16px', fontWeight: 500, color: textPrimary }}>
              {data.topEdge.pick}
            </span>
            <span style={{ fontFamily: mono, fontSize: '16px', fontWeight: 500, color: brandGreen }}>
              {data.topEdge.edge}
            </span>
          </div>
          <div style={{ fontFamily: mono, fontSize: '11px', color: textMuted, marginBottom: '10px' }}>
            {data.topEdge.matchup}
          </div>
          {(data.topEdge.modelLine || data.topEdge.marketLine) && (
            <div style={{ fontFamily: mono, fontSize: '11px', color: textMuted, marginBottom: '10px' }}>
              {data.topEdge.modelLine && <span>Model: <span style={{ color: brandGreen }}>{data.topEdge.modelLine}</span></span>}
              {data.topEdge.modelLine && data.topEdge.marketLine && <span> · </span>}
              {data.topEdge.marketLine && <span>Market: <span style={{ color: textPrimary }}>{data.topEdge.marketLine}</span></span>}
              {data.topEdge.gap && <span> · Gap: {data.topEdge.gap}</span>}
            </div>
          )}
          {data.topEdge.status && (
            <div style={{ marginBottom: data.topEdge.reasons.length > 0 ? '10px' : 0 }}>
              <span style={{
                fontFamily: mono, fontSize: '10px', fontWeight: 600,
                padding: '3px 8px', borderRadius: '4px',
                color: data.topEdge.status === 'Signal issued' ? brandGreen : textMuted,
                background: data.topEdge.status === 'Signal issued' ? greenDim : 'rgba(122,132,148,0.1)',
              }}>{data.topEdge.status}</span>
            </div>
          )}
          {data.topEdge.reasons.length > 0 && (
            <div style={{ borderLeft: '2px solid rgba(90,158,114,0.3)', paddingLeft: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {data.topEdge.reasons.map((r, i) => (
                <div key={i} style={{ fontFamily: sans, fontSize: '12px', color: textSecondary, lineHeight: 1.5 }}>{r}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Edge Map */}
      {data.edgeMap.length > 0 && (
        <div style={{
          background: bgCard, border: `1px solid ${border}`,
          borderRadius: '8px', padding: '20px', marginBottom: '24px',
        }}>
          <div style={sectionLabel}>Edge Map</div>
          {(() => {
            const maxEdge = Math.max(...data.edgeMap.map(g => Math.abs(g.edge)), 1);
            const thresholdPct = (3.5 / maxEdge) * 100;
            return (
              <div style={{ position: 'relative' }}>
                {data.edgeMap.map((g, i) => {
                  const barPct = Math.min((Math.abs(g.edge) / maxEdge) * 100, 100);
                  const isPositive = g.edge >= 0;
                  const barColor = g.status === 'Signal' ? brandGreen : isPositive ? 'rgba(90,158,114,0.5)' : brandRed;
                  const edgeColor = g.status === 'Signal' ? brandGreen : isPositive ? '#7a9e87' : brandRed;
                  const statusColor = g.status === 'Signal' ? brandGreen : textMuted;
                  return (
                    <div key={i} style={{
                      display: 'grid', gridTemplateColumns: '100px 55px 1fr 90px',
                      alignItems: 'center', gap: '8px', padding: '6px 0',
                      borderBottom: i < data.edgeMap.length - 1 ? '0.5px solid rgba(30,48,80,0.3)' : 'none',
                    }}>
                      <span style={{ fontFamily: sans, fontSize: '12px', color: '#c8cdd4', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {g.game}
                      </span>
                      <span style={{ fontFamily: mono, fontSize: '11px', color: edgeColor, textAlign: 'right' }}>
                        {g.edge >= 0 ? '+' : ''}{g.edge}%
                      </span>
                      <div style={{ position: 'relative', height: '8px', background: 'rgba(20,26,46,0.6)', borderRadius: '2px' }}>
                        <div style={{
                          height: '100%', width: `${barPct}%`, background: barColor,
                          borderRadius: '2px', transition: 'width 0.3s ease',
                        }} />
                        {thresholdPct <= 100 && (
                          <div style={{
                            position: 'absolute', left: `${thresholdPct}%`, top: -2, bottom: -2,
                            width: '1px', borderLeft: '1px dashed rgba(90,158,114,0.4)',
                          }} />
                        )}
                      </div>
                      <span style={{ fontFamily: mono, fontSize: '9px', color: statusColor, textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {g.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      )}

      {/* Near Misses */}
      {data.nearMisses.length > 0 && (
        <div style={{
          background: bgCard, border: `1px solid ${border}`,
          borderLeft: '3px solid #2a3a52',
          borderRadius: '8px', padding: '20px', marginBottom: '24px',
        }}>
          <div style={{ ...sectionLabel, color: textMuted }}>Near Misses</div>
          {data.nearMisses.map((nm, i) => (
            <div key={i} style={{
              padding: '8px 0',
              borderBottom: i < data.nearMisses.length - 1 ? '0.5px solid rgba(30,48,80,0.3)' : 'none',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                <span style={{ fontFamily: sans, fontSize: '13px', fontWeight: 500, color: '#c8cdd4' }}>{nm.game}</span>
                <span style={{ fontFamily: mono, fontSize: '11px', color: '#7a9e87' }}>+{nm.edge}%</span>
              </div>
              <div style={{ fontFamily: sans, fontSize: '12px', color: textMuted, lineHeight: 1.5 }}>{nm.reason}</div>
            </div>
          ))}
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

      {/* Sharp Principle */}
      <div style={{
        borderTop: `1px solid ${border}`,
        borderBottom: `1px solid ${border}`,
        padding: '20px 0', marginBottom: '40px',
      }}>
        <div style={{
          fontFamily: mono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: textMuted, marginBottom: '10px',
        }}>Sharp Principle</div>
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
      {/* Progress bar */}
      <div style={{
        position: 'sticky', top: 0, left: 0, right: 0, height: '2px',
        zIndex: 2, background: 'transparent',
      }}>
        <div style={{
          height: '100%',
          width: `${scrollProgress * 100}%`,
          background: 'linear-gradient(90deg, #5A9E72, #7BC493)',
          transition: 'width 0.1s linear',
        }} />
      </div>

      <div style={{ maxWidth: '430px', margin: '0 auto' }}>
      {/* Top bar */}
      <div style={{
        position: 'sticky', top: '2px', zIndex: 1,
        background: 'rgba(10,13,20,0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        padding: '14px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
        borderBottom: '1px solid #1C2130',
      }}>
        <button
          onClick={onBack}
          aria-label="Go back"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#626878', fontSize: '20px', lineHeight: 1,
            padding: '4px', margin: '-4px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            minWidth: '44px', minHeight: '44px',
          }}
        >
          ←
        </button>
        <span style={{
          fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
          fontSize: '11px', fontWeight: 500,
          letterSpacing: '3px', textTransform: 'uppercase',
          color: '#626878',
        }}>Sharp Journal</span>
      </div>

      <div ref={contentRef} style={{ padding: '0 20px 60px' }}>
        {isMarketNote ? (
          <div style={{ paddingTop: '24px' }}>
          <MarketNoteContent insight={insight} />
          </div>
        ) : (
          <>
            {/* Hero */}
            <div style={{
              padding: '32px 0 28px',
              borderBottom: '1px solid #1C2130',
              marginBottom: '32px',
              animation: fadeIn ? 'insightsFadeUp 0.4s ease 0.05s both' : 'none',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
                <HeroCategoryTag category={insight.category} slug={insight.slug} />
                <span style={{
                  fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
                  fontSize: '10px', color: '#454B5C', letterSpacing: '0.3px',
                }}>
                  Sharp Journal · {insight.reading_time_minutes || 2} min read
                </span>
              </div>

              <h1 style={{
                fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
                fontSize: '28px', fontWeight: 600,
                color: '#E2E4E8',
                lineHeight: 1.25,
                letterSpacing: '-0.3px',
                marginBottom: '10px',
              }}>
                {(insight.title || '').replace(/—/g, ' -- ')}
              </h1>

              <span style={{
                fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
                fontSize: '11px', color: '#454B5C', letterSpacing: '0.3px',
              }}>
                {formatDate(insight.publish_date)}
              </span>
            </div>

            {/* Body */}
            <div style={{
              fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
              fontSize: '16px',
              color: '#9DA1AC',
              lineHeight: 1.8,
              animation: fadeIn ? 'insightsFadeUp 0.4s ease 0.12s both' : 'none',
            }}>
              {paragraphs.map((p, i) => {
                const trimmed = p.trim();
                const isHowItWorks = insight.category === 'how_it_works' || insight.story_type === 'how_it_works';
                const isGlossarySection = isHowItWorks && /^## Key Concepts/.test(trimmed);

                if (trimmed === '---') {
                  return (
                    <div key={i} style={{
                      border: 'none', height: '1px', margin: '36px 0',
                      background: '#1C2130',
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
                      fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
                      fontSize: '20px', fontWeight: 600,
                      color: '#E2E4E8',
                      lineHeight: 1.3, letterSpacing: '-0.2px',
                      marginTop: '40px', marginBottom: '16px',
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
                    <blockquote key={i} style={{
                      borderLeft: '2px solid #5A9E72',
                      padding: '14px 18px', margin: '28px 0',
                      background: 'rgba(90,158,114,0.04)',
                      borderRadius: '0 6px 6px 0',
                    }}>
                      <p style={{
                        fontFamily: "'IBM Plex Serif', serif",
                        fontSize: '14px', lineHeight: 1.7,
                        color: '#9DA1AC', fontStyle: 'italic',
                        margin: 0,
                      }}>
                        {parseInlineMarkdown(quoteText)}
                      </p>
                    </blockquote>
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
                  return <p key={i} className="kicker" style={{
                    fontSize: '15px', fontWeight: 500,
                    color: '#E2E4E8', marginBottom: '28px',
                  }}>{parseInlineMarkdown(p)}</p>;
                }

                return <p key={i} style={{ marginBottom: '22px' }}>{parseInlineMarkdown(p)}</p>;
              })}
            </div>

            <WhyThisMatters insight={insight} />

            {/* Author byline */}
            <div style={{
              margin: '40px 0 32px',
              display: 'flex', alignItems: 'center', gap: '14px',
              animation: fadeIn ? 'insightsFadeUp 0.3s ease 0.18s both' : 'none',
            }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: '#181D28', border: '1px solid #1C2130',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px', fontWeight: 600, color: '#5A9E72',
                flexShrink: 0,
              }}>EC</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{
                  fontFamily: "'Inter', var(--font-sans), sans-serif",
                  fontSize: '14px', fontWeight: 600, color: '#E2E4E8',
                }}>Evan Cole</span>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '10px', color: '#454B5C', letterSpacing: '0.3px',
                }}>Head of Signal Intelligence</span>
              </div>
            </div>
          </>
        )}

        {/* CTA link */}
        {!isMarketNote && insight.cta_text && (
          <a
            onClick={() => onNavigate && onNavigate(insight.cta_target || 'performance', 'model')}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              gap: '6px', padding: '14px 20px',
              background: 'transparent',
              border: '1px solid #1C2130', borderRadius: '8px',
              marginBottom: '16px', cursor: 'pointer',
              textDecoration: 'none',
              transition: 'border-color 0.2s, background 0.2s',
              animation: fadeIn ? 'insightsFadeUp 0.3s ease 0.22s both' : 'none',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'rgba(90,158,114,0.3)';
              e.currentTarget.style.background = 'rgba(90,158,114,0.04)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = '#1C2130';
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <span style={{
              fontFamily: "'Inter', var(--font-sans), sans-serif",
              fontSize: '13px', fontWeight: 500, color: '#9DA1AC',
            }}>{insight.cta_text || 'See how this discipline performs in real picks'}</span>
            <span style={{ fontSize: '14px', color: '#5A9E72' }}>→</span>
          </a>
        )}

        {!isMarketNote && !insight.cta_text && (
          <a
            onClick={() => onNavigate && onNavigate('performance', 'model')}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              gap: '6px', padding: '14px 20px',
              background: 'transparent',
              border: '1px solid #1C2130', borderRadius: '8px',
              marginBottom: '16px', cursor: 'pointer',
              textDecoration: 'none',
              transition: 'border-color 0.2s, background 0.2s',
              animation: fadeIn ? 'insightsFadeUp 0.3s ease 0.22s both' : 'none',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'rgba(90,158,114,0.3)';
              e.currentTarget.style.background = 'rgba(90,158,114,0.04)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = '#1C2130';
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <span style={{
              fontFamily: "'Inter', var(--font-sans), sans-serif",
              fontSize: '13px', fontWeight: 500, color: '#9DA1AC',
            }}>See how this discipline performs in real picks</span>
            <span style={{ fontSize: '14px', color: '#5A9E72' }}>→</span>
          </a>
        )}

        {insight.has_related_picks && (
          <RelatedPicksSection insightId={insight.id} />
        )}

        {/* Next Read card */}
        {nextInsight && (
          <button
            onClick={() => onSelectInsight(nextInsight)}
            style={{
              width: '100%', textAlign: 'left',
              background: '#131720',
              border: '1px solid #1C2130', borderRadius: '10px',
              padding: '16px 18px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '14px',
              transition: 'border-color 0.2s',
              animation: fadeIn ? 'insightsFadeUp 0.3s ease 0.26s both' : 'none',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = '#5A9E72';
              e.currentTarget.querySelector('.nr-title').style.color = '#E2E4E8';
              e.currentTarget.querySelector('.nr-arrow').style.color = '#5A9E72';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = '#1C2130';
              e.currentTarget.querySelector('.nr-title').style.color = '#9DA1AC';
              e.currentTarget.querySelector('.nr-arrow').style.color = '#454B5C';
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '9px', fontWeight: 600,
                letterSpacing: '1.5px', textTransform: 'uppercase',
                color: '#454B5C', marginBottom: '6px',
              }}>Next Read</div>
              <div className="nr-title" style={{
                fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
                fontSize: '14px', fontWeight: 500,
                color: '#9DA1AC', lineHeight: 1.4,
                transition: 'color 0.2s',
              }}>
                {(nextInsight.title || '').replace(/—/g, ' -- ')}
              </div>
            </div>
            <span className="nr-arrow" style={{
              color: '#454B5C', fontSize: '16px', flexShrink: 0,
              transition: 'color 0.2s',
            }}>›</span>
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
      margin: '40px 0',
      padding: '28px 24px',
      background: 'linear-gradient(135deg, rgba(90,158,114,0.04), rgba(90,158,114,0.02))',
      borderLeft: '3px solid #5A9E72',
      borderRadius: '0 10px 10px 0',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: 0, left: '-3px', right: 0,
        height: '1px',
        background: 'linear-gradient(90deg, #5A9E72, transparent 50%)',
        opacity: 0.3, borderRadius: '0 10px 0 0',
      }} />
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '9px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: '#454B5C',
        marginBottom: '16px',
      }}>{label || 'Sharp Principle'}</div>
      <div style={{
        fontFamily: "'IBM Plex Serif', serif",
        fontSize: '18px',
        fontWeight: 500,
        color: '#E2E4E8',
        lineHeight: 1.6,
        textAlign: 'left',
      }}>
        {parseInlineMarkdown(text)}
      </div>
    </div>
  );
}

function WhyThisMatters({ insight }) {
  const mattersMap = {
    'discipline': 'This is why SharpPicks passes most games. The goal is not activity. The goal is capital preservation. Discipline compounds. Impulse erodes.',
    'philosophy': 'This principle shapes every decision the model makes. It is not strategy -- it is structure.',
    'how_it_works': 'Understanding how the system works builds the trust needed to follow it through variance.',
    'market_notes': 'The market is your competition. Understanding it is the first step toward finding real edge.',
    'founder_note': 'These are the convictions behind the code. The model is a reflection of these beliefs.',
  };

  const text = mattersMap[insight.category] || mattersMap['philosophy'];

  return (
    <div style={{
      margin: '40px 0',
      padding: '20px',
      background: '#131720',
      border: '1px solid #1C2130',
      borderRadius: '8px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: '1px',
        background: 'linear-gradient(90deg, #5A9E72, transparent 40%)',
        opacity: 0.4, borderRadius: '8px 8px 0 0',
      }} />
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '9px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: '#454B5C',
        marginBottom: '8px',
      }}>Why This Matters</div>
      <p style={{
        fontSize: '13px',
        color: '#9DA1AC',
        lineHeight: 1.65,
        margin: 0,
        fontFamily: "'Inter', var(--font-sans), sans-serif",
      }}>
        {text}
      </p>
    </div>
  );
}

const HERO_TAG_STYLES = {
  philosophy:   { bg: 'rgba(212,160,84,0.12)', color: '#D4A054' },
  discipline:   { bg: 'rgba(196,104,107,0.12)', color: '#C4686B' },
  market_notes: { bg: 'rgba(90,158,114,0.15)', color: '#5A9E72' },
  how_it_works: { bg: 'rgba(130,160,210,0.12)', color: '#82A0D2' },
  founder_note: { bg: 'rgba(90,158,114,0.15)', color: '#5A9E72' },
};

function HeroCategoryTag({ category, slug }) {
  const isStartHere = slug === 'beginners-guide';
  const catKey = isStartHere ? 'founder_note' : (category || 'philosophy');
  const style = HERO_TAG_STYLES[catKey] || HERO_TAG_STYLES.philosophy;
  const label = isStartHere
    ? 'Start Here'
    : (CATEGORY_LABELS[category] || category || '');

  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '9px', fontWeight: 600,
      letterSpacing: '1.5px', textTransform: 'uppercase',
      padding: '4px 10px', borderRadius: '4px',
      background: style.bg, color: style.color,
    }}>
      {label}
    </span>
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

function EmptyInsights({ category }) {
  const catLabel = category && category !== 'all'
    ? CATEGORY_LABELS[category] || category
    : null;
  return (
    <div style={{
      padding: '40px 24px',
      textAlign: 'center',
    }}>
      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '14px',
        color: 'rgba(232,234,237,0.35)',
        lineHeight: '1.6',
      }}>
        {catLabel
          ? `No articles in ${catLabel} yet.`
          : 'No articles yet.'}
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
