# Claude Code Handoff: NBA Off-Season + NFL Calibration Screens

Paste everything below this line into Claude Code from `~/Projects/SharpPicks`. Drop the combined mockup `empty-state-screens-nba-nfl.html` into `docs/mockups/` first.

---

We are adding two screens to the app in one pass: a fourth empty state (NBA OFF-SEASON) and an NFL chip in a pre-launch CALIBRATION state. The visual spec for both is the single mockup at `docs/mockups/empty-state-screens-nba-nfl.html`. Open it in a browser: left frame is NBA off-season, right frame is NFL calibration. Treat it as the source of truth for layout, spacing, type, and copy. Match it closely; do not redesign. The mockup's stylesheet already demonstrates the intended component architecture: shared components with a per-screen state color variable. Build it that way.

## Context you need before writing code

The app has a three-way empty state taxonomy that must never be conflated:

- PASS DAY: games exist, no edge cleared threshold. "Capital preserved."
- OFF DAY: league not playing today. "No slate, no signal."
- CALIBRATION: model not ready. Amber CAL pill.

This work adds OFF-SEASON as a fourth state (a long-horizon sibling of OFF DAY, steel-colored) and applies the existing CALIBRATION state at the sport level for NFL pre-launch (amber). OFF-SEASON is not OFF DAY and must not reuse its copy or pill. NFL pre-launch is not a new state and must not invent vocabulary like "coming soon" or "beta."

## Discovery step, report everything before changing anything

1. Locate the existing empty state components for all three current states, and the logic that selects between them. Report file paths, component names, and how the state is decided.
2. Locate the existing amber CAL pill and report the exact amber hex currently shipping. The mockup uses `#C9A35C` (dim `rgba(201,163,92,0.12)`, border `rgba(201,163,92,0.40)`). If a different amber already exists, flag the conflict and stop for a decision. We will not ship two ambers.
3. Locate the sport chip row component and how the sport list is defined (hardcoded array vs config).
4. Check whether NFL data reaches any client-facing endpoint today. NFL picks exist in Postgres tagged `sport='nfl'`, `model_era='nfl_v2_2026'`; confirm no public endpoint currently leaks them. If one does, flag it immediately.

Then present an implementation plan and wait for approval.

## State selection

Selection order when rendering a sport's main screen: CALIBRATION beats everything (and for NFL, applies unconditionally while the launch flag is off), then OFF-SEASON (today outside the sport's season window), then OFF DAY (in season, no slate), then PASS DAY (slate exists, no signals cleared). Confirm this matches or cleanly extends the existing selector.

## Configuration, not hardcoding

All dates and statuses on both screens are server-driven. Nothing on these screens may require a binary resubmission to update.

- Per-sport season window config: season start/end dates per league. Drives the OFF-SEASON trigger, the off-season countdown, and opening night.
- NBA road-back dates (draft, free agency, summer league, camps, preseason, opening night) in config. Mockup dates are approximate; mark them TODO and I will supply verified league dates.
- `nfl_launch` config block: kickoff datetime, launch flag (off), an ordered list of gates (id, title, note, status in {cleared, in_progress, pending}), and Road to Week One dates (camps open, preseason window, cut-down day; also TODO pending verified dates).
- While the launch flag is off, the NFL chip always resolves to the calibration screen regardless of slate, season window, or anything else. When it flips on, NFL enters the normal four-state selector like every other sport.
- Use an existing server-driven config/feature-flag path if the app already has one; otherwise a versioned config the backend serves. Report which.

## Shared components and tokens

Brand spec is v4.3, existing tokens unchanged: bg `#0A0D14`, Edge Green sage `#5A9E72` (never mint `#34D399`), rose `#C4868A`, IBM Plex Sans/Mono/Serif, hairline-grid stat cards.

One new token: `--steel: #8FA3C2` (dim `rgba(143,163,194,0.12)`, border `rgba(143,163,194,0.38)`). This is the OFF-SEASON state color. Add it wherever tokens live; never inline the hex in components.

Build these as shared components parameterized by a state color, exactly as the mockup's CSS does with its `--state` variable:

- **Timeline** (used by both screens): hairline rail, mono date in the state color, title with small label pill, one-line note, optional green-highlighted final node. Accent color is a prop: steel on off-season, amber on calibration.
- **State pill**: mono pill in the state color (`NBA OFF-SEASON` steel, `NFL CALIBRATION` amber).
- **Narrative card**: section label, optional state-colored pill, serif title, muted body. Used for "The off-season retrain is underway." (steel pill, IN THE LAB) and "Why the wait." (no pill).
- **Chip state dot**: NBA chip shows the steel dot while in off-season; NFL chip shows the amber dot while in calibration; in-season sports keep live green dots.

## Screen 1: NBA off-season (left frame)

Sections top to bottom, matching the mockup:

1. Date row with steel `NBA OFF-SEASON` pill.
2. Hero: serif "Season closed." plus body copy exactly as written. The line "This isn't a pass day. It's the calendar." is load-bearing taxonomy copy; keep it verbatim.
3. Countdown card in days with opening-night sub-line, driven by season window config.
4. Season ledger card: three-stat hairline grid leading with CLV BEAT %, then NET units, then RECORD, a strip line (signals issued, pass days, selectivity), and the footer tagline "EVERY SIGNAL TRACKED. NOTHING REMOVED." All numbers in the mockup are placeholders. Wire to real season-aggregate data; if no season-summary endpoint exists, propose the cheapest query/endpoint shape and wait for approval before building it.
5. The Road Back: six timeline entries from config. Summer League keeps its "NO SIGNAL" pill and note. Opening night is the only green node.
6. The Market Doesn't Close: live rows for in-season sports with game counts and a VIEW SLATE button that switches the active sport chip. Only render sports currently in season.
7. Model status narrative card: steel IN THE LAB pill. No CAL pill, no amber, no progress indicators anywhere on this screen.
8. Off-season reading: existing Journal card component, category SEASON REVIEW, content from the existing journal feed.
9. Sharp Principle: "The work between games is the work."
10. Existing disclaimer and tab bar unchanged.

## Screen 2: NFL calibration (right frame)

1. NFL chip added to the chip row: amber dot at rest, amber border and dim fill when selected.
2. Date row with amber `NFL CALIBRATION` pill.
3. Hero: serif "Built. Not shipped." plus body copy exactly as written.
4. Countdown card: kickoff in days with week 1 sub-line, from `nfl_launch` config.
5. The Gate Ledger: hairline-divided rows from config order, three mark styles (green check ring cleared, amber dot ring in progress, empty faint ring pending) with matching mono status tags, and the footer line "SIGNALS SHIP ONLY AFTER EVERY GATE CLEARS".
6. Road to Week One: three timeline entries from config (camps, preseason with NO SIGNAL pill, final cuts with PRIORS LOCK pill). No green final node on this one.
7. "Why the wait." narrative card.
8. Notify me card. The one interactive element:
   - Tapping requests push permission if not granted, then sets an `nfl_launch_notify` flag on the user. Button flips to a quiet confirmed state (mono, muted, no celebration) and renders confirmed on revisit.
   - The copy promises exactly one notification. Backend is a one-shot send keyed off the launch flag flip; propose the cheapest endpoint and flag shape (likely a boolean on the user row plus one endpoint) and wait for approval before building.
   - The tap lands in `user_events` with `surface` set appropriately, consistent with existing tracker paths.
9. Journal card, category MODEL NOTES (amber).
10. Sharp Principle: "No edge, no pick." Then disclaimer and tab bar unchanged.

## Hard content rules

- No model performance numbers anywhere on the NFL screen. No hit rates, no win percentages, no edge band percentages, no backtest stats beyond the qualitative copy in the mockup ("seven seasons," "every game graded"). If any data wiring would surface a number, stub it and flag it.
- The amber CAL treatment appears on the NFL screen only. It must not appear on the off-season screen. The steel token must not appear on the NFL screen.
- Copy rules, zero exceptions: no em-dashes, no exclamation marks, no emoji, no caps for emphasis outside mono label styling, no gambling slang, no hype words. Bloomberg analyst, not ESPN. Copy in the mockup is final; if anything must change for technical reasons, flag it rather than rewording it yourself.

## Process

- Manual diff approval on every meaningful change. Discovery report, then plan, then small reviewed chunks.
- No emoji or em-dashes in code comments.
- Do not modify PASS DAY, OFF DAY, or CALIBRATION component behavior for existing sports beyond what the state selector extension and shared chip row strictly require.

## Acceptance checklist

State logic:
- System date inside the NBA season window with no slate: OFF DAY renders, unchanged.
- System date after the NBA season end date: OFF-SEASON renders with steel pill and days countdown.
- CALIBRATION still wins over everything when a model is not ready.
- NFL launch flag off: NFL chip always resolves to the calibration screen; no NFL picks reachable from any client surface. Flag on: NFL enters the normal four-state selector (verify with a stubbed slate).

Config:
- Gate statuses, all countdowns, and all timeline dates come from config; changing config changes both screens with no client rebuild.

Components and visuals:
- Timeline is one shared implementation used by both screens, accent color via prop.
- NBA chip steel dot in off-season; NFL chip amber dot in calibration; MLB and WNBA rows appear under The Market Doesn't Close only while in season, with working sport switch.
- No amber on the off-season screen; no steel on the NFL screen.
- No numeric performance claims render anywhere on the NFL screen.

Data and tracking:
- Season ledger renders real aggregates or a clearly marked loading/empty fallback, never the mockup placeholders.
- Notify me requests permission, sets the flag, fires the tracking event, and renders the confirmed state on revisit.

Devices:
- Both screens verified on iOS simulator and Android at 390px and 430px widths; chip row wraps cleanly with four chips at 390px; `contentInset` behavior consistent with the rest of the app.
