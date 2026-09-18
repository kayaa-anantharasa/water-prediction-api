import pandas as pd


def load_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df["pump"] = df["pump"].map({"ON": 1, "OFF": 0})
    df = df.sort_values("timestamp")
    return df


def get_daily_usage(df: pd.DataFrame) -> pd.Series:
    temp = df.copy()
    temp["date"] = temp["timestamp"].dt.date
    daily = temp.groupby("date")["daily_usage"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def get_daily_avg_level(df: pd.DataFrame) -> pd.Series:
    temp = df.copy()
    temp["date"] = temp["timestamp"].dt.date
    daily = temp.groupby("date")["water_level"].mean()
    daily.index = pd.to_datetime(daily.index)
    return daily