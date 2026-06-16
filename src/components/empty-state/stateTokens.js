// Per-screen state color tokens for the empty-state component family
// (Timeline, StatePill, NarrativeCard). Mirrors the v4.3.1 CSS tokens in
// static/css/tokens.css for components that read from JS at render time.
//
// state name -> {color, soft, border}:
//   steel  off-season / long-horizon empty state (NBA off-season screen)
//   amber  calibration / live / pre-launch (NFL calibration screen,
//          existing CalibrationBanner on MLB/WNBA)
//   green  default / verified result accent (used as the green-highlighted
//          "final node" treatment on timelines, e.g. NBA opening night)
//
// Always read state via getStateTokens(state) below. Never inline these
// hex values in consuming components; if a new state color is added,
// extend STATE_TOKENS here and the CSS file in lockstep.

export const STATE_TOKENS = {
  steel: {
    color: '#8FA3C2',
    soft: 'rgba(143, 163, 194, 0.12)',
    border: 'rgba(143, 163, 194, 0.38)',
  },
  amber: {
    color: '#C9A35C',
    soft: 'rgba(201, 163, 92, 0.12)',
    border: 'rgba(201, 163, 92, 0.40)',
  },
  green: {
    color: '#5A9E72',
    soft: 'rgba(90, 158, 114, 0.14)',
    border: 'rgba(90, 158, 114, 0.45)',
  },
};

export function getStateTokens(state) {
  return STATE_TOKENS[state] || STATE_TOKENS.steel;
}

// Shared neutral tokens these components reuse. Mirror of static/css/tokens.css
// canonical values, NOT the looser mockup contrast scale.
export const NEUTRAL_TOKENS = {
  bg: '#0A0D14',
  card: '#0E1320',
  hairline: 'rgba(255, 255, 255, 0.08)',
  hairlineStrong: 'rgba(255, 255, 255, 0.15)',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
};
