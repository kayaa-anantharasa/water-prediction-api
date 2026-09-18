# Water Prediction API

1. Install dependencies:
   `pip install -r requirements.txt`
2. Start the API:
   `python -m uvicorn main:app --host 0.0.0.0 --port 8000`

Endpoints:

- `GET /predict/usage?days_ahead=7`
- `GET /predict/level?days_ahead=7`
- `GET /predict/pump?water_level=60`
- `GET /predict/next-refill?threshold=50`
- `GET /predict/water-finish`
