import { useState, useEffect, useRef } from 'react';

/**
 * SharpJournalArticle
 *
 * Locked rendering for Sharp Journal articles. Spec: docs/sharp-journal-spec.md.
 * Reference HTML: docs/sharp-journal-locked.html.
 *
 * Renders all 17 locked elements from the spec: reading progress bar, nav bar,
 * article meta (content tag, journal, read time), H1, date, byline, section
 * dividers, H2, H3, body copy, inline stats, Sharp Principle pull-quote,
 * Observation callout, pull-quote, Why This Matters footer (required), cross-
 * edition link, article footer.
 *
 * Content authoring conventions (markdown-ish):
 *   ## Section title             -> H2 with auto section-divider above
 *   ### Sub-section title        -> H3 (no divider)
 *   > **Sharp Principle**        -> Sharp Principle block (italic IBM Plex Serif)
 *   > Quote text on next line
 *   > [Observation]              -> Observation callout (NOT italic, analytical)
 *   > Observation text
 *   >>> Centered pull quote      -> Pull quote (editorial only, rare)
 *   **bold**                     -> <strong>
 *   *italic*                     -> <em>
 *   `code`                       -> inline code
 *   [stat:+2.0]                  -> green stat span
 *   [stat-:-3.4]                 -> negative stat span
 *   [stat:any]                   -> neutral stat span
 *
 * Why This Matters source priority:
 *   1. insight.why_this_matters prop (explicit field on the article)
 *   2. Last `> WHY THIS MATTERS:` block in content
 *   3. insight.excerpt as fallback
 *   4. Generic default ("Discipline is the edge.")
 *
 * Voice rules (em-dashes, exclamation marks, AI filler, hype words) are NOT
 * enforced at render time. Authoring linter is a separate concern per the spec.
 */

// "Field Guide" as a brand was retired. Sharp Journal is the umbrella;
// each article is tagged with the section it belongs to. Green is the
// default section color; how-it-works gets blue for technical pieces and
// editorial / market notes get amber for opinion-shaped content.
const CATEGORY_TAG = {
  how_it_works: { label: 'How it works', className: 'tech' },
  discipline:   { label: 'Discipline',   className: 'section' },
  philosophy:   { label: 'Philosophy',   className: 'section' },
  education:    { label: 'Education',    className: 'section' },
  founder_note: { label: 'Editorial',    className: 'editorial' },
  editorial:    { label: 'Editorial',    className: 'editorial' },
  market_notes: { label: 'Market notes', className: 'editorial' },
  morning_edition: { label: 'Morning Edition', className: 'section' },
  evening_edition: { label: 'Evening Edition', className: 'section' },
};

const TAG_STYLE = {
  tech: {
    background: 'var(--sp-blue-soft)',
    color: 'var(--sp-blue)',
    border: '1px solid rgba(79, 134, 247, 0.3)',
  },
  section: {
    background: 'var(--sp-green-soft)',
    color: 'var(--sp-green)',
    border: '1px solid rgba(90, 158, 114, 0.3)',
  },
  editorial: {
    background: 'var(--sp-amber-soft)',
    color: 'var(--sp-amber)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
  },
};

function formatArticleDate(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
  } catch {
    return '';
  }
}

// Inline markdown: bold, italic, code, and stat tokens. Returns an array of
// React nodes. Spec calls out <strong>/<em>/<code>/.stat as the only inline
// formats. Em-dashes deliberately not rendered specially; spec forbids them.
//
// Stat token shapes accepted:
//   [stat:+1.4]               neutral
//   [stat green:+2.0]         positive
//   [stat-:-3.4]              negative
//   <span class="stat">+1.4</span>          (matches the locked HTML in the spec)
//   <span class="stat green">+2.0</span>
//   <span class="stat negative">-3.4</span>
function renderInline(text, keyPrefix = 'i') {
  if (!text) return [];
  const tokens = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[stat[-+]?(?:\s+green)?\s*:[^\]]+\]|<span class="stat(?:\s+(?:green|negative))?">[^<]+<\/span>)/g;
  let lastIndex = 0;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push(text.slice(lastIndex, match.index));
    }
    tokens.push(match[0]);
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < text.length) tokens.push(text.slice(lastIndex));

  return tokens.map((tok, idx) => {
    const key = `${keyPrefix}-${idx}`;
    if (tok.startsWith('**') && tok.endsWith('**')) {
      return <strong key={key} style={{ color: 'var(--sp-text)', fontWeight: 600 }}>{tok.slice(2, -2)}</strong>;
    }
    if (tok.startsWith('*') && tok.endsWith('*') && tok.length > 2) {
      return <em key={key} style={{ fontStyle: 'italic', color: 'var(--sp-text)' }}>{tok.slice(1, -1)}</em>;
    }
    if (tok.startsWith('`') && tok.endsWith('`')) {
      return (
        <code key={key} style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '14px',
          background: 'rgba(0, 0, 0, 0.3)',
          padding: '1px 6px',
          borderRadius: '3px',
          color: 'var(--sp-text)',
        }}>{tok.slice(1, -1)}</code>
      );
    }
    if (tok.startsWith('[stat')) {
      const m = tok.match(/^\[stat([-+])?(?:\s+green)?\s*:([^\]]+)\]$/);
      if (m) {
        const variant = /\bgreen\b/.test(tok) ? 'green' : (m[1] === '-' ? 'negative' : null);
        return <Stat key={key} variant={variant}>{m[2].trim()}</Stat>;
      }
    }
    if (tok.startsWith('<span class="stat')) {
      const m = tok.match(/^<span class="stat(?:\s+(green|negative))?">([^<]+)<\/span>$/);
      if (m) return <Stat key={key} variant={m[1] || null}>{m[2]}</Stat>;
    }
    return tok;
  });
}

function Stat({ variant, children }) {
  const color =
    variant === 'green' ? 'var(--sp-green)'
    : variant === 'negative' ? '#C4868A'
    : 'var(--sp-text)';
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '0.92em',
      color,
      background: 'rgba(255, 255, 255, 0.04)',
      padding: '1px 5px',
      borderRadius: '3px',
      letterSpacing: '0.02em',
    }}>{children}</span>
  );
}

function SectionDivider() {
  return <div style={{ height: '1px', background: 'var(--sp-border)', margin: '32px 0' }} />;
}

function ArticleH2({ children }) {
  return (
    <h2 style={{
      fontFamily: "'IBM Plex Serif', Georgia, serif",
      fontSize: '22px', fontWeight: 600,
      lineHeight: 1.25, letterSpacing: '-0.005em',
      color: 'var(--sp-text)', marginBottom: '14px',
    }}>{children}</h2>
  );
}

function ArticleH3({ children }) {
  return (
    <h3 style={{
      fontFamily: "'IBM Plex Serif', Georgia, serif",
      fontSize: '17px', fontWeight: 600, lineHeight: 1.3,
      color: 'var(--sp-text)', marginTop: '22px', marginBottom: '10px',
    }}>{children}</h3>
  );
}

function ArticleBody({ children }) {
  return (
    <p style={{
      fontFamily: "'IBM Plex Serif', Georgia, serif",
      fontSize: '16px', fontWeight: 400, lineHeight: 1.6,
      color: 'var(--sp-text-2)', marginBottom: '18px',
    }}>{children}</p>
  );
}

function SharpPrinciple({ text }) {
  return (
    <div style={{
      background: 'var(--sp-green-soft)',
      borderLeft: '3px solid var(--sp-green)',
      borderRadius: '0 12px 12px 0',
      padding: '22px 24px',
      margin: '28px 0',
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase',
        color: 'var(--sp-green)', marginBottom: '12px',
      }}>Sharp Principle</div>
      <div style={{
        fontFamily: "'IBM Plex Serif', Georgia, serif",
        fontStyle: 'italic', fontWeight: 400,
        fontSize: '19px', lineHeight: 1.45,
        color: 'var(--sp-text)',
      }}>{renderInline(text, 'sp')}</div>
    </div>
  );
}

function Observation({ text }) {
  return (
    <div style={{
      background: 'var(--sp-green-soft)',
      borderLeft: '2px solid var(--sp-green)',
      borderRadius: '0 10px 10px 0',
      padding: '16px 20px',
      margin: '24px 0',
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '9px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase',
        color: 'var(--sp-green)', marginBottom: '8px',
      }}>Observation</div>
      <div style={{
        fontFamily: "'IBM Plex Serif', Georgia, serif",
        fontSize: '14px', lineHeight: 1.5,
        color: 'var(--sp-text)',
      }}>{renderInline(text, 'ob')}</div>
    </div>
  );
}

function PullQuote({ text }) {
  return (
    <div style={{
      margin: '32px 0', padding: '0 12px',
      textAlign: 'center',
      fontFamily: "'IBM Plex Serif', Georgia, serif",
      fontSize: '22px', fontWeight: 600, lineHeight: 1.35,
      color: 'var(--sp-text)', letterSpacing: '-0.005em',
    }}>{renderInline(text, 'pq')}</div>
  );
}

function WhyMatters({ text }) {
  if (!text) return null;
  return (
    <div style={{
      background: 'var(--sp-surface)',
      border: '1px solid var(--sp-border)',
      borderRadius: '12px',
      padding: '20px 22px',
      marginTop: '36px',
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase',
        color: 'var(--sp-text-3)', marginBottom: '10px',
      }}>Why this matters</div>
      <div style={{
        fontFamily: "'IBM Plex Serif', Georgia, serif",
        fontSize: '15px', lineHeight: 1.5,
        color: 'var(--sp-text)',
      }}>{renderInline(text, 'wm')}</div>
    </div>
  );
}

function CrossLink({ title, onClick }) {
  if (!title) return null;
  return (
    <a
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 20px', marginTop: '24px',
        background: 'var(--sp-surface)',
        border: '1px solid var(--sp-border)',
        borderRadius: '10px',
        cursor: onClick ? 'pointer' : 'default',
        textDecoration: 'none',
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '9px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase',
          color: 'var(--sp-blue)', marginBottom: '4px',
        }}>Read next</div>
        <div style={{
          fontFamily: "'IBM Plex Serif', Georgia, serif",
          fontSize: '14px', fontWeight: 600,
          color: 'var(--sp-text)', lineHeight: 1.3,
        }}>{title}</div>
      </div>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--sp-text-3)" strokeWidth="2.5" style={{ flexShrink: 0, marginLeft: '12px' }}>
        <path d="M9 18l6-6-6-6" />
      </svg>
    </a>
  );
}

function ArticleFooter({ updatedDate, contentType, version }) {
  const parts = [];
  if (updatedDate) parts.push(`Updated ${updatedDate}`);
  if (contentType) parts.push(`${contentType}${version ? ` ${version}` : ''}`);
  if (!parts.length) return null;
  return (
    <div style={{
      marginTop: '32px',
      paddingTop: '18px',
      borderTop: '1px solid var(--sp-border)',
      textAlign: 'center',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '10px',
      color: 'var(--sp-text-4)',
      letterSpacing: '0.16em',
      textTransform: 'uppercase',
    }}>{parts.join(' · ')}</div>
  );
}

// Extract the inner text of a single class="X-Y" div from a chunk. Strips
// surrounding tags. Returns '' if not found. Used by the HTML-block parser
// for sharp-principle / observation / why-matters constructs since the
// articles encode those blocks as raw HTML per the spec's reference render.
function extractInner(chunk, klass) {
  const re = new RegExp(`<div class="${klass}">([\\s\\S]*?)</div>`);
  const m = chunk.match(re);
  return m ? m[1].trim() : '';
}

// Parse content blocks. Each \n\n separated chunk becomes one block of a
// specific kind. The first matching pattern wins.
//
// Recognizes both markdown-ish authoring (## H2, > **Sharp Principle**,
// >>> pull-quote) and the locked HTML constructions from the spec
// (<div class="sharp-principle"> etc.). HTML form is preferred for new
// content because it matches the reference render in docs/.
//
// Pass articleTitle to suppress a body-level H2 that exactly matches the
// article title (legacy MLB articles authored their body with `## <Title>`
// at the top, which duplicates the H1 the article container already renders).
function parseContent(content, articleTitle = '') {
  if (!content) return [];
  const chunks = content.split(/\n\n+/).map(c => c.trim()).filter(Boolean);
  const blocks = [];
  const normalizedTitle = articleTitle.trim().toLowerCase().replace(/\.$/, '');

  for (const chunk of chunks) {
    // Skip markdown horizontal rules (---) entirely. Old articles used them
    // as section separators; the spec's auto-divider before every H2 makes
    // them redundant, and rendering '---' as body text reads as a typo.
    if (/^-{3,}$/.test(chunk)) continue;

    // Skip a body-level H1: the article container renders the title from
    // frontmatter / insight.title, so an inline H1 in content would be
    // duplicate noise.
    if (/^#\s+/.test(chunk) && !chunk.startsWith('##')) continue;

    // Skip a body-level H2 that matches the article title (legacy authoring
    // pattern where MLB articles mirrored their title as `## Title`).
    if (normalizedTitle) {
      const h2Match = chunk.match(/^##\s+(.+)/);
      if (h2Match) {
        const heading = h2Match[1].trim().toLowerCase().replace(/\.$/, '');
        if (heading === normalizedTitle) continue;
      }
    }

    // Locked HTML constructs (per docs/sharp-journal-locked.html).
    if (chunk.includes('class="sharp-principle"')) {
      const quote = extractInner(chunk, 'sharp-principle-quote');
      if (quote) { blocks.push({ type: 'sharp-principle', text: quote }); continue; }
    }
    if (chunk.includes('class="observation"')) {
      const text = extractInner(chunk, 'observation-text');
      if (text) { blocks.push({ type: 'observation', text }); continue; }
    }
    if (chunk.includes('class="why-matters"')) {
      const text = extractInner(chunk, 'why-matters-text');
      if (text) { blocks.push({ type: 'why-matters', text }); continue; }
    }
    if (chunk.includes('class="pull-quote"')) {
      // Render whatever the div contains, stripped of its outer div tags.
      const m = chunk.match(/<div class="pull-quote">([\s\S]*?)<\/div>/);
      if (m) { blocks.push({ type: 'pull-quote', text: m[1].trim() }); continue; }
    }

    // Pull quote (rare, editorial only): >>> text
    if (chunk.startsWith('>>>')) {
      blocks.push({ type: 'pull-quote', text: chunk.replace(/^>>>\s*/, '') });
      continue;
    }
    // Markdown blockquote with label: > **Sharp Principle** / > **Observation** / etc.
    if (chunk.startsWith('>')) {
      const stripped = chunk.split('\n').map(line => line.replace(/^>\s*/, '')).join('\n').trim();
      const labelMatch = stripped.match(/^\*\*([^*]+)\*\*\s*\n?([\s\S]*)/);
      const label = labelMatch ? labelMatch[1].trim().toLowerCase() : '';
      const body = labelMatch ? labelMatch[2].trim() : stripped;

      if (/sharp\s+principle/.test(label) || (!labelMatch && /^principle/i.test(stripped))) {
        blocks.push({ type: 'sharp-principle', text: body || stripped });
      } else if (/observation/.test(label)) {
        blocks.push({ type: 'observation', text: body });
      } else if (/why\s+this\s+matters/.test(label)) {
        blocks.push({ type: 'why-matters', text: body });
      } else {
        // Unknown blockquote: render as Sharp Principle (safe default for italics).
        blocks.push({ type: 'sharp-principle', text: stripped });
      }
      continue;
    }
    // H2
    const h2Match = chunk.match(/^##\s+(.+)/);
    if (h2Match) {
      blocks.push({ type: 'h2', text: h2Match[1].trim() });
      continue;
    }
    // H3
    const h3Match = chunk.match(/^###\s+(.+)/);
    if (h3Match) {
      blocks.push({ type: 'h3', text: h3Match[1].trim() });
      continue;
    }
    // Default: body paragraph
    blocks.push({ type: 'body', text: chunk });
  }
  return blocks;
}

// Extract Why This Matters from a parsed block list (and remove it from the
// flow). Returns { blocks, whyMattersText }.
function extractWhyMatters(blocks) {
  const idx = blocks.findIndex(b => b.type === 'why-matters');
  if (idx < 0) return { blocks, whyMattersText: '' };
  const text = blocks[idx].text;
  const remaining = [...blocks.slice(0, idx), ...blocks.slice(idx + 1)];
  return { blocks: remaining, whyMattersText: text };
}

export default function SharpJournalArticle({
  insight,
  onBack,
  nextInsight,
  onSelectNext,
}) {
  const scrollRef = useRef(null);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    setScrollProgress(0);
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [insight?.id]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const scrollable = el.scrollHeight - el.clientHeight;
    if (scrollable <= 0) { setScrollProgress(0); return; }
    setScrollProgress(Math.min(1, el.scrollTop / scrollable));
  };

  if (!insight) return null;

  const allBlocks = parseContent(insight.content || '', insight.title || '');
  const { blocks, whyMattersText } = extractWhyMatters(allBlocks);
  const why = insight.why_this_matters || whyMattersText || insight.excerpt || '';

  const tagInfo = CATEGORY_TAG[insight.category] || { label: 'Sharp Journal', className: 'section' };
  const tagStyle = TAG_STYLE[tagInfo.className] || TAG_STYLE.section;
  const readMinutes = insight.reading_time_minutes || insight.read_time || 2;

  const dateStr = formatArticleDate(insight.publish_date || insight.created_at || insight.date);
  const showByline = insight.author !== false; // default to showing byline unless explicitly disabled
  const authorName = insight.author_name || 'Evan Cole';
  const authorTitle = insight.author_title || 'Head of Signal Intelligence';

  const contentType = insight.content_type || 'Sharp Journal';
  const version = insight.version || 'v1.0';

  // Track whether the next H2 needs a divider above it. The first H2 in the
  // article (lede paragraph(s) then first section) DOES need one to match the
  // reference render; subsequent ones too. We render the divider before EVERY
  // H2 unconditionally, matching the spec.
  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      style={{
        position: 'fixed', inset: 0,
        background: 'var(--sp-bg)',
        zIndex: 200,
        overflowY: 'auto',
        WebkitOverflowScrolling: 'touch',
        // env(safe-area-inset-top) pushes the nav bar (and the sticky
        // reading progress bar) below the iOS notch / Dynamic Island
        // so the back arrow is reachable. 0px fallback keeps web and
        // Android pixel-identical.
        paddingTop: 'env(safe-area-inset-top, 0px)',
      }}
    >
      {/* Reading progress bar (sticky, 2px) */}
      <div style={{
        position: 'sticky', top: 0,
        width: '100%', height: '2px',
        background: 'var(--sp-surface-2)',
        zIndex: 50,
      }}>
        <div style={{
          height: '100%',
          width: `${scrollProgress * 100}%`,
          background: 'var(--sp-green)',
          transition: 'width 0.1s linear',
        }} />
      </div>

      <div style={{ maxWidth: '480px', margin: '0 auto' }}>
        {/* Nav bar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '14px 18px 16px',
          borderBottom: '1px solid var(--sp-border)',
        }}>
          <button
            onClick={onBack}
            aria-label="Back"
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: '32px', height: '32px', marginLeft: '-8px',
              background: 'none', border: 'none',
              color: 'var(--sp-text-2)', cursor: 'pointer',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '12px', fontWeight: 500,
            letterSpacing: '0.24em', textTransform: 'uppercase',
            color: 'var(--sp-text)',
          }}>Sharp Journal</span>
        </div>

        <article style={{ padding: '28px 22px 100px' }}>
          {/* Meta line */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            flexWrap: 'wrap', marginBottom: '18px',
          }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center',
              padding: '4px 10px', borderRadius: '4px',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '9px', fontWeight: 500,
              letterSpacing: '0.22em', textTransform: 'uppercase',
              ...tagStyle,
            }}>{tagInfo.label}</span>
            <span style={{ color: 'var(--sp-text-5)' }}>·</span>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px', color: 'var(--sp-text-3)',
              letterSpacing: '0.04em',
            }}>Sharp Journal</span>
            <span style={{ color: 'var(--sp-text-5)' }}>·</span>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px', color: 'var(--sp-text-3)',
              letterSpacing: '0.04em',
            }}>{readMinutes} min read</span>
          </div>

          {/* H1 */}
          <h1 style={{
            fontFamily: "'IBM Plex Serif', Georgia, serif",
            fontSize: '30px', fontWeight: 700,
            lineHeight: 1.18, letterSpacing: '-0.012em',
            color: 'var(--sp-text)', marginBottom: '12px',
          }}>{insight.title}</h1>

          {/* Date */}
          {dateStr && (
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px', color: 'var(--sp-text-3)',
              letterSpacing: '0.06em',
              marginBottom: showByline ? '8px' : '28px',
            }}>{dateStr}</div>
          )}

          {/* Byline */}
          {showByline && (
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px', color: 'var(--sp-text-3)',
              letterSpacing: '0.04em',
              marginBottom: '28px',
            }}>
              By <span style={{ color: 'var(--sp-text-2)', fontWeight: 500 }}>{authorName}</span> &middot; {authorTitle}
            </div>
          )}

          {/* Body blocks */}
          {blocks.map((block, idx) => {
            const key = `b-${idx}`;
            if (block.type === 'h2') {
              return (
                <div key={key}>
                  <SectionDivider />
                  <ArticleH2>{renderInline(block.text, `h2-${idx}`)}</ArticleH2>
                </div>
              );
            }
            if (block.type === 'h3') {
              return <ArticleH3 key={key}>{renderInline(block.text, `h3-${idx}`)}</ArticleH3>;
            }
            if (block.type === 'sharp-principle') {
              return <SharpPrinciple key={key} text={block.text} />;
            }
            if (block.type === 'observation') {
              return <Observation key={key} text={block.text} />;
            }
            if (block.type === 'pull-quote') {
              return <PullQuote key={key} text={block.text} />;
            }
            // body paragraph
            return <ArticleBody key={key}>{renderInline(block.text, `p-${idx}`)}</ArticleBody>;
          })}

          {/* Why This Matters (required terminal block) */}
          <WhyMatters text={why} />

          {/* Cross-edition link */}
          {nextInsight && (
            <CrossLink
              title={nextInsight.title}
              onClick={() => onSelectNext && onSelectNext(nextInsight)}
            />
          )}

          {/* Article footer */}
          <ArticleFooter
            updatedDate={dateStr}
            contentType={contentType}
            version={version}
          />
        </article>
      </div>
    </div>
  );
}
