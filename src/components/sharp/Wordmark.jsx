export default function Wordmark({ size = 16, opacity = 1, style = {} }) {
  const barH = size * 1.25;
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
          gap: size * 0.12,
          flexShrink: 0,
        }}
      >
        <span style={{ display: 'inline-block', width: 1.5, height: barH, backgroundColor: 'currentColor', borderRadius: 0.5 }} />
        <span style={{ display: 'inline-block', width: 1.5, height: barH, backgroundColor: 'currentColor', borderRadius: 0.5 }} />
      </span>
      PICKS
    </span>
  );
}
