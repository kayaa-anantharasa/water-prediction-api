import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression


def forecast_series(series: pd.Series, periods_ahead: int = 7):
    """
    series: pandas Series with datetime index (daily usage or daily level)
    periods_ahead: number of future days to predict

    Uses a linear trend + day-of-week dummy variables to capture
    weekly seasonality (e.g. weekend usage spikes).

    IMPORTANT: predictions always start from TODAY'S actual date (not the
    last date found in the CSV/data source). This keeps the forecast in
    correct real-world chronological order (today, tomorrow, ...) even if
    the underlying data was collected a while ago.
    """
    df = series.reset_index()
    df.columns = ["date", "value"]
    df["t"] = np.arange(len(df))
    df["dow"] = df["date"].dt.dayofweek  # 0=Monday ... 6=Sunday

    # one-hot encode day-of-week (drop first to avoid collinearity)
    dow_dummies = pd.get_dummies(df["dow"], prefix="dow", drop_first=True)
    X = pd.concat([df[["t"]], dow_dummies], axis=1)
    y = df["value"].values

    model = LinearRegression()
    model.fit(X, y)

    # Anchor future predictions to today's real date, not the last data date.
    last_data_date = df["date"].iloc[-1]
    today = pd.Timestamp(datetime.now().date())
    start_date = today + pd.Timedelta(days=1) if today >= last_data_date else last_data_date + pd.Timedelta(days=1)

    # Keep "t" (the trend index) continuing naturally from the data's own
    # timeline, based on how many days have actually passed since the last
    # recorded date, so the linear trend extrapolates sensibly.
    days_gap = (start_date - last_data_date).days
    future_dates = pd.date_range(start=start_date, periods=periods_ahead)
    future_t = np.arange(len(df) + days_gap - 1, len(df) + days_gap - 1 + periods_ahead)
    future_dow = future_dates.dayofweek

    future_df = pd.DataFrame({"t": future_t, "dow": future_dow})
    future_dow_dummies = pd.get_dummies(future_df["dow"], prefix="dow", drop_first=True)
    future_dow_dummies = future_dow_dummies.reindex(columns=dow_dummies.columns, fill_value=0)
    future_X = pd.concat([future_df[["t"]], future_dow_dummies], axis=1)

    predictions = model.predict(future_X)
    predictions = np.clip(predictions, a_min=0, a_max=None)

    return [
        {"date": str(d.date()), "predicted_value": round(float(p), 2)}
        for d, p in zip(future_dates, predictions)
    ]