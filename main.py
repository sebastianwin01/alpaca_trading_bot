import os
from alpaca.trading.client import TradingClient

client = TradingClient(
    api_key=os.environ["ALPACA_API_KEY"],
    secret_key=os.environ["ALPACA_SECRET_KEY"],
    paper=True
)

account = client.get_account()

print("Connected to Alpaca!")
print("Cash:", account.cash)
print("Buying power:", account.buying_power)
print("Portfolio value:", account.portfolio_value)
