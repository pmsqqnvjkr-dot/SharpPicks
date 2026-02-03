# NBA Sharp Picks - Betting Analysis System

## Overview
Comprehensive NBA betting analysis system with automated data collection, calibrated ensemble ML models for spread predictions, arbitrage detection, live game analysis, and responsible gambling monitoring.

## Tech Stack
- **Frontend**: React + Vite (port 5000)
- **Backend**: Python/Flask (port 8000)
- **Database**: SQLite (sharp_picks.db)

## Current Status
- **Model Accuracy**: 79.4% on test data (15,131 games)
- **Brier Score**: 0.139 (excellent calibration)
- **Features**: 36 features including pace, ratings, line movement
- **Backtest ROI**: +47.26% simulated on historical data

## Recent Changes (Feb 2026)
- **Converted frontend to React** with Vite build system
- Added TrustBanner component showing model stats
- Added NBA pace/offensive/defensive ratings features
- Implemented sample weighting (recent games weighted higher)
- Added betting filters with minimum confidence threshold
- Created live performance tracking system
- Model now uses 36 features (up from 23)
- Added retry logic with exponential backoff for NBA stats API

## Key Files
- `src/` - React frontend (Vite)
  - `App.jsx` - Main dashboard component
  - `components/TrustBanner.jsx` - Model stats banner
  - `components/CalibrationChart.jsx` - Calibration visualization
- `app.py` - Flask API backend (port 8000)
- `model.py` - Ensemble ML prediction model
- `main.py` - Data collection script
- `nba_ratings.py` - Team pace/ratings fetcher (with retry logic)
- `performance_tracker.py` - Prediction logging/tracking
- `rundown_api.py` - The Rundown API integration
- `arbitrage.py` - Arbitrage opportunity detector

## API Endpoints
- `GET /` - Web dashboard
- `GET /api/games` - All games
- `GET /api/predictions` - Model predictions
- `GET /api/arbitrage` - Arbitrage opportunities
- `GET /api/performance` - Model performance stats
- `GET /api/model/calibration` - Calibration check by confidence bucket
- `GET /api/validation/detailed` - Alias for calibration endpoint

## Configuration
- Minimum confidence threshold: 55%
- Strong pick threshold: 60%
- Current season games weighted 1.5x higher

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Track all predictions for performance analysis
