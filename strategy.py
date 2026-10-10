import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

# 1. Connect to Alpaca market data
client = StockHistoricalDataClient(
    os.environ["ALPACA_API_KEY"],
    os.environ["ALPACA_SECRET_KEY"]
)

# 2. Choose the stock or ETF
symbol = "SPY"

# 3. Request 90 days of historical prices
now = datetime.now(timezone.utc)

request = StockBarsRequest(
    symbol_or_symbols=symbol,
    timeframe=TimeFrame.Day,
    start=now - timedelta(days=90),
    end=now,
    feed=DataFeed.IEX
)

bars = client.get_stock_bars(request).df

if bars.empty:
    raise RuntimeError("No market data returned")

# 4. Prepare the price data
if isinstance(bars.index, pd.MultiIndex):
    bars = bars.xs(symbol, level="symbol")

bars = bars.sort_index().copy()

# Exclude today's potentially incomplete daily candle
ny_time = ZoneInfo("America/New_York")
today = datetime.now(ny_time).date()

bars = bars[
    bars.index.tz_convert(ny_time).date < today
].copy()

if len(bars) < 21:
    raise RuntimeError("Not enough completed daily bars")

# 5. Calculate moving averages
bars["SMA_5"] = bars["close"].rolling(5).mean()
bars["SMA_20"] = bars["close"].rolling(20).mean()

# 6. Compare the latest two completed days
previous = bars.iloc[-2]
current = bars.iloc[-1]

signal = "HOLD"

if (previous["SMA_5"] <= previous["SMA_20"]
        and current["SMA_5"] > current["SMA_20"]):
    signal = "BUY"

elif (previous["SMA_5"] >= previous["SMA_20"]
        and current["SMA_5"] < current["SMA_20"]):
    signal = "SELL"

# 7. Display results
print(bars[["close", "SMA_5", "SMA_20"]].tail())

print("\nLatest completed day:", bars.index[-1])
print("Latest closing price:", current["close"])
print("Trading signal:", signal)
