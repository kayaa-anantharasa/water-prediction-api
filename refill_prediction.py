import pandas as pd
from datetime import datetime, timedelta


def _calculate_drop_rate(df: pd.DataFrame):
    """Shared helper: average level-drop rate per hour from historical readings."""
    df = df.copy()
    df["prev_level"] = df["water_level"].shift(1)
    df["prev_time"] = df["timestamp"].shift(1)
    df["hours_diff"] = (df["timestamp"] - df["prev_time"]).dt.total_seconds() / 3600
    df["level_diff"] = df["prev_level"] - df["water_level"]  # positive = level dropped

    drops = df[(df["level_diff"] > 0) & (df["hours_diff"] > 0)]
    if drops.empty:
        return None
    avg_drop_per_hour = (drops["level_diff"] / drops["hours_diff"]).mean()
    return avg_drop_per_hour if avg_drop_per_hour > 0 else None


def _get_anchor_time_and_level(df: pd.DataFrame, avg_drop_per_hour):
    """
    Determines the "current" reference point for timing calculations.

    The last row in the CSV tells us the last KNOWN level, but its
    timestamp may be old (e.g. data collected days ago). We anchor all
    "how many hours from now" calculations to the REAL current time,
    and estimate what the level would be right now by projecting the
    known drop rate forward across the gap between the last reading
    and now (assuming no refill happened in between).
    """
    latest_row = df.iloc[-1]
    last_known_level = float(latest_row["water_level"])
    last_known_time = latest_row["timestamp"]

    now = pd.Timestamp(datetime.now())
    hours_since_last_reading = max((now - last_known_time).total_seconds() / 3600, 0)

    if avg_drop_per_hour is not None and hours_since_last_reading > 0:
        projected_level = last_known_level - (avg_drop_per_hour * hours_since_last_reading)
        projected_level = max(projected_level, 0)
    else:
        projected_level = last_known_level

    return now, projected_level, last_known_level, last_known_time


def predict_next_pump_on(df: pd.DataFrame, threshold: float = 50):
    """
    "Eppa thanni varum" - estimates when the water level will drop to the
    pump-ON threshold, i.e. when the pump is expected to switch on and
    refill the tank. All timing is anchored to the real current date/time.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    avg_drop_per_hour = _calculate_drop_rate(df)
    now, current_level, last_known_level, last_known_time = _get_anchor_time_and_level(df, avg_drop_per_hour)

    if current_level <= threshold:
        return {
            "status": "already_low",
            "current_level": round(current_level, 1),
            "current_timestamp": str(now),
            "message": "Water level is already at or below the pump-ON threshold.",
        }

    if avg_drop_per_hour is None:
        return {
            "status": "insufficient_data",
            "current_level": round(current_level, 1),
            "current_timestamp": str(now),
            "message": "Not enough historical drop data to estimate timing.",
        }

    level_to_drop = current_level - threshold
    hours_remaining = level_to_drop / avg_drop_per_hour
    estimated_datetime = now + timedelta(hours=hours_remaining)

    return {
        "status": "ok",
        "current_level": round(current_level, 1),
        "current_timestamp": str(now),
        "hourly_drop_rate": round(float(avg_drop_per_hour), 2),
        "estimated_hours_remaining": round(float(hours_remaining), 1),
        "estimated_datetime": str(estimated_datetime),
    }


def predict_water_finish(df: pd.DataFrame):
    """
    "Eppa thanni mudiyum" - estimates when the tank will run completely
    empty (water_level reaches 0%). All timing is anchored to the real
    current date/time, not the last CSV row's timestamp.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    avg_drop_per_hour = _calculate_drop_rate(df)
    now, current_level, last_known_level, last_known_time = _get_anchor_time_and_level(df, avg_drop_per_hour)

    if current_level <= 0:
        return {
            "status": "already_empty",
            "current_level": round(current_level, 1),
            "current_timestamp": str(now),
            "message": "Water level is already at 0%.",
        }

    if avg_drop_per_hour is None:
        return {
            "status": "insufficient_data",
            "current_level": round(current_level, 1),
            "current_timestamp": str(now),
            "message": "Not enough historical drop data to estimate timing.",
        }

    hours_remaining = current_level / avg_drop_per_hour
    estimated_datetime = now + timedelta(hours=hours_remaining)

    return {
        "status": "ok",
        "current_level": round(current_level, 1),
        "current_timestamp": str(now),
        "hourly_drop_rate": round(float(avg_drop_per_hour), 2),
        "estimated_hours_remaining": round(float(hours_remaining), 1),
        "estimated_datetime": str(estimated_datetime),
    }