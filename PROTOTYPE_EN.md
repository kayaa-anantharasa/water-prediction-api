# Water Tank Prediction API — Prototype Guide

## What does this project do?

This project uses historical water-tank readings to estimate water usage, tank level, pump status, the next refill time, and when the tank may run out of water. A Flutter app or another client can send requests to the API and receive predictions.

The current prototype reads data from `water_data.csv`. It does not receive live sensor readings or physically control the pump.

## Where does the data come from?

Each row in `water_data.csv` contains:

- `timestamp` — date and time of the reading
- `water_level` — tank water level in percent
- `liters` — amount of water in the tank
- `pump` — pump state (`ON` or `OFF`)
- `daily_usage` — water usage associated with the reading

## How does the project work?

1. `data_prep.py` reads the CSV, converts pump states to numeric values, and calculates daily usage and average water level.
2. `model.py` uses historical daily values, their time trend, and day of the week to forecast future usage or water level. Negative forecasts are set to zero.
3. `pump_model.py` estimates a threshold from the water levels recorded when the pump was ON and OFF. At or below the threshold, the predicted status is `ON`; above it, the prediction is `OFF`.
4. `refill_prediction.py` estimates the water-level drop rate from past readings and uses it to estimate when the tank will reach a threshold or become empty.
5. `main.py` creates the FastAPI server and exposes the predictions through HTTP endpoints.

## Code walkthrough

The project is written in Python. Each `.py` file has a specific responsibility. `main.py` receives API requests, calls the relevant helper functions, and returns the result as JSON.

### `main.py` — handling API requests

`FastAPI(...)` creates the API application. `@app.get(...)` maps a URL to the function that handles its GET request. For example:

```python
@app.get("/predict/usage")
def predict_usage(days_ahead: int = 7):
    df = load_data(DATA_FILE)
    daily_usage = get_daily_usage(df)
    predictions = forecast_series(daily_usage, days_ahead)
    return {"type": "daily_usage_liters", "predictions": predictions}
```

In this example:

- `days_ahead` is the number of days requested in the URL. It defaults to `7`.
- `load_data(...)` reads the CSV into a pandas DataFrame.
- `get_daily_usage(...)` groups the readings into daily usage totals.
- `forecast_series(...)` produces the forecast for the requested number of days.
- `return` sends the result to the client as a JSON response.

The other prediction endpoints follow the same general pattern: read request parameters, load the CSV, call the appropriate prediction function, and return its result.

#### Other code in `main.py`

- The `from ... import ...` statements make functions and tools from other modules available here. `FastAPI`, `HTTPException`, and `CORSMiddleware` provide the API framework, HTTP error responses, and cross-origin access support.
- `app = FastAPI(title=...)` creates the API application. The title appears in the interactive API documentation.
- `app.add_middleware(CORSMiddleware, ...)` allows requests from clients running on another origin or port. The current `*` settings allow all origins, methods, and headers. This is broad prototype configuration; production should restrict access to the app's required origins.
- `DATA_FILE = "water_data.csv"` stores the data filename in one place. The endpoints pass it to `load_data`.
- `@app.get("/")` maps the root URL to `root()`, which returns a running status and a list of some endpoints.
- `@app.get("/predict/usage")` maps requests to `predict_usage(days_ahead=7)`. It aggregates daily usage, forecasts it with `forecast_series`, and returns JSON.
- `@app.get("/predict/level")` maps requests to `predict_level(days_ahead=7)`. It prepares daily average levels and forecasts them.
- `@app.get("/predict/pump")` requires a `water_level` query parameter, calculates a threshold from the CSV, and returns the predicted pump status.
- `@app.get("/predict/next-refill")` accepts a `threshold` parameter, defaulting to `50`, and returns the time estimated by `predict_next_pump_on`.
- `@app.get("/predict/water-finish")` calls `predict_water_finish` without an additional parameter.
- The `try` blocks run the prediction code. If an exception occurs, the `except` blocks convert it into an HTTP 500 response and include the exception message.

### `data_prep.py` — preparing CSV data

- `load_data(file_path)` reads the CSV, parses `timestamp` as a date/time, maps pump values from `ON`/`OFF` to `1`/`0`, and sorts the rows by timestamp.
- `get_daily_usage(df)` adds together the `daily_usage` values recorded on the same date.
- `get_daily_avg_level(df)` calculates the average `water_level` for each date.
- `df.copy()` creates a temporary copy so the original DataFrame is not changed while daily data is prepared.
- `timestamp.dt.date` extracts the date from each timestamp. `groupby("date")` groups rows from the same date; `.sum()` calculates a total and `.mean()` calculates an average.
- The daily result's index is converted back to datetime with `pd.to_datetime(...)`, so the forecasting code can work with dates and weekdays.

### `model.py` — forecasting usage and water level

`forecast_series(series, periods_ahead)` takes a historical time series. The numeric feature `t` represents the time trend, and `dow` represents the day of the week. Scikit-learn's `LinearRegression` learns from those features and predicts future values. `periods_ahead` specifies how many days to forecast. `np.clip(..., a_min=0, ...)` prevents negative predictions.

#### What are the imports in `model.py` used for?

```python
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
```

- `import numpy as np` — NumPy provides numerical operations. `np.arange(...)` creates sequences of time-step numbers, and `np.clip(...)` changes negative predictions to `0`. `np` is the conventional short name for NumPy.
- `import pandas as pd` — Pandas handles tables and time-series data. `pd.Series` is used in the function's type annotation; `pd.DataFrame(...)` creates the future input table, and `pd.concat(...)` joins columns. `pd` is the conventional short name for pandas.
- `from datetime import datetime, timedelta` — These are Python date/time utilities. `datetime.now()` gets the current date. `timedelta` is imported but is not used in this file; `pd.Timedelta` is used to calculate date offsets.
- `from sklearn.linear_model import LinearRegression` — Imports Scikit-learn's linear regression algorithm. `LinearRegression()` creates the model, `model.fit(X, y)` learns from historical inputs and values, and `model.predict(...)` forecasts future values.

#### How are future predictions produced?

Future usage and water-level forecasts use Scikit-learn's `LinearRegression`. The model learns a simple mathematical trend from historical values. It is not an LSTM, neural network, or ARIMA model.

1. **Prepare daily data:** For usage, the `daily_usage` values for each date are summed. For water level, the readings for each date are averaged.
2. **Create model inputs:** Each day receives a sequential time index `t` (`0, 1, 2, ...`). Its weekday (`dow`, Monday through Sunday) is also recorded and converted into separate 0/1 dummy columns.
3. **Learn the trend:** `LinearRegression.fit(X, y)` learns the relationship between the historical inputs (`t` and weekday columns) and observed values (`y`).
4. **Create future inputs:** The code generates the requested number of future dates. For each date it calculates the continuing `t` value and weekday. It aligns the weekday columns with those used for training.
5. **Predict and return:** `model.predict(...)` produces forecast values. Negative values are clipped to `0`, rounded to two decimal places, paired with dates, and returned in the API's JSON response.

In simplified form, the model learns a relationship like:

```text
predicted value = baseline + (time trend × day index) + weekday adjustment
```

For example, when a client requests a seven-day usage forecast, the model receives the time index and weekday for each of the seven future dates and returns a predicted usage for each date. The actual values depend on the CSV data and forecast dates.

This method assumes that historical trends and weekday patterns will continue. It does not provide a confidence interval. Predictions may be unreliable if there is too little data or the data varies substantially.

### `pump_model.py` — predicting pump status

- Despite its name, `train_pump_model(df)` does not train a machine-learning model. It estimates a threshold from the data. It calculates the average water level for pump-ON rows and pump-OFF rows. If the ON average is lower, their midpoint becomes the threshold. If the data is missing or does not show a sensible relationship, it uses the default threshold `50`.
- `predict_pump_status(threshold, water_level)` returns `"ON"` if the water level is at or below the threshold; otherwise, it returns `"OFF"`.
- The Logistic Regression code near the top of the file is commented out with `#`. Python does not execute it; the active implementation is the threshold rule.
- `df[df["pump"] == 1]` and `df[df["pump"] == 0]` select pump-ON and pump-OFF rows, respectively. Their average levels are used to estimate the threshold.

### `refill_prediction.py` — estimating refill and empty times

- `_calculate_drop_rate(df)` calculates the time between consecutive readings and how much the water level fell. It returns the average level drop per hour.
- `_get_anchor_time_and_level(...)` uses the latest CSV reading to estimate the level at the current time. This assumes there has been no refill since that reading.
- `predict_next_pump_on(df, threshold)` estimates how many hours it will take for the estimated level to reach the threshold. It returns a different status if the level is already at/below the threshold or there is not enough drop data.
- `predict_water_finish(df)` uses the same drop rate to estimate when the level will reach zero.
- `sort_values("timestamp")` orders readings by time. `.shift(1)` makes the preceding row's level and timestamp available for comparison with the current row.
- `hours_diff` is the time between readings; `level_diff` is the preceding level minus the current level. Only readings with a positive time interval and a falling water level are included in the drop-rate calculation. If no such readings exist, the function returns `None`, so it cannot estimate a time.
- To estimate the current level, the average hourly drop is multiplied by the number of hours since the latest CSV reading and subtracted from the last known level. The result is not allowed to go below zero.
- The refill-time calculation is approximately `(estimated current level - threshold) / hourly drop rate`. The empty-time calculation is `estimated current level / hourly drop rate`. The response includes a status and, when available, the estimated time and hours remaining.
- `already_low` or `already_empty` means the target level has already been reached. `insufficient_data` means there is not enough data to calculate a drop rate. `ok` means a time estimate was produced.

### The full path of an API request

For a request such as `/predict/usage?days_ahead=7`:

1. FastAPI calls `predict_usage` in `main.py`.
2. `data_prep.py` reads the CSV and prepares daily usage.
3. `model.py` forecasts the next seven days.
4. `main.py` sends the predictions to the client as JSON.

## Dependencies and run commands

`requirements.txt` lists the Python packages used by the project:

- `fastapi` — creates HTTP APIs.
- `uvicorn` — runs the FastAPI application as a web server.
- `pandas` — handles CSV, table, and time-series data.
- `numpy` — provides numerical arrays and math operations.
- `scikit-learn` — provides the `LinearRegression` forecasting algorithm.
- `openpyxl` — helps pandas read/write Excel `.xlsx` files; the current code reads CSV, so it is not directly used for CSV loading.

`pip install -r requirements.txt` installs the listed packages. `python -m uvicorn main:app ...` starts the `app` application defined in `main.py` using Uvicorn. `--host 0.0.0.0` makes the server accessible to other devices on the network, and `--port 8000` runs it on port 8000.

## API endpoints

| Endpoint | What it does |
|---|---|
| `GET /predict/usage?days_ahead=7` | Forecasts daily water usage for the next seven days. |
| `GET /predict/level?days_ahead=7` | Forecasts the average water level for the next seven days. |
| `GET /predict/pump?water_level=60` | Predicts whether the pump status is `ON` or `OFF` at the supplied level. |
| `GET /predict/next-refill?threshold=50` | Estimates when the water level will reach the pump threshold. |
| `GET /predict/water-finish` | Estimates when the tank may run out of water. |

`days_ahead`, `water_level`, and `threshold` are inputs sent in the request. Each endpoint returns JSON. Open `/docs` to inspect the API responses and try the endpoints interactively.

## Running the project

Open a terminal in the project folder and install the required Python packages:

```bash
pip install -r requirements.txt
```

Then start the API server:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` in a browser. If the Flutter app runs on another device, use the computer's IP address that the device can access instead of `localhost`.

## Prototype limitations

- Predictions depend only on historical data in the CSV. Their accuracy depends on the amount and quality of that data.
- Refill and empty-time estimates assume there has been no refill since the latest reading. If a refill occurred, the estimate may be wrong.
- The estimated pump threshold should be checked against the real pump configuration.
- This is a prototype. Before real-world use, test live sensor integration, input validation, error handling, access control, and deployment security.
