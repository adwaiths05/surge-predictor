# Ride-Hailing Surge Prediction Backend

Production-style real-time inference backend for NYC surge multiplier prediction.

## What This Repository Provides
- FastAPI inference endpoints
- Live weather, traffic, and holiday integration
- Encoder and model artifact loading for inference
- Deterministic feature ordering from `artifacts/feature_columns.pkl`
- Docker-ready runtime
- Pytest suite with mocked external APIs

## Quick Start
1. Create and activate a Python 3.11 environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Add artifacts to `artifacts/`:
   - `model.pkl`
   - `borough_encoder.pkl`
   - `zone_encoder.pkl`
   - `zone_name_encoder.pkl`
   - `feature_columns.pkl`
4. Create `.env` with:
   - `TOMTOM_API_KEY=...`
   - `CALENDARIFIC_API_KEY=...`
   - `OPENMETEO_BASE_URL=https://api.open-meteo.com/v1/forecast`
   - `MODEL_PATH=artifacts/model.pkl`
   - `LOG_LEVEL=INFO`
5. Run API:
   - `uvicorn backend.app:app --reload`

## API Endpoints
- `GET /` health check
- `GET /ready` readiness check for runtime/artifacts/API-key availability
- `GET /zones` returns supported zone names
- `POST /predict` body: `{ "zone_name": "Alphabet City" }`

## Startup Validation
- Backend startup is fail-fast.
- If required artifacts are missing, empty, or still placeholder files, startup aborts with an explicit runtime error.

## Docker
- Build: `docker build -t surge-backend .`
- Run: `docker run --env-file .env -p 8000:8000 surge-backend`

## Notes
- This repository intentionally keeps frontend and deployment folders as placeholders.
- Backend code is in `backend/`.
