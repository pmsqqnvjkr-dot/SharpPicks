export default function StatsCard({ icon, label, value, color, subtext }) {
  return (
    <div className="stats-card">
      <div className="stats-icon" style={{ background: color || '#3B82F6' }}>
        {icon}
      </div>
      <div className="stats-content">
        <span className="stats-label">{label}</span>
        <span className="stats-value">{value}</span>
        {subtext && <span className="stats-subtext">{subtext}</span>}
      </div>
    </div>
  );
}
