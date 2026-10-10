"""SMA(5/20) SPY paper-trading bot. Run once per trading morning.

Set DRY_RUN=False only when ready to submit actual PAPER orders.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv

from alpaca.common.exceptions import APIError
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

# Configuration
SYMBOL = "SPY"
ORDER_QTY = 1
DRY_RUN = True
NY = ZoneInfo("America/New_York")


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_SECRET_KEY"]
    if not key.isascii() or not secret.isascii():
        raise ValueError("Alpaca credentials contain non-ASCII characters")

    trader = TradingClient(key, secret, paper=True)
    data_client = StockHistoricalDataClient(key, secret)

    now_utc = datetime.now(timezone.utc)
    now_ny = now_utc.astimezone(NY)
    print(f"Checked at {now_ny:%Y-%m-%d %H:%M:%S %Z}")

    request = StockBarsRequest(
        symbol_or_symbols=SYMBOL,
        timeframe=TimeFrame.Day,
        start=now_utc - timedelta(days=90),
        end=now_utc,
        feed=DataFeed.IEX,
    )
    bars = data_client.get_stock_bars(request).df
    if bars.empty:
        print("No market data. Skipping.")
        return

    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.xs(SYMBOL, level="symbol")
    bars = bars.sort_index().copy()

    # Use only fully completed daily bars, never today's partial candle.
    dates_ny = bars.index.tz_convert(NY).date
    bars = bars[dates_ny < now_ny.date()].copy()
    if len(bars) < 21:
        print("Not enough completed daily bars. Skipping.")
        return

    bars["SMA_5"] = bars["close"].rolling(5).mean()
    bars["SMA_20"] = bars["close"].rolling(20).mean()
    previous = bars.iloc[-2]
    current = bars.iloc[-1]
    signal = "HOLD"
    if previous["SMA_5"] <= previous["SMA_20"] and current["SMA_5"] > current["SMA_20"]:
        signal = "BUY"
    elif previous["SMA_5"] >= previous["SMA_20"] and current["SMA_5"] < current["SMA_20"]:
        signal = "SELL"

    signal_day = bars.index[-1].tz_convert(NY).date()
    print(f"SPY {signal_day} close: ${current['close']:.2f}")
    print(f"SMA 5: {current['SMA_5']:.3f} | SMA 20: {current['SMA_20']:.3f}")
    print(f"Signal: {signal}")
    if signal == "HOLD":
        print("No new crossover. No order.")
        return

    # Trading is restricted to regular market hours.
    if not trader.get_clock().is_open:
        print("Stock market closed. No order.")
        return

    pending = trader.get_orders(
        filter=GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[SYMBOL],
        )
    )
    if pending:
        print("An open SPY order already exists. Skipping.")
        return

    positions = trader.get_all_positions()
    position = next((p for p in positions if p.symbol == SYMBOL), None)
    held_qty = float(position.qty) if position else 0.0

    if signal == "BUY":
        if held_qty != 0:
            print(f"Already holding {held_qty} SPY shares. Skipping buy.")
            return
        account = trader.get_account()
        estimated_cost = float(current["close"]) * ORDER_QTY * 1.10
        if float(account.cash) < estimated_cost:
            print("Not enough cash for estimated cost plus 10% buffer. Skipping.")
            return
        side = OrderSide.BUY
        qty = ORDER_QTY
    else:
        if held_qty <= 0:
            print("No SPY position to sell. Skipping.")
            return
        side = OrderSide.SELL
        qty = min(held_qty, ORDER_QTY)

    # Same daily signal always gets the same ID; avoid duplicate submission.
    client_id = f"sma520-{SYMBOL.lower()}-{signal_day:%Y%m%d}-{signal.lower()}"
    try:
        existing = trader.get_order_by_client_id(client_id)
    except APIError as exc:
        if exc.status_code != 404:
            raise
    else:
        print(f"Signal already has order {existing.id} ({existing.status}). Skipping.")
        return

    print(f"Proposed order: {side.value.upper()} {qty:g} {SYMBOL}")
    if DRY_RUN:
        print("DRY RUN: No paper order submitted.")
        return

    result = trader.submit_order(
        order_data=MarketOrderRequest(
            symbol=SYMBOL,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_id,
        )
    )
    print(f"PAPER ORDER SUBMITTED: {result.id}; status={result.status}")


if __name__ == "__main__":
    main()
