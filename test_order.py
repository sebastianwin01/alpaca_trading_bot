import os

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    QueryOrderStatus,
)

DRY_RUN = False
SYMBOL = "SPY"
QUANTITY = 1

client = TradingClient(
    os.environ["ALPACA_API_KEY"],
    os.environ["ALPACA_SECRET_KEY"],
    paper=True
)

account = client.get_account()
clock = client.get_clock()

print("Cash:", account.cash)
print("Market open:", clock.is_open)

positions = client.get_all_positions()
held = any(p.symbol == SYMBOL for p in positions)

open_orders = client.get_orders(
    filter=GetOrdersRequest(
        status=QueryOrderStatus.OPEN,
        symbols=[SYMBOL]
    )
)

if held or open_orders:
    print("Existing position or open order. Skipping.")

elif DRY_RUN:
    print(f"DRY RUN: Would BUY {QUANTITY} share of {SYMBOL}")

elif not clock.is_open:
    print("Market closed. No order submitted.")

elif float(account.cash) <= 0:
    print("No available cash.")

else:
    order = MarketOrderRequest(
        symbol=SYMBOL,
        qty=QUANTITY,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )

    result = client.submit_order(order)

    print("Paper order submitted:", result.id)
    print("Order status:", result.status)
