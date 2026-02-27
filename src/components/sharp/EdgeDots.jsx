export default function EdgeDots({ edge }) {
  const filled = edge >= 10 ? 4 : edge >= 8 ? 3 : edge >= 6 ? 2 : 1;
  return (
    <div style={{ display: 'flex', gap: '3px', justifyContent: 'flex-end', marginTop: '4px' }}>
      {[1, 2, 3, 4].map(i => (
        <span key={i} style={{
          width: '5px', height: '5px', borderRadius: '50%',
          backgroundColor: i <= filled ? '#22c55e' : '#374151',
        }} />
      ))}
    </div>
  );
}
