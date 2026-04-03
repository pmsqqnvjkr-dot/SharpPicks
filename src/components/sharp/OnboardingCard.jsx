import { useOnboardingCard } from '../../hooks/useOnboardingCard';

export default function OnboardingCard({ cardId, title, children }) {
  const { visible, dismiss } = useOnboardingCard(cardId);
  if (!visible) return null;

  return (
    <div style={{
      background: '#111e33',
      border: '0.5px solid #1e3050',
      borderLeft: '3px solid #5A9E72',
      borderRadius: '8px',
      padding: '11px 13px',
      marginBottom: '8px',
      position: 'relative',
    }}>
      <button
        onClick={dismiss}
        aria-label="Dismiss"
        style={{
          position: 'absolute', top: '8px', right: '10px',
          background: 'none', border: 'none', padding: 0,
          fontSize: '15px', color: '#4a5a6e', cursor: 'pointer',
          lineHeight: 1,
        }}
      >&times;</button>
      <div style={{
        fontFamily: "'JetBrains Mono','SF Mono','Menlo','Consolas','Courier New',monospace",
        fontSize: '8px', letterSpacing: '2px', color: '#5A9E72',
        fontWeight: 600, marginBottom: '4px',
      }}>{title}</div>
      <div style={{
        fontSize: '11px', color: '#e8ecf0', lineHeight: 1.55,
        fontWeight: 500, paddingRight: '16px',
      }}>{children}</div>
    </div>
  );
}
