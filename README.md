# Water Prediction API

1. Install dependencies:
   `pip install -r requirements.txt`
2. Start the API:
   `python -m uvicorn main:app --host 0.0.0.0 --port 8000`

Endpoints:

- `GET /predict/usage?days_ahead=7`
- `GET /predict/level?days_ahead=7`
- `GET /predict/next-refill?threshold=50`
- `GET /predict/water-finish`

<!-- Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^(127|169)\.' } | Select-Object InterfaceAlias, IPAddress
http://192.168.8.103:8000/docs
flutter url http://192.168.8.103:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000 -->