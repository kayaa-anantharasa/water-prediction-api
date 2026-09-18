# from sklearn.linear_model import LogisticRegression
# import pandas as pd


# def train_pump_model(df: pd.DataFrame):
#     X = df[["water_level"]].values
#     y = df["pump"].values  # 1 = ON, 0 = OFF

#     model = LogisticRegression()
#     model.fit(X, y)
#     return model


# def predict_pump_status(model, water_level: float) -> str:
#     pred = model.predict([[water_level]])[0]
#     return "ON" if pred == 1 else "OFF"
import pandas as pd

# Pump turns ON when water level drops to/below this threshold.
# Adjust this to match your actual tank's real trigger point.
PUMP_ON_THRESHOLD = 50


def train_pump_model(df: pd.DataFrame):
    """
    Kept for compatibility with main.py's function call signature.
    We don't actually need to "train" anything for a threshold rule,
    but we auto-detect a sensible threshold from historical data if possible.
    """
    on_rows = df[df["pump"] == 1]
    off_rows = df[df["pump"] == 0]

    if len(on_rows) > 0 and len(off_rows) > 0:
        # Use the midpoint between typical ON-level and typical OFF-level
        # as a data-informed threshold, but only trust it if it looks sane
        # (i.e. ON levels are lower than OFF levels, as expected physically).
        avg_on = on_rows["water_level"].mean()
        avg_off = off_rows["water_level"].mean()
        if avg_on < avg_off:
            return (avg_on + avg_off) / 2

    # Fallback to the fixed default if data doesn't give a sane signal
    return PUMP_ON_THRESHOLD


def predict_pump_status(threshold, water_level: float) -> str:
    return "ON" if water_level <= threshold else "OFF"