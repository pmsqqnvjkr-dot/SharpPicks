import { useState, useEffect } from 'react';

export default function CalibrationChart() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/model/calibration')
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data || !data.buckets) {
    return <div className="calibration-chart loading">Loading calibration data...</div>;
  }

  const buckets = Object.entries(data.buckets).filter(([_, v]) => v.total > 0);

  return (
    <div className="calibration-chart">
      <h3>Model Calibration by Confidence</h3>
      <p className="calibration-status">
        Status: <span className={`status-${data.calibration_status}`}>
          {data.calibration_status.toUpperCase()}
        </span>
        {' '}(MAE: {data.mean_absolute_error}%)
      </p>
      
      {buckets.length === 0 ? (
        <p className="no-data">No predictions tracked yet. Check back after games complete!</p>
      ) : (
        <div className="calibration-bars">
          {buckets.map(([bucket, info]) => (
            <div key={bucket} className="calibration-row">
              <span className="bucket-label">{bucket}</span>
              <div className="bar-container">
                <div 
                  className="bar expected" 
                  style={{ width: `${info.expected_rate}%` }}
                  title={`Expected: ${info.expected_rate}%`}
                />
                <div 
                  className={`bar actual ${info.calibrated ? 'good' : 'off'}`}
                  style={{ width: `${info.actual_rate}%` }}
                  title={`Actual: ${info.actual_rate}%`}
                />
              </div>
              <span className="bar-values">
                {info.actual_rate}% ({info.total} picks)
                {info.calibrated ? ' ✅' : ' ⚠️'}
              </span>
            </div>
          ))}
        </div>
      )}
      
      <div className="calibration-legend">
        <span><span className="legend-dot expected"></span> Expected</span>
        <span><span className="legend-dot actual"></span> Actual</span>
      </div>
    </div>
  );
}
