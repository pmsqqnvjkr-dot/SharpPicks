export default function Wordmark({ size = 16, opacity = 1, style = {} }) {
  const barH = size * 1.15;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: size * 0.2,
        fontFamily: 'var(--font-mono)',
        fontSize: size,
        fontWeight: 700,
        letterSpacing: '0.12em',
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
          gap: 2,
          flexShrink: 0,
        }}
      >
        <span style={{ display: 'inline-block', width: 1.5, height: barH, backgroundColor: 'currentColor', borderRadius: 1 }} />
        <span style={{ display: 'inline-block', width: 1.5, height: barH, backgroundColor: 'currentColor', borderRadius: 1 }} />
      </span>
      PICKS
    </span>
  );
}
