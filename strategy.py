import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    QueryOrderStatus
)

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
# -----------------------------------------
# PAPER TRADING EXECUTION
# -----------------------------------------

DRY_RUN = True
ORDER_QTY = 1

trader = TradingClient(
    api_key=os.environ["ALPACA_API_KEY"],
    secret_key=os.environ["ALPACA_SECRET_KEY"],
    paper=True
)

print("\n--- Paper Trading Bot ---")

if signal == "HOLD":
    print("No new crossover. No order needed.")

else:
    # Check for existing pending orders
    pending_orders = trader.get_orders(
        filter=GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[symbol]
        )
    )

    # Check current positions
    positions = trader.get_all_positions()

    position = next(
        (p for p in positions if p.symbol == symbol),
        None
    )

    held_qty = float(position.qty) if position else 0

    order_side = None

    if pending_orders:
        print("Existing open order. Skipping.")

    elif signal == "BUY" and held_qty == 0:
        account = trader.get_account()

        # Use cash, not leveraged buying power
        estimated_cost = float(current["close"]) * ORDER_QTY

        if float(account.cash) >= estimated_cost * 1.10:
            order_side = OrderSide.BUY
        else:
            print("Insufficient cash.")

    elif signal == "SELL" and held_qty >= ORDER_QTY:
        order_side = OrderSide.SELL

    else:
        print("No eligible trade based on current position.")

    if order_side is not None:
        print(f"Proposed: {order_side.value} {ORDER_QTY} {symbol}")

        if DRY_RUN:
            print("DRY RUN: No order submitted.")

        elif not trader.get_clock().is_open:
            print("Market is closed. No order submitted.")

        else:
            order = MarketOrderRequest(
                symbol=symbol,
                qty=ORDER_QTY,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                client_order_id=(
                    f"sma520-{symbol.lower()}-"
                    f"{bars.index[-1].date():%Y%m%d}-"
                    f"{signal.lower()}"
                )
            )

            result = trader.submit_order(order)

            print("Paper order submitted!")
            print("Order ID:", result.id)
            print("Status:", result.status)
