from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from data_prep import load_data, get_daily_usage, get_daily_avg_level
from model import forecast_series
from refill_prediction import predict_next_pump_on, predict_water_finish

app = FastAPI(title="Water Tank Prediction API")

# Allow requests from any origin (needed for Flutter web, and for testing
# from different ports/devices). For production, replace "*" with your
# app's actual domain(s) for better security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "water_data.csv"


@app.get("/")
def root():
    return {"status": "running", "endpoints": ["/predict/usage", "/predict/level", "/predict/next-refill", "/predict/water-finish"]}


@app.get("/predict/usage")
def predict_usage(days_ahead: int = 7):
    try:
        df = load_data(DATA_FILE)
        daily_usage = get_daily_usage(df)
        predictions = forecast_series(daily_usage, days_ahead)
        return {"type": "daily_usage_liters", "predictions": predictions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/level")
def predict_level(days_ahead: int = 7):
    try:
        df = load_data(DATA_FILE)
        daily_level = get_daily_avg_level(df)
        predictions = forecast_series(daily_level, days_ahead)
        return {"type": "water_level_percent", "predictions": predictions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/next-refill")
def predict_next_refill(threshold: float = 50):
    """
    "Eppa thanni varum" - predicts when the pump is expected to turn ON
    (i.e. when water is expected to be refilled/come next).
    """
    try:
        df = load_data(DATA_FILE)
        result = predict_next_pump_on(df, threshold=threshold)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/water-finish")
def predict_finish():
    """
    "Eppa thanni mudiyum" - predicts when the tank water is expected to
    run completely out (reach 0%), based on current level and usage rate.
    """
    try:
        df = load_data(DATA_FILE)
        result = predict_water_finish(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))