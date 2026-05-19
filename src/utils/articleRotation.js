// Per-sport Sharp Journal article rotation.
//
// Every surface that shows a journal article on the picks home (off-day,
// pass day, pre-model "while you wait", night-mode "today's read",
// post-slate "recommended reads") flows through these helpers so the
// rules stay consistent when a user flips between NBA / MLB / WNBA tabs:
//
//   1. If a non-market-note article was published today (ET) and is
//      universal (sport tag empty, null, or 'all'), it wins on every
//      tab. Same hero card across sports, by design, so a fresh
//      broadly-applicable piece gets max distribution on launch day.
//   2. Otherwise rotate through sport-tagged + universal articles using
//      (day_of_year + sportOffset) % pool.length so consecutive
//      no-signal days surface different pieces instead of repeating the
//      same hero card.
//   3. Final fallback: the first evergreen article in the list.
//
// "Universal" = the article applies to all sports (philosophy, how-it-
// works, broad discipline pieces). We mark these by leaving the sport
// field empty in the journal frontmatter rather than adding a separate
// audience field.

const SPORT_OFFSETS = { nba: 0, mlb: 1, wnba: 2 };

function etDateString(d = new Date()) {
  try {
    return d.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  } catch {
    return '';
  }
}

function sportOffset(sport) {
  return SPORT_OFFSETS[(sport || 'nba').toLowerCase()] ?? 0;
}

// Day-of-year in ET as a stable rotation key. Same value all day across
// any user; ticks over at midnight ET so the off-day hero changes each
// calendar day.
function dayOfYearET(d = new Date()) {
  const iso = etDateString(d);
  if (!iso) return 0;
  const [y, m, day] = iso.split('-').map(Number);
  const start = Date.UTC(y, 0, 0);
  const date = Date.UTC(y, (m || 1) - 1, day || 1);
  return Math.floor((date - start) / 86400000);
}

function isMarketNote(a) {
  if (!a) return true;
  if (a.category === 'market_notes') return true;
  if (/^market-note-(\w+-)?[0-9]{4}/.test(a.slug || '')) return true;
  return false;
}

function isUniversalSport(a) {
  const s = (a?.sport || '').toLowerCase();
  return !s || s === 'all' || s === 'any';
}

function articlePublishDate(a) {
  return a?.publish_date || a?.published_at?.slice?.(0, 10) || a?.date || '';
}

export function pickPrimaryArticle(articles, sport) {
  if (!Array.isArray(articles) || !articles.length) return null;
  const evergreen = articles.filter((a) => a && !isMarketNote(a));
  if (!evergreen.length) return null;

  const today = etDateString();
  if (today) {
    const universalToday = evergreen.find(
      (a) => isUniversalSport(a) && articlePublishDate(a) === today
    );
    if (universalToday) return universalToday;
  }

  const sportLower = (sport || '').toLowerCase();
  const dayIdx = dayOfYearET();
  const offset = (dayIdx + sportOffset(sport)) % Math.max(evergreen.length, 1);

  // Rotation pool: sport-tagged articles for this sport first, then
  // universal articles, deduped. This way the day-of-year rotation
  // surfaces different content on consecutive no-signal days while a
  // fresh article published today still wins via the priority above.
  const pool = [];
  const seen = new Set();
  evergreen.forEach((a) => {
    if ((a.sport || '').toLowerCase() === sportLower && !seen.has(a)) {
      pool.push(a);
      seen.add(a);
    }
  });
  evergreen.forEach((a) => {
    if (isUniversalSport(a) && !seen.has(a)) {
      pool.push(a);
      seen.add(a);
    }
  });

  if (pool.length) return pool[offset % pool.length];
  return evergreen[offset % evergreen.length];
}

// Returns evergreen articles ordered for the current sport tab. Primary
// is index 0 (per pickPrimaryArticle), then the remaining sport-matched
// articles, then universals, then anything else. Callers typically slice
// the first N for stacked lists.
export function pickArticlesForSport(articles, sport) {
  if (!Array.isArray(articles) || !articles.length) return [];
  const evergreen = articles.filter((a) => a && !isMarketNote(a));
  if (!evergreen.length) return [];

  const out = [];
  const seen = new Set();

  const primary = pickPrimaryArticle(articles, sport);
  if (primary) {
    out.push(primary);
    seen.add(primary);
  }

  const sportLower = (sport || '').toLowerCase();
  evergreen.forEach((a) => {
    if (!seen.has(a) && (a.sport || '').toLowerCase() === sportLower) {
      out.push(a);
      seen.add(a);
    }
  });

  evergreen.forEach((a) => {
    if (!seen.has(a) && isUniversalSport(a)) {
      out.push(a);
      seen.add(a);
    }
  });

  evergreen.forEach((a) => {
    if (!seen.has(a)) {
      out.push(a);
      seen.add(a);
    }
  });

  return out;
}
