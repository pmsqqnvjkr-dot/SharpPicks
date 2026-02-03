import { useState, useEffect } from 'react';

export default function ModelTransparency() {
  const [calibration, setCalibration] = useState(null);
  const [performance, setPerformance] = useState(null);

  useEffect(() => {
    fetch('/api/model/calibration')
      .then(res => res.json())
      .then(setCalibration)
      .catch(console.error);
    
    fetch('/api/performance')
      .then(res => res.json())
      .then(setPerformance)
      .catch(console.error);
  }, []);

  const bucketOrder = ['50-55%', '55-60%', '60-65%', '65-70%', '70-75%', '80-100%'];

  return (
    <div className="transparency-section">
      <h2>Model Transparency</h2>
      <p className="section-subtitle">Complete visibility into how our predictions perform</p>

      <div className="transparency-grid">
        <div className="transparency-card">
          <h3>Calibration by Confidence</h3>
          <p className="card-description">Expected vs actual win rates per confidence bucket</p>
          
          {calibration?.buckets && (
            <div className="calibration-table">
              <div className="table-header">
                <span>Confidence</span>
                <span>Predictions</span>
                <span>Expected</span>
                <span>Actual</span>
                <span>Status</span>
              </div>
              {bucketOrder.map(bucket => {
                const data = calibration.buckets[bucket];
                if (!data) return null;
                return (
                  <div key={bucket} className="table-row">
                    <span className="bucket-name">{bucket}</span>
                    <span>{data.total}</span>
                    <span>{data.expected_rate}%</span>
                    <span className={data.actual_rate > 0 ? 'highlight' : ''}>
                      {data.actual_rate}%
                    </span>
                    <span className={`status ${data.calibrated === true ? 'calibrated' : data.calibrated === false ? 'off' : 'pending'}`}>
                      {data.calibrated === true ? 'Calibrated' : data.calibrated === false ? 'Off' : 'Pending'}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
          
          {calibration && (
            <div className="calibration-summary">
              <span>Mean Absolute Error: <strong>{calibration.mean_absolute_error}%</strong></span>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${
                calibration.calibration_status === 'excellent' 
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : calibration.calibration_status === 'good'
                  ? 'bg-blue-50 border-blue-200 text-blue-900'
                  : calibration.calibration_status === 'moderate'
                  ? 'bg-amber-50 border-amber-200 text-amber-900'
                  : 'bg-red-50 border-red-200 text-red-900'
              }`}>
                {calibration.calibration_status?.toUpperCase()}
              </span>
            </div>
          )}
        </div>

        <div className="transparency-card">
          <h3>Live Performance</h3>
          <p className="card-description">Real-time tracking of all predictions</p>
          
          {performance && (
            <div className="performance-stats">
              <div className="stat-row">
                <span>Total Predictions</span>
                <span className="value">{performance.total_predictions || 0}</span>
              </div>
              <div className="stat-row">
                <span>Correct Picks</span>
                <span className="value success">{performance.correct || 0}</span>
              </div>
              <div className="stat-row">
                <span>Incorrect Picks</span>
                <span className="value error">{performance.incorrect || 0}</span>
              </div>
              <div className="stat-row">
                <span>Win Rate</span>
                <span className="value highlight">
                  {performance.win_rate ? `${(performance.win_rate * 100).toFixed(1)}%` : 'N/A'}
                </span>
              </div>
              <div className="stat-row">
                <span>Pending Results</span>
                <span className="value">{performance.pending || 0}</span>
              </div>
            </div>
          )}
          
          {(!performance || performance.total_predictions === 0) && (
            <div className="no-data">
              <p>Predictions will be tracked here as games complete.</p>
            </div>
          )}
        </div>

        <div className="transparency-card full-width">
          <h3>Model Methodology</h3>
          <div className="methodology-content">
            <div className="method-item">
              <h4>Ensemble Approach</h4>
              <p>Combines Random Forest, Gradient Boosting, and Logistic Regression models for robust predictions.</p>
            </div>
            <div className="method-item">
              <h4>36 Features</h4>
              <p>Includes team records, pace ratings, offensive/defensive efficiency, rest days, home/away splits, and line movement.</p>
            </div>
            <div className="method-item">
              <h4>Calibration</h4>
              <p>Model is calibrated so that 60% confidence picks actually win ~60% of the time.</p>
            </div>
            <div className="method-item">
              <h4>Sample Weighting</h4>
              <p>Recent games weighted 1.5x higher to capture current team form and roster changes.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
