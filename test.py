async_mode = None
from datetime import datetime, timedelta
import socketio
from flask import Flask, render_template
from flask_cors import CORS
from binance import ThreadedWebsocketManager
from binance.client import Client
from binance.enums import *
from coinmarketcapapi import CoinMarketCapAPI
import eventlet
import eventlet.wsgi
sio = socketio.Server(logger=True, engineio_logger=True,async_mode="threading", cors_allowed_origins = "*", always_connect=True)
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
CORS(app)
import timeit

cmc= CoinMarketCapAPI("df54f7e7-f5a8-4e78-ab24-08fd9ffbfc7f")
@sio.on('connect')
def connect(sid, environ):
    sio.enter_room(sid, "room_test")
    # IS EMITING. OK  <========================================================== #3
    sio.emit("connection", ["CONNECT"], room="room_test", namespace="/")


def cback(message):
    try:
        today = datetime.today()
        delta = timedelta(days=1)
        lookback = today-delta
        lookback.timestamp()
        #print(lookback)
        #print(message["k"])
        msg = client.get_historical_klines(symbol=message["s"], start_str=str(lookback), interval=KLINE_INTERVAL_1HOUR)
        #print(message)
        result = {message["s"]: []}
        for i in msg:
            date = datetime.fromtimestamp(i[0]/1000).strftime("%d/%m/%Y %H:%M:%S")
            result[message["s"]].append([date, i[1]])
            #with app.test_request_context("/"):
        sio.emit("my response", result)
        #a =main()
    except Exception as ex:
        print(message, ex)
    return 1

def setup():
    symbols = cmc.cryptocurrency_listings_latest().data
    print(symbols)
    output = {}
    l=0
    for s in symbols:
        try:
            print(len(symbols)-l)
            name = s["name"]
            price = s["quote"]["USD"]["price"]
            s = s["symbol"]
            symb = s+"USDT"
            coin_info =cmc.cryptocurrency_info(symbol=s).data[s][0]
            #name = coin_info["name"]
            icon = coin_info["logo"]
            today = datetime.today()
            delta = timedelta(days=365*5)
            lookback = today - delta
            lookback.timestamp()

            msg = client.get_historical_klines(symbol=symb, start_str=str(lookback),
                                               interval=KLINE_INTERVAL_1MONTH)
            #price = msg[len(msg)-1][1]
            prices = []
            for i in prices:
                date = datetime.fromtimestamp(i[0] / 1000).strftime("%d/%m/%Y %H:%M:%S")
                prices.append([date, i[1]])
            output[symb]={"logo": icon, "name": name, "current_price": price, "prices": prices}
        except:
            pass
        l+=1
    return output


setup()
if __name__ == '__main__':
    client = Client()
    info = client.get_exchange_info()
    # The binance websocket start in another thread <============================ #1
    bm = ThreadedWebsocketManager()
    thread = sio.start_background_task(bm.start)
    for c in info['symbols']:
        if c['quoteAsset'] == 'USDT' and c['status'] == "TRADING":
            symb = c["symbol"][:len(c["symbol"]) - 4]
            # print(symb)
            # print(cmc.cryptocurrency_info(symbol = symb).data)
            bm.start_kline_socket(symbol=c["symbol"], interval=KLINE_INTERVAL_1DAY, callback=cback)


    app.run(threaded = True)