export default function Wordmark({ size = 16, opacity = 1, style = {} }) {
  const barH = size * 1.25;
  const barW = 2;
  const barGap = size * 0.12;
  const underlineW = barW * 2 + barGap;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: size * 0.45,
        fontFamily: 'var(--font-mono)',
        fontSize: size,
        fontWeight: 500,
        letterSpacing: '0.2em',
        color: '#fff',
        opacity,
        lineHeight: 1,
        whiteSpace: 'nowrap',
        userSelect: 'none',
        ...style,
      }}
    >
      SHARP
      <span
        style={{
          display: 'inline-flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: size * 0.15,
          flexShrink: 0,
        }}
      >
        <span style={{ display: 'inline-flex', gap: barGap }}>
          <span style={{ display: 'inline-block', width: barW, height: barH, backgroundColor: 'currentColor', borderRadius: 0.5 }} />
          <span style={{ display: 'inline-block', width: barW, height: barH, backgroundColor: 'currentColor', borderRadius: 0.5 }} />
        </span>
        <span style={{ display: 'inline-block', width: underlineW, height: 1.5, backgroundColor: 'var(--color-signal, #5A9E72)', borderRadius: 1 }} />
      </span>
      PICKS
    </span>
  );
}
