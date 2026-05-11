// TodaysReadCard — Field Guide rotating article tile for the post-midnight
// home view. Editorial format matching the May 2026 Midnight State mockup:
// eyebrow (FIELD GUIDE · {category} · {n} min read), serif title, excerpt,
// and a "From the SharpPicks Field Guide" + Read → CTA footer.
//
// Picks one evergreen (non-market_notes) article from the insights array
// using a stable date-seeded rotation so the same article shows for the
// whole midnight window.

const SP = {
  surface: '#121725',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  green: '#5A9E72',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
};

const CAT_LABELS = {
  philosophy: 'Philosophy',
  discipline: 'Discipline',
  how_it_works: 'How It Works',
  founder_note: 'Signal Notes',
  education: 'Education',
};

function pickEvergreenArticle(articles, sport) {
  if (!Array.isArray(articles) || articles.length === 0) return null;
  // Filter out daily Market Notes — those rotate via the morning report.
  // Field Guide cards should be evergreen content (Philosophy / Discipline /
  // How It Works / Founder Notes / Education).
  const evergreen = articles.filter((a) => a && a.category && a.category !== 'market_notes');
  if (!evergreen.length) return null;
  // Date-seeded rotation, offset by sport so NBA / MLB / WNBA tabs each
  // get a different article on the same ET day instead of all surfacing
  // the same one. Stable for the whole day per (sport, date) pair.
  const sportOffset = { nba: 0, mlb: 1, wnba: 2 }[(sport || 'nba').toLowerCase()] ?? 0;
  const seed = (() => {
    try {
      const ymd = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
      return ymd.split('-').reduce((a, b) => a + parseInt(b, 10), 0);
    } catch { return 0; }
  })();
  return evergreen[(seed + sportOffset) % evergreen.length];
}

export default function TodaysReadCard({ articles, onOpen, sport }) {
  const article = pickEvergreenArticle(articles, sport);
  if (!article) return null;

  const catLabel = CAT_LABELS[article.category] || article.category || 'Sharp Journal';
  const minutes = article.reading_time_minutes || article.read_time || 3;
  const isClickable = typeof onOpen === 'function';
  const handleOpen = () => { if (isClickable) onOpen(article); };

  return (
    <div style={{
      background: SP.surface,
      border: `1px solid ${SP.border}`,
      borderRadius: '14px',
      padding: '22px',
      marginBottom: '22px',
      cursor: isClickable ? 'pointer' : 'default',
      fontFamily: SP.fontSans,
    }}
      onClick={handleOpen}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleOpen(); } } : undefined}
    >
      <div style={{
        display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '14px',
        fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
      }}>
        <span style={{ color: SP.green, display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: 5, height: 5, background: SP.green, borderRadius: '50%' }} />
          Sharp Journal
        </span>
        <span style={{ color: SP.text4 }}>·</span>
        <span>{catLabel}</span>
        <span style={{ color: SP.text4 }}>·</span>
        <span>{minutes} min read</span>
      </div>

      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '20px', fontWeight: 600,
        color: SP.text, lineHeight: 1.25, margin: '0 0 8px',
      }}>{article.title}</h2>

      {article.excerpt && (
        <p style={{
          fontSize: '13px', lineHeight: 1.55, color: SP.text2,
          margin: '0 0 16px',
        }}>{article.excerpt}</p>
      )}

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        paddingTop: '14px', borderTop: `1px solid ${SP.border2}`,
      }}>
        <span style={{
          fontFamily: SP.fontMono, fontSize: '10px', color: SP.text4,
          letterSpacing: '0.04em',
        }}>From the Sharp Journal</span>
        {isClickable && (
          <span style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
            display: 'inline-flex', alignItems: 'center', gap: '5px',
          }}>
            Read
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </span>
        )}
      </div>
    </div>
  );
}
