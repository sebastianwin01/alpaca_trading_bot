import os
from dotenv import load_dotenv

load_dotenv(override=True)

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

# Load credentials from .env
load_dotenv(override=True)

# Validate API credentials
for name in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
    value = os.environ.get(name, "")

    print(f"{name}:")
    print(f"  Loaded: {bool(value)}")
    print(f"  ASCII valid: {value.isascii()}")

    if not value or not value.isascii():
        for index, char in enumerate(value):
            if not char.isascii():
                print(
                    f"  Invalid character at position {index}: "
                    f"Unicode U+{ord(char):04X}"
                )

        raise ValueError(f"Invalid credential: {name}")


# Trading configuration
DRY_RUN = True
SYMBOL = "SPY"
QUANTITY = 1

# Connect to Alpaca paper trading
client = TradingClient(
    os.environ["ALPACA_API_KEY"],
    os.environ["ALPACA_SECRET_KEY"],
    paper=True
)

# Account information
account = client.get_account()
clock = client.get_clock()

print("Cash:", account.cash)
print("Market open:", clock.is_open)

# Check existing positions
positions = client.get_all_positions()

held = any(
    p.symbol == SYMBOL for p in positions
)

# Check open orders
open_orders = client.get_orders(
    filter=GetOrdersRequest(
        status=QueryOrderStatus.OPEN,
        symbols=[SYMBOL]
    )
)

# Trading decision
if held or open_orders:
    print("Existing position or open order. Skipping.")

elif DRY_RUN:
    print(f"DRY RUN: Would BUY {QUANTITY} share of {SYMBOL}")

elif not clock.is_open:
    print("Market closed. No order submitted.")

elif float(account.cash) < 1000:
    print("Cash below $1,000 safety threshold. Skipping.")

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