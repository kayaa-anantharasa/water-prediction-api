1.pip install -r requirements.txt
2.uvicorn main:app --host 0.0.0.0 --port 8000

http://localhost:8000/predict/usage?days_ahead=7    → daily usage prediction
http://localhost:8000/predict/level?days_ahead=7    → water level prediction
http://localhost:8000/predict/next-refill?threshold=50 → refill timing estimate
http://localhost:8000/predict/water-finish          → when tank is expected to run out

http://localhost:8000/predict/usage?days_ahead=7 -> set default