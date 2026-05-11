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
//   2. Otherwise the most recent article tagged for the current sport.
//   3. Otherwise a universal article rotated by a stable sport offset
//      (NBA=0, MLB=1, WNBA=2) so each tab lands on a different one
//      instead of all surfacing the same fallback.
//   4. Final fallback: the first evergreen article in the list.
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
  const sportMatch = evergreen.find(
    (a) => (a.sport || '').toLowerCase() === sportLower
  );
  if (sportMatch) return sportMatch;

  const universals = evergreen.filter(isUniversalSport);
  if (universals.length) {
    return universals[sportOffset(sport) % universals.length];
  }
  return evergreen[0];
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
