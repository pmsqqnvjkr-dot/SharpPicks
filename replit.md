# NBA Sharp Picks - Betting Analysis System

## Overview
Comprehensive NBA betting analysis system with automated data collection, calibrated ensemble ML models for spread predictions, arbitrage detection, live game analysis, and responsible gambling monitoring.

## Tech Stack
- **Frontend**: React + Vite (port 5000)
- **Backend**: Python/Flask (port 8000)
- **Database**: PostgreSQL (via DATABASE_URL)
- **Auth**: Replit Auth (OAuth2 with Google, GitHub, Apple, email)

## Current Status
- **Model Accuracy**: 79.4% on test data (15,131 games)
- **Brier Score**: 0.139 (excellent calibration)
- **Features**: 36 features including pace, ratings, line movement
- **Backtest ROI**: +47.26% simulated on historical data

## Recent Changes (Feb 2026)
- **Added Replit Auth** with OAuth2 (Google, GitHub, Apple, email)
- Migrated database from SQLite to PostgreSQL
- Added User and OAuth models with premium status tracking
- Auth-protected API endpoints for bets, upgrade, unit size
- Premium upgrade and unit size now persist to database
- **Converted frontend to React** with Vite build system
- Added TrustBanner component showing model stats
- Added NBA pace/offensive/defensive ratings features
- Implemented sample weighting (recent games weighted higher)
- Added betting filters with minimum confidence threshold
- Created live performance tracking system
- Model now uses 36 features (up from 23)
- Added retry logic with exponential backoff for NBA stats API

## Key Files
- `src/` - React frontend (Vite + React Router)
  - `App.jsx` - Router with 3 routes (/, /app, /analytics)
  - `SharpPicksApp.jsx` - Consumer picks app
  - `AnalyticsDashboard.jsx` - Analytics deep dive
  - `components/TrustBanner.jsx` - Model stats banner
  - `components/TodaysPicks.jsx` - Pick cards with confidence filters
  - `components/ModelTransparency.jsx` - Calibration and performance tracking
- `app.py` - Flask API backend (port 8000)
- `models.py` - SQLAlchemy User and OAuth models
- `replit_auth.py` - Replit Auth blueprint configuration
- `model.py` - Ensemble ML prediction model
- `main.py` - Data collection script
- `nba_ratings.py` - Team pace/ratings fetcher (with retry logic)
- `performance_tracker.py` - Prediction logging/tracking
- `rundown_api.py` - The Rundown API integration
- `arbitrage.py` - Arbitrage opportunity detector

## API Endpoints
- `GET /` - Web dashboard
- `GET /api/predictions` - Today's model predictions with confidence
- `GET /api/performance` - Live performance tracking stats
- `GET /api/model/calibration` - Calibration check by confidence bucket
- `GET /api/admin/stats` - Dashboard stats (games, spreads, etc.)
- `GET /api/auth/user` - Current authenticated user info
- `POST /api/auth/upgrade` - Upgrade user to premium (auth required)
- `POST /api/auth/unit-size` - Set user's betting unit size (auth required)
- `GET/POST /api/bets` - User's tracked bets (auth required)
- `GET /auth/replit_auth` - OAuth login endpoint
- `GET /auth/logout` - Logout endpoint

## Configuration
- Minimum confidence threshold: 55%
- Strong pick threshold: 60%
- Current season games weighted 1.5x higher

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Track all predictions for performance analysis
