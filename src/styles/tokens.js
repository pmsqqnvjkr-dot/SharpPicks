// SharpPicks design tokens. Source of truth is static/css/tokens.css
// (v4.3, May 2026). The exports here are JS mirrors for inline-style
// components that can't read CSS custom properties at render time.
//
// Canonical palette (use these when writing new components):
//
//   green     #5A9E72   sage; positive/edge/verified result
//   blue      #4F86F7   signal blue; active signal/info
//   blueHover #3D72E0   signal blue hover/deep variant
//   amber     #C9A35C   institutional warning/calibration (muted brass; was #F59E0B pre-v4.3.1)
//   steel     #8FA3C2   off-season / long-horizon empty state
//   negative  #C4868A   muted rose; loss/negative (NEVER fire-truck red)
//
//   bg        #0A0D14   page root
//   surface   #121725   card surface
//   surface2  #1B2030   elevated surface, bar tracks
//
//   text      #E8EAED   primary
//   text-2/3/4/5 = rgba(232, 234, 237, X) at 0.7/0.5/0.35/0.25

export const colors = {
  bg: '#0A0D14',
  surface0: '#0D1017',          // deeper-than-bg variant; under-card, modal backdrop
  surface1: '#121725',
  surface2: '#1B2030',          // canonical surface-2 (was #161C2E pre-v4.3)
  signalBlue: '#4F86F7',
  anchorBlue: '#3D72E0',        // canonical hover/deep variant (was #2F5FD6)
  edgeGreen: '#5A9E72',
  deepGreen: '#5A9E72',
  alertRed: '#C4868A',
  premiumGold: '#C9A35C',       // amber; retoned from #F59E0B in v4.3.1
  premiumGoldSoft: 'rgba(201, 163, 92, 0.12)',
  premiumGoldBorder: 'rgba(201, 163, 92, 0.40)',
  steel: '#8FA3C2',             // off-season state
  steelSoft: 'rgba(143, 163, 194, 0.12)',
  steelBorder: 'rgba(143, 163, 194, 0.38)',
  text: '#E8EAED',              // canonical (was #EEF2FF)
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  stroke: 'rgba(255, 255, 255, 0.08)',
  strokeStrong: 'rgba(255, 255, 255, 0.12)',
};

export const fonts = {
  sans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  serif: "'IBM Plex Serif', Georgia, serif",
  mono: "'JetBrains Mono', 'SF Mono', monospace",
  label: "'Courier New', monospace",
};

export const radii = { sm: 6, md: 8, lg: 12 };

// DEPRECATED: the `inst` (institutional) palette below is a v4.0 leftover
// consumed by ~78 sites across signals/shared/ (HeroCard, MIPill,
// SharpPrinciple, CapitalCard, CountdownCard, FurtherReadingCard). Values
// were retoned to v4.3 canonical in the May 2026 brand sweep so existing
// consumers render correctly without code changes. Do NOT add new consumers;
// use the `colors` export above (or static/css/tokens.css var(--sp-*))
// directly. Plan is to inline these into the consuming components and drop
// the export entirely once those screens get their next visual revision.
export const inst = {
  bgPage: '#0A0D14',            // was #0A0E1A
  bgCard: '#121725',            // was #111726
  bgCardElev: '#1B2030',        // was #161D2E
  borderSubtle: 'rgba(255, 255, 255, 0.08)',   // was #1F2940
  borderMedium: 'rgba(255, 255, 255, 0.15)',   // was #2B3A5C

  edge: '#5A9E72',              // was #4ADE80 (mint, off-brand)
  edgeDim: '#5A9E72',           // was #2F9E5F; collapses to canonical sage
  edgeBg: 'rgba(90, 158, 114, 0.06)',          // was rgba(74,222,128,...)
  edgeBorder: 'rgba(90, 158, 114, 0.22)',      // was rgba(74,222,128,...)

  system: '#4F86F7',            // was #6B8AC4 (slate-blue, off-brand)
  systemDim: '#3D72E0',         // was #4A6691; canonical hover/deep
  systemBg: 'rgba(79, 134, 247, 0.08)',        // was rgba(107,138,196,...)
  systemBorder: 'rgba(79, 134, 247, 0.28)',    // was rgba(107,138,196,...)

  textPrimary: '#E8EAED',                       // was #E8ECF4
  textSecondary: 'rgba(232, 234, 237, 0.7)',   // was #9BA8C2
  textTertiary: 'rgba(232, 234, 237, 0.5)',    // was #5A6886
  textMuted: 'rgba(232, 234, 237, 0.35)',      // was #3E4A66
};

export const instFonts = {
  serif: "'Fraunces', Georgia, serif",
  sans: "'Inter', system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
};
