import websocket
import stocksymbol
import ast
markets = ['ru', 'jp', 'it', 'gb', 'ch', 'cn', 'de', 'ca', 'us']
symbols_stock = []
api = stocksymbol.StockSymbol("e57d8559-253f-4d05-9545-7b83d637064a")

symbols_stock+=api.get_symbol_list("us")[:49]
print(symbols_stock)
def on_message(ws, message):
    print(message)
    print(ast.literal_eval(message)["data"][0]["p"], ast.literal_eval(message)["data"][0]["s"])

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    for i in symbols_stock:
        print('{"type":"subscribe","symbol":"'+i.split(".")[0]+'"}')
        ws.send('{"type":"subscribe","symbol":"'+i.split(".")[0]+'"}')

if __name__ == "__main__":
    ws = websocket.WebSocketApp("wss://ws.finnhub.io?token=ci9gas9r01qtqvvf1p00ci9gas9r01qtqvvf1p0g",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()

