import stocksymbol
import yfinance as yf
import pandas as pd
import datetime
import yliveticker
from coinmarketcapapi import CoinMarketCapAPI
from currency_converter import CurrencyConverter
from binance.client import Client
cl = Client()
print(cl.get_ticker(symbol="BTCUSDT"))
c = CurrencyConverter()
cmc= CoinMarketCapAPI("df54f7e7-f5a8-4e78-ab24-08fd9ffbfc7f")
#ticker=yf.Ticker("GAZP.ME=X")
print(yf.Ticker("GAZP.ME").info)
print(ticker.history(period="5y", interval="1mo").columns.values.tolist())
for index, row in ticker.history(period="5y", interval="1mo").reset_index().iterrows():

    print(pd.to_datetime(row["Date"]).strftime("%d-%m-%Y"), row['Close'])

print(ticker.info)
markets = ['ru', 'jp', 'it', 'gb', 'ch', 'cn', 'de', 'ca', 'us']
symbols_stock = []
api = stocksymbol.StockSymbol("e57d8559-253f-4d05-9545-7b83d637064a")
#for m in markets:
    #symbols_stock+=api.get_symbol_list(m, symbols_only=True)[:12]
print(symbols_stock)
dt=datetime.datetime.now()
client = Client()
def on_new_msg(ws, msg):
    print(msg)
print(c.currencies)
from alpha_vantage.foreignexchange import ForeignExchange
cc = ForeignExchange(key='T53JZJR2H40JFAQQ')
# There is no metadata in this call
data, _ = cc.get_currency_exchange_rate(from_currency='USD',to_currency='RUB')
print(data["5. Exchange Rate"])
yliveticker.YLiveTicker(on_ticker=on_new_msg, ticker_names=["GAZP.ME"])