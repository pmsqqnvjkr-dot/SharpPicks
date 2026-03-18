# Multi-Sport Unified Feed — Architecture & UI Spec

## Reference
See `multi-sport-feed.html` for the pixel-reference mockup. Two frames: "All Sports" (peak overlap, July) and "MLB Only" (single-sport filtered view).

---

## Core Concept

All sports live in a single unified feed on the Market tab. Sport filter pills at the top let users toggle between "All", "NBA", "MLB", and "WNBA". Selecting a sport filters the Discipline Filter stats, Signals summary, and game list. Selecting "All" shows everything, grouped by sport with section headers.

---

## Sport Identity System

Each sport gets a unique accent color. These are used for sport pills, badges, group headers, and the discipline scope indicator.

```
NBA:
  --nba-color:  #F97316  (orange)
  --nba-dim:    rgba(249,115,22, 0.12)

MLB:
  --mlb-color:  #3B82F6  (blue)
  --mlb-dim:    rgba(59,130,246, 0.12)

WNBA:
  --wnba-color: #EC4899  (pink)
  --wnba-dim:   rgba(236,72,153, 0.12)
```

These colors are only used for sport identification elements — not for edge/signal coloring, which stays green/red per the existing brand.

---

## Component Changes

### 1. Sport Filter Row (NEW)

**Position:** Below the page header, above the Discipline Filter.

**Layout:** Horizontal scrollable row of pills. Left-aligned, 6px gap.

**Each pill contains:**
- Sport color dot: 6px circle in the sport's accent color. When active: add `box-shadow: 0 0 6px` in the sport color at 0.4 opacity. When inactive: 0.4 opacity on the dot.
- Sport name: IBM Plex Mono 11px, weight 500.
- Game count: IBM Plex Mono 9px, weight 400, `--text-muted`. Shows number of games for that sport today.

**"All" pill:**
- No color dot.
- Shows total game count across all active sports.
- Active state: white text, `--bg-elevated` bg, `rgba(255,255,255, 0.1)` border.

**Active sport pill:**
- Text color: the sport's accent color.
- Background: the sport's dim color.
- Border: sport color at 0.3 opacity.

**Inactive sport pill:**
- Text: `--text-secondary`.
- Border: `--border`.
- Dot opacity: 0.4.

**Off-season sport pill:**
- Entire pill at `opacity: 0.35`.
- Game count replaced with "OFF" text.
- Not tappable (disabled).

**Behavior:**
- Only one pill active at a time (radio behavior).
- Selecting a sport pill filters ALL downstream components: Discipline Filter, Signals summary, and game list.
- Selecting "All" shows the combined view.
- Off-season sports are dimmed and disabled. Determine off-season status from the backend (`model_active` flag per sport).

**Data source:** The pill row needs a list of active sports with game counts. Add an endpoint or extend the existing Market Intelligence endpoint to return:
```json
{
  "sports": [
    { "key": "nba", "label": "NBA", "games": 0, "active": false },
    { "key": "mlb", "label": "MLB", "games": 15, "active": true },
    { "key": "wnba", "label": "WNBA", "games": 6, "active": true }
  ]
}
```

---

### 2. Discipline Filter — Scope-Aware

**Change:** The Discipline Filter now reflects the currently selected sport filter.

**When "All" is selected:**
- Top-right shows a scope badge: "ALL SPORTS" in `--text-muted` on `--bg-elevated` bg.
- Stats (Analyzed / Signals / Passed) are totals across all active sports.
- Below the main stats, show a per-sport breakdown row:
  - Each row: sport color dot (5px) + "MLB: 15 games, **3 signals**" (signals count in `--brand-green`, bold).
  - One row per active sport.

**When a single sport is selected:**
- Scope badge shows the sport name in its accent color on its dim bg (e.g., "MLB" in `#3B82F6` on `rgba(59,130,246, 0.12)`).
- Stats reflect only that sport's numbers.
- No per-sport breakdown needed (redundant).

**Everything else stays the same:** "NO EDGE. NO PICK." tagline, "View Passed" button, layout.

---

### 3. Signals Summary — Sport-Aware

**When "All" is selected:**
- Header: "TODAY'S SIGNALS".
- Each signal card includes a sport badge on the left: the sport's 3-4 letter abbreviation in its accent color on its dim bg. IBM Plex Mono 8px, weight 500, uppercase, padding 2px 6px, border-radius 3px.
- Cards sorted by edge descending across all sports.

**When a single sport is selected:**
- Header: "{SPORT} SIGNALS" (e.g., "MLB SIGNALS").
- No sport badge needed on individual cards (redundant).
- Only shows signals for that sport.

---

### 4. Game List — Sport Grouping & Badges

**When "All" is selected:**
- Games are grouped by sport.
- Each group has a **Sport Group Header:**
  - Layout: sport dot (6px) + sport name (IBM Plex Mono 10px, weight 500, letter-spacing 2px, uppercase, `--text-muted`) + horizontal line (flex: 1, 1px `--border`) + game count ("15 games · 3 signals" in IBM Plex Mono 10px, `--text-muted`, signals count in `--brand-green`).
- Each game card has a **sport badge** in the top-right corner (position: absolute, top: 14px, right: 16px). Style: same as signal card badge — sport abbreviation in accent color on dim bg.
- Groups ordered by: most signals first, then alphabetical.

**When a single sport is selected:**
- No sport group headers (only one sport).
- No sport badge on cards (redundant — the user already filtered).
- Straight list sorted by the current sort option (Time / Edge).

**MLB-specific card data:**
- Replace "Spread" label with "Run Line".
- Add a **pitcher line** between the team names and the data strip:
  - Layout: "SP" label (IBM Plex Mono 8px, uppercase, `--text-muted`) + pitcher last name (Inter 11px, `--text-secondary`) + ERA (IBM Plex Mono 10px, `--text-muted`) + "vs" + opposing pitcher.
  - Only show for upcoming games (not final).

**WNBA card data:**
- Same structure as NBA cards (Spread / Total / ML / Edge). No sport-specific differences.

---

### 5. Page Header Meta — Multi-Sport Aware

**Change:** The meta line below "Market Intelligence" adapts to selected filter.

- **All:** "2026-07-15 · 21 games · **3 models active**" — pluralize "models" when multiple sports are active.
- **Single sport:** "2026-07-15 · 15 games · **Model active**" — singular.

---

### 6. Daily Market Brief — Multi-Sport

The existing Daily Market Brief card needs to work across sports.

**When "All" is selected:**
- NEI, Regime, and Top Edge should reflect the aggregate or show per-sport if they differ significantly.
- The Model Favoring bar should show combined favorite/underdog bias across all sports.
- The Market Signal text should reference the most notable cross-sport observation.

**When a single sport is selected:**
- All brief data scoped to that sport only.

**Implementation note:** This may require the brief generation logic to produce per-sport briefs that can be aggregated. For MVP, it's fine to hide the Daily Market Brief when "All" is selected and only show it on single-sport views. Revisit aggregation later.

---

## Seasonal Behavior

The sport filter row handles seasonality automatically:

| Period | NBA | MLB | WNBA | Default View |
|--------|-----|-----|------|-------------|
| Oct–Apr | Active | OFF | OFF | NBA (only active) |
| Apr–May | Active | Active | OFF | All (NBA + MLB) |
| May–Jun | Active (playoffs) | Active | Active | All |
| Jul–Sep | OFF | Active | Active | All (MLB + WNBA) |
| Oct | Active (new season) | Active (playoffs) | OFF | All |

**Rules:**
- If only 1 sport is active, auto-select that sport (skip "All" view since it's identical).
- If 2+ sports are active, default to "All".
- Off-season pills are always visible but dimmed and disabled. This teases upcoming sports.
- When a sport transitions from off-season to active (e.g., WNBA shadow → live in May), update the pill state without requiring a page reload — the backend `active` flag drives it.

---

## Sort Options Adaptation

**NBA/WNBA:** Time | Spread | Total | Edge (current set)
**MLB:** Time | Run Line | Total | Edge (rename Spread → Run Line)
**All:** Time | Edge only (simplify when mixing sports with different primary bet types)

---

## Backend Requirements

Minimal backend changes needed:

1. **Sport metadata endpoint** (or extend existing): Return list of sports with active status and game counts.
2. **Game data:** Already has sport identifiers. Ensure the Market Intelligence API supports a `sport` query param to filter results.
3. **Discipline Filter stats:** Support filtering by sport. Either compute on the frontend from the full game list, or accept a `sport` param on the stats endpoint.
4. **MLB game data:** Ensure starting pitcher info (name, ERA) is available in the game payload. This likely comes from the Odds API or ESPN enrichment.
5. **WNBA:** The shadow mode endpoints (`wnba-collect`, `wnba-closing-lines`, `wnba-shadow`, `wnba-grade`) are already built. When WNBA goes live, the same game data structure as NBA should work with no UI changes beyond the sport badge.

---

## Implementation Priority

| Phase | What | Notes |
|-------|------|-------|
| 1 | Sport filter row + filtering logic | Frontend only, filter existing data |
| 2 | Sport badges on game cards | CSS + conditional render |
| 3 | Discipline Filter scoping | Frontend filtering of existing stats |
| 4 | Sport group headers (All view) | Template change |
| 5 | MLB card adaptations (Run Line, pitchers) | Template + data mapping |
| 6 | Signals summary sport badges | CSS + conditional render |
| 7 | Seasonal pill states | Backend `active` flag |
| 8 | Daily Market Brief scoping | Backend brief generation per sport |

Phases 1-6 are frontend only. Phase 7 needs a small backend flag. Phase 8 is the largest backend lift and can be deferred.
