import codecs
import decimal
import logging
import random
import uuid
from functools import wraps
from math import floor
from threading import Thread
from datetime import datetime, timedelta
from time import time
import flask_socketio
import pandas as pd
from flask_socketio import SocketIO, emit
from binance.client import Client
from binance import ThreadedWebsocketManager
from binance.enums import *
from coinmarketcapapi import CoinMarketCapAPI
from flask import Flask, request, jsonify, make_response, send_file
from flask_cors import  CORS
from sqlalchemy import insert, select, update, desc, delete, text
from werkzeug.utils import secure_filename

from database import conn, Session
import models
import jwt
import os
from werkzeug.security import generate_password_hash, check_password_hash
from paykassa.merchant import MerchantApi
from paykassa.dto import GenerateAddressRequest, GetPaymentUrlRequest, MakePaymentRequest
from paykassa.payment import PaymentApi
from paykassa.struct import System, Currency, CommissionPayer, TransactionPriority
import stocksymbol
import yfinance as yf
from yliveticker import YLiveTicker
from currency_converter import CurrencyConverter
from alpha_vantage.foreignexchange import ForeignExchange
from sqlalchemy.exc import SQLAlchemyError
import smtplib
from email.mime.text import MIMEText


cc = ForeignExchange(key='T53JZJR2H40JFAQQ')
converter = CurrencyConverter()

markets = ['ru', 'jp', 'it', 'gb', 'ch', 'cn', 'de', 'ca', 'us']
client_api = PaymentApi(24014, "K78myX14gLUUOoODJ6anqN4CiT9mGPbj")
passw = "gnLH9xPXJWCrYLsiuSGo7DOdYMJbGhLf"
client_merchant = MerchantApi("22645", passw)

session_sql = Session(autocommit = False)
cmc= CoinMarketCapAPI("df54f7e7-f5a8-4e78-ab24-08fd9ffbfc7f")
server_path = ""
app = Flask(__name__,  static_folder=os.path.join(server_path, 'client', 'dist', 'static'))
client = Client()
websocket = ThreadedWebsocketManager()
#eventlet.monkey_patch()
info = client.get_exchange_info()
CORS(app)
sio = SocketIO(app, async_mode = "threading", cors_allowed_origins="*")

#websocket.start(
sio.init_app(app, cors_allowed_origins="*")
app.config['SECRET_KEY'] = "secret_key_new_bin_test"
app.config["UPLOAD_DIR"]="user_files"
cryptocurrency = {}
stocks={}

@app.route('/')  # , methods=['GET']
def ping_pong():
    vuejs_html =  os.path.join(server_path, "client", "dist", "index.html")
    return send_file(vuejs_html)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return send_file(os.path.join(server_path, "client", "dist", "index.html"))

@sio.on("ping")
def ping():
    sio.emit("pong")
    print("pong")

@sio.event
def chat(req):
    print(req)
    sid=request.sid
    print(req["data"])
    for l in req["data"]:
        print(l)
        flask_socketio.join_room(l, sid)
        sio.emit("chat1", {"data": "yeah"}, to=l)
    sio.emit("chat1", {"data": "yeah"})
    print("chat")
    sio.emit("chat1", {"data": "yeah"})


@sio.on("del_ticket")
def del_room(req):
    emit("delete", {"room":req["data"]}, to=req["data"])
    flask_socketio.close_room(req["data"])

@sio.on("create_room")
def create_room(req):
    print(1)
    token = req["token"]
    name = req["data"]
    data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    id = str(uuid.uuid4())
    started=datetime.today()
    stmt = insert(models.Rooms).values(id = id, started = started, name= name)
    session_sql.execute(stmt)
    stmt2=insert(models.User_Rooms).values(admin = False, user = data, room = id)
    session_sql.execute(stmt2)
    session_sql.commit()
    room = session_sql.query(models.Rooms).filter_by(id = id).first()
    room=room.__dict__
    room_s={}
    for r in room.keys():
        if r!="_sa_instance_state":
            room_s[r]=room[r]
    room_s["started"]=room_s["started"].strftime('%d-%m-%Y')
    flask_socketio.join_room(id, request.sid)
    sio.emit("new_room", room_s, to = id)


@sio.on("new_msg")
def new_mes(req):
    try:
        print(req)
        token = req["token"]
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        if len(session_sql.query(models.User_Rooms).filter_by(user = data["public_id"], room = req["data"]["roomId"]).all()):
            flask_socketio.leave_room(req["data"]["roomId"], request.sid)
            flask_socketio.join_room(req["data"]["roomId"], request.sid)
            print("NEW MSG")
            last_id = session_sql.query(models.Messages._id).order_by("_id").all()
            last_id = last_id[len(last_id)-1][0]+1 if len(last_id)!=0 else 0
            stmt = insert(models.Messages).values(content = req['data']["content"], senderId = req["data"]["senderId"], timestamp = req["data"]["timestamp"], date=req["data"]["date"], roomId=req["data"]["roomId"])
            session_sql.execute(stmt)
            session_sql.commit()
            if req["data"]['files'] != None:
                for file in req["data"]["files"]:
                    name = file["name"]+'-'+str(uuid.uuid4())
                    path = os.path.join(app.config["UPLOAD_DIR"], "chat", name+"."+file["extension"])
                    with open(path, 'wb') as f:
                        f.write(file["blob"])
                    stmt = insert(models.Files).values(name = name, msg = last_id, blob = file["blob"], extension=file["extension"], size = file["size"], type = file["type"], localUrl=file["localUrl"], path = path)
                    session_sql.execute(stmt)
                    session_sql.commit()
            callback_ = {}
            callback_=session_sql.query(models.Messages).filter_by(_id = last_id).first().__dict__
            file_msg = session_sql.query(models.Files).filter_by(msg = last_id).all()
            cb=[]
            send={}
            for l in file_msg:
                h={}
                l=l.__dict__
                for i in l.keys():
                    if i!="_sa_instance_state":
                        h[i]=l[i]
                cb.append(h)
            send["files"]=file_msg
            for k in callback_.keys():
                if k!="_sa_instance_state":
                    send[k]=callback_[k]
            print(send)
            sio.emit("new_message_received", {"data": send, "roomId": req["data"]["roomId"]}, to=req["data"]["roomId"])
            print(req["data"]["roomId"] in flask_socketio.rooms(request.sid))
    except Exception as ex:
        print(ex)
        sio.emit("new_message_received", {"status": "error"})



    #print(content, timestamp, sender)

@sio.on('connect')
def test_connect():
    sio.emit('connection', {'data': 'Connected'})
    #flask_socketio.join_room("test_room")
    print("Client connected")
@sio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

def on_close():
    print("closed")
    symbols = session_sql.query(models.Objects.symbol).filter_by(type="stock").all()
    res = []
    for i in symbols:
        res.append(i[0])
    sio.start_background_task(YLiveTicker, **{"on_ticker": cback_stocks, "ticker_names": res, "on_close": on_close})

def cback(message):
    try:
        today = datetime.today()
        delta = timedelta(days=1)
        lookback = today-delta
        lookback.timestamp()
        #print(lookback)
        #print(message["k"])
        #print(message)
        data = message["k"]
        price = float("{:.2f}".format(float(data["c"])))
        change = client.get_ticker(symbol = message["s"])["priceChangePercent"]
        #stmt = update(models.Objects).filter_by(symbol = message["s"]).values(price = price, change = change)
        #session_sql.execute(stmt)
        #print(change, message["s"])
        stocks[message["s"]] = [price, change]
        result = {"symb": message["s"], "price": price, "change": change}
        #with app.test_request_context("/"):
        sio.emit("changeCrypto", result)
        #a =main()
    except Exception as ex:
        #print(message, ex)
        print(ex)
        pass
    return 1
    #print(1)
setup2 = False
setupped = False
setup3 = False
def setup_func():
    global cryptocurrency, stocks
    print("Setting up")
    symbols_stock = []
    api = stocksymbol.StockSymbol("e57d8559-253f-4d05-9545-7b83d637064a")
    for m in markets:
        symbols_stock += api.get_symbol_list(m, symbols_only=True)[:12]
    global setup2, setupped, setup3
    symbols_stock.remove("GOOGL")
    today = datetime.today()
    start = today - timedelta(days=365*5)
    #symbols = cmc.cryptocurrency_listings_latest().data
    symbols = []
    for c in info["symbols"]:
        if "USDT" in c["symbol"] and c["status"]=="TRADING":
            symbols.append(c["symbol"])
        symbols = symbols[:100]

    for s in symbols:
        websocket.start_kline_socket(symbol=s, interval=KLINE_INTERVAL_1DAY, callback=cback)
        if setup2:
            try:

                history = client.get_historical_klines(symbol=s, start_str=str(start), interval=KLINE_INTERVAL_1MONTH)
                ticker = client.get_ticker(symbol=s)
                change = ticker['priceChangePercent']
                data = cmc.cryptocurrency_info(symbol=s[:len(s) - 4]).data
                name = data[s[:len(s) - 4]][0]["name"]
                logo = data[s[:len(s) - 4]][0]["logo"]
                type = "symbol"
                price = history[len(history)-1][4]
                try:
                    stmt2 = insert(models.Objects).values(type="crypto", name=name, logo=logo, symbol=s, change=change, price=price)
                    cryptocurrency[s] = [price, change]
                    session_sql.execute(stmt2)
                    session_sql.commit()
                except:
                    cryptocurrency[s] = [price, change]
                    session_sql.rollback()

                counter = 0
                for hist in history:
                    date = datetime.fromtimestamp(hist[0] // 1000).strftime("%Y-%m-%d")
                    price = hist[4]
                    symbol = s
                    stmt = insert(models.History).values(type=type, price=price, timestamp=date, symbol=symbol,
                                                         counter=counter)
                    stmt3=delete(models.History).filter_by(counter = counter, symbol = symbol)
                    session_sql.execute(stmt3)
                    session_sql.execute(stmt)
                    session_sql.commit()
                    counter += 1
            except:
                continue

    if setup3:
        print(symbols_stock)
        for symb in symbols_stock:
            counter = 0
            ticker = yf.Ticker(symb)
            try:
                try:
                    print(symb)
                    name = ticker.info["shortName"]
                    current_price = ticker.info["currentPrice"]
                    previous = ticker.info["previousClose"]
                    rate = 1/yf.Ticker(ticker.info["currency"]+"=X").info["bid"]
                    price = current_price*rate

                    change = (current_price-previous)/100
                    stmt = insert(models.Objects).values(type = "stock", name = name, price = price, change = change, symbol = symb)
                    session_sql.execute(stmt)
                    stocks[symb] = [price, change]
                    session_sql.commit()
                except:
                    current_price = ticker.info["currentPrice"]
                    previous = ticker.info["previousClose"]
                    rate = 1/yf.Ticker(ticker.info["currency"]+"=X").info["bid"]
                    price = current_price * rate
                    print(current_price)
                    change = (current_price-previous)/100
                    stocks[symb] = [price, change]
                    stmt2 = update(models.Objects).filter_by(symbol=symb).values({"price": price, "change": change})
                    session_sql.execute(stmt2)
                    session_sql.commit()

                for index, row in ticker.history(period="5y", interval="1mo").reset_index().iterrows():
                    counter+=1
                    if len(session_sql.query(models.History.id).filter_by(counter = counter, symbol = symb).all())<1:
                        date = pd.to_datetime(row["Date"]).strftime("%d-%m-%Y")
                        price = row["Close"]
                        stmt = insert(models.History).values(type = "stock", symbol = symb, price = price, counter=counter, timestamp=date)
                        session_sql.execute(stmt)
                        session_sql.commit()
            except Exception as ex:
                print("exception", ex)
                continue
    sio.start_background_task(target=YLiveTicker, **{"on_ticker": cback_stocks, "ticker_names": symbols_stock, "on_close": on_close})






    print("Setup complete")



def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'X-Access-token' in request.headers:
            token = request.headers['X-Access-token']

        if not token:
            return jsonify({'message': 'a valid token is missing'})
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = session_sql.query(models.Users).filter_by(public_id=data['public_id']).first()
            if current_user is None:
                return jsonify({'message': 'Пользователь не найден! Требуется авторизация', 'exception': True, 'ex': True})

        except Exception as ex:
            print(ex)
            return jsonify({'message': 'token is invalid'})

        return f(*args, **kwargs)

    # current_user,
    return decorator




@app.route("/api/get_file_contract", methods = ["POST"])
@token_required
def get_file_contract():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    id = request.get_json()["id"]
    obj = session_sql.query(models.Contracts.path).filter_by(user = pub_id, id = id).first()
    if len(obj)>=1:
        return send_file(os.path.join(app.config["UPLOAD_DIR"], "contracts", obj[0]))

@app.route("/api/send_verify", methods=["POST"])
@token_required
def send_verify():
    data=request.files
    token = request.headers["X-Access-token"]
    print(data)
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    file = request.files.getlist("doc")
    file2 = request.files.getlist("face")
    last_id = session_sql.query(models.Verification.id).order_by(models.Verification.id.desc()).first()
    last_id = last_id[0] + 1 if last_id is not None else 1
    try:
        stmt2 = insert(models.Verification).values(phone=str(uuid.uuid4()), user = pub_id)
        session_sql.execute(stmt2)
    except:
        session_sql.rollback()
        return jsonify({"exception": True, "message": "Заявка на верификацию уже отправлена!"})
    types={"passport": "Паспорт", "international": "Загранпаспорт"}
    for f in file:
        print(f)
        postfix=str(uuid.uuid4())
        filename = secure_filename(f.filename)
        a = filename.split(".")
        path = os.path.join("user_files", "document", a[0] + postfix + "."+a[1])
        f.save(path)
        stmt = insert(models.VerifyFiles).values(filepath = path, ver_id=last_id)
        session_sql.execute(stmt)
        session_sql.commit()
    for f in file2:
        print(f)
        postfix = str(uuid.uuid4())
        filename = secure_filename(f.filename)
        a = filename.split(".")
        path = os.path.join("user_files", "faces", a[0] + postfix+"."+a[1])
        f.save(path)
        stmt = insert(models.VerifyFiles).values(filepath=path, ver_id=last_id)
        session_sql.execute(stmt)
        session_sql.commit()
    return jsonify(message=last_id)

@app.route("/api/get_all_users")
@token_required
def get_all_users():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        ret=session_sql.query(models.Users).all()
        result=[]
        for user in ret:
            res = {}
            user = user.__dict__
            for k in user.keys():
                if k!="_sa_instance_state":
                    res[k]=user[k]
            result.append(res)
        print(result)
        return jsonify(result)
    raise

@app.route("/api/verify", methods = ["POST"])
@token_required
def verify():
    data = request.get_json()
    data["user"]["phone"]=data["user"]["code"]+" "+data["user"]["phone"]
    del [data["user"]["code"]]
    stmt = update(models.Verification).values(data["user"]).filter_by(id=data["id"])
    session_sql.execute(stmt)
    session_sql.commit()
    return jsonify(message="Успешно")
@app.route("/api/get_file_verify", methods = ["POST"])
@token_required
def get_file_verify():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        return send_file(request.get_json()["data"])

@app.route("/api/verify_admin", methods = ["POST"])
@token_required
def verify_admin():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        data=request.get_json()
        for i in data.keys():
            id = session_sql.query(models.Verification).filter_by(user=i).first().id
            if data[i]==True:
                stmt = update(models.Users).filter_by(public_id=i).values({"verificated": True})

                stmt2 = delete(models.Verification).filter_by(id=id)
                stmt3=delete(models.VerifyFiles).filter_by(ver_id=id)
                try:
                    session_sql.execute(stmt)
                    session_sql.execute(stmt2)
                    session_sql.execute(stmt3)
                    session_sql.commit()
                except:
                    session_sql.rollback()
                    raise
            else:
                stmt2 = delete(models.Verification).filter_by(id=id)
                stmt3 = delete(models.VerifyFiles).filter_by(ver_id=id)
                try:
                    session_sql.execute(stmt2)
                    session_sql.execute(stmt3)
                    session_sql.commit()
                except:
                    session_sql.rollback()
                    raise
        return jsonify(message="Успешно")
    raise
@app.route("/api/get_verifies")
@token_required
def get_verifies():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        verifies = session_sql.query(models.Verification).all()
        s_f=[]
        for i in verifies:
            res={}
            a = i.__dict__
            for k in a.keys():
                if k != "_sa_instance_state":
                    res[k] = a[k]
            files = session_sql.query(models.VerifyFiles.filepath, models.VerifyFiles.name).filter_by(ver_id=res["id"]).all()
            files_dict = []
            for f in files:
                f_d={}
                f_d["name"]=f[1]
                f_d["filepath"]=f[0]
                files_dict.append(f_d)
            res["files"]=files_dict
            s_f.append(res)
            print(res)
        return jsonify(message=s_f)

@app.route("/api/get_custom", methods = ["POST"])
def get_custom():
    symbs=session_sql.query(models.Objects).filter_by(type=request.get_json()["type"]+'_custom').all()
    client_s=[]
    for i in symbs:
        i=i.__dict__
        res = {}
        print(i)
        for k in i.keys():
            if k != "_sa_instance_state":
                res[k] = i[k]
        client_s.append(res)
    return jsonify(client_s)

@app.route("/api/create_position", methods = ["POST", "OPTIONS"])
@token_required
def create_position():
    print(1)
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        data = request.get_json()
        data["data"]["change"]=0
        data["data"]["type"]=data["type"]+"_custom"
        data["data"]["symbol"]+="USDT" if data["type"]=="crypto" else data["data"]["symbol"]
        stmt = insert(models.Objects).values(data["data"])
        try:
            session_sql.execute(stmt)
            session_sql.commit()
            return jsonify({"message": "Успешно"})
        except:
            session_sql.rollback()
            raise

@app.route("/api/update_custom", methods=["POST"])
@token_required
def update_custom():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        data = request.get_json()
        for k in data:
            price_change = float(k["change_price"])
            price = float(k["price"])
            type = k["type_change"]
            if price_change!=price or type==1:
                symbol=k["symbol"]
                symb = session_sql.query(models.Objects).filter_by(symbol=symbol).first()
                current = symb.price
                result = {"symb": symbol}
                if type==0:
                    change = price_change-current
                    change = float("{:.2f}".format(float(change/current*100)))
                    stmt = update(models.Objects).filter_by(symbol=symbol).values({"price": price_change, "change": change})
                    result["change"]=change
                    result["price"]=price_change
                else:
                    change = current+current*(price_change/100)
                    stmt=update(models.Objects).filter_by(symbol=symbol).values({"price": change, "change": price_change})
                    result["change"] = price_change
                    result["price"] = change
                session_sql.execute(stmt)
                session_sql.commit()
                event = "changeCrypto" if symb.type=="crypto_custom" else "changeStock"
                print(event)
                sio.emit(event, result)
        return jsonify(message="Успешно")
    raise

@app.route("/api/pin_contract", methods=["POST"])
@token_required
def pin_contract():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        file = request.files.getlist("contract")
        for f in file:
            print(f)
            postfix = str(uuid.uuid4())
            filename = secure_filename(f.filename)
            a = filename.split(".")
            path = os.path.join("user_files", "contracts", a[0] + postfix + "." + a[1])
            f.save(path)
            today = datetime.today()
            today = today.strftime('%d-%m-%Y')
            stmt = insert(models.Contracts).values(path=a[0] + postfix + "." + a[1], date=today, name = "Договор")
            session_sql.execute(stmt)
            session_sql.commit()
        last_id = session_sql.query(models.Contracts.id).order_by(models.Contracts.id.desc()).first()
        last_id = len(file) if last_id[0] is None else last_id[0]
        ids = [last_id]
        for i in range(len(file)):
            ids.append(last_id-i)
            i-=1
        return jsonify(id = ids)

@app.route("/api/get_tickets_admin")
@token_required
def get_tickets_admin():
    tickets=session_sql.query(models.Rooms).all()
    ticks= []
    for tick in tickets:
        t = tick
        users = session_sql.query(models.User_Rooms.user).filter_by(room = t.id).all()
        if len(users)<2:
            user = session_sql.query(models.Users).filter_by(public_id=users[0][0]).first()
            ticks.append({"room_name": t.name, "date": t.started, "name": user.name, "second_name": user.second_name, "id": t.id, "counter": t.count, "email": user.email})
    return jsonify(message = ticks)

@app.route("/api/accept_ticket", methods=["POST"])
@token_required
def accept_ticket():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        id = request.get_json()["data"]
        stmt = insert(models.User_Rooms).values(user = pub_id, room = id, admin=True)
        session_sql.execute(stmt)
        session_sql.commit()
        return jsonify(message="Успешно")

@app.route("/api/contract_data", methods=["POST"])
@token_required
def contract_data():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()[0]:
        data = request.get_json()
        for i in data["id"]:
            stmt = update(models.Contracts).filter_by(id = i).values(user = data["user"])
            session_sql.execute(stmt)
        session_sql.commit()
        return jsonify(message="Успешно")

@app.route("/api/create_pay_request", methods = ["POST"])
@token_required
def create_pay_request():
    data = request.get_json()
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]

    valus = {
        "Bitcoin": client.get_ticker(symbol="BTCUSDT")["lastPrice"], "Ethereum": client.get_ticker(symbol="ETHUSDT")["lastPrice"],
               "Litecoin": client.get_ticker(symbol="ETHUSDT")["lastPrice"], "USDT TRC-20": 1,
               "USDT ERC-20": 1,
               "USDT BEP-20": 1,
               "Tron": client.get_ticker(symbol="TRXUSDT")["lastPrice"], "USD Coin ERC-20": client.get_ticker(symbol="USDCUSDT")["lastPrice"],
               "Bank card RUB": 1 / yf.Ticker("RUB=X").info["bid"],
               "Bank card USD":1
    }
    amount=float(valus[data["system"]])*float(data["amount"])
    tr=str(uuid.uuid4())[:8]
    bal = session_sql.query(models.Users).filter_by(public_id=pub_id).first()
    stmt2 = insert(models.PaymentRequests).values(public_id=pub_id, transaction = tr, address = data["address"], amount = data["amount"], system=data["system"])
    stmt = insert(models.Transactions).values(pub_id=tr, user=pub_id, date=datetime.today(), result=-1*float(amount),
                                              status="Обрабатывается", bal=bal.balance-amount)

    stmt3 = update(models.Users).filter_by(public_id = pub_id).values({"balance": bal.balance-amount})
    stmts = [stmt, stmt2, stmt3]
    for i in stmts:
        try:
            session_sql.execute(i)
        except:
            session_sql.rollback()
            raise
    session_sql.commit()
    return jsonify(message="Успешно")

@app.route("/api/set_transaction_status", methods = ["POST"])
@token_required
def set_transaction_status():
    data = request.get_json()
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    if session_sql.query(models.Users).filter_by(public_id=pub_id).first()[0].admin:
        if data["status"]=="Отклонено":
            stmt = update(models.Transactions).filter_by(pub_id=data["trans"]).values({"status": "Отклонено"})
            stmt2=delete(models.PaymentRequests).filter_by(transaction=data["trans"])
            try:
                session_sql.execute(stmt)
                session_sql.execute(stmt2)
                session_sql.commit()
            except:
                session_sql.rollback()
                raise
            return jsonify({"exception": False})
        systems = {"Bitcoin": [System.BITCOIN, Currency.BTC], "Ethereum": [System.ETHEREUM, Currency.ETH],
                   "Litecoin": [System.LITECOIN, Currency.LTC], "USDT TRC-20": [System.TRON_TRC20, Currency.USDT],
                   "USDT ERC-20": [System.ETHEREUM_ERC20, Currency.ETH],
                   "USDT BEP-20": [System.BINANCESMARTCHAIN_BEP20, Currency.USDT],
                   "Tron": [System.TRON, Currency.TRX], "USD Coin ERC-20": [System.ETHEREUM_ERC20, Currency.USDC],
                   "Bank card RUB": [System.BERTY, Currency.RUB],
                   "Bank card USD": [System.BERTY, Currency.USD],
                   }
        trans = session_sql.query(models.PaymentRequests).filter_by(transaction=data["trans"])
        pay_req = MakePaymentRequest().set_amount(str(trans.amount)).set_system(systems[trans.system][0]).set_currency(systems[trans.system][1])
        res = client_api.make_payment(pay_req)
        if res.has_error():
            raise
        stmt = update(models.Transactions).filter_by(pub_id=data["trans"]).values({"status": "Успешно"})
        stmt2 = delete(models.PaymentRequests).filter_by(transaction=data["trans"])
        try:
            session_sql.execute(stmt)
            session_sql.execute(stmt2)
            session_sql.commit()
        except:
            session_sql.rollback()
            raise
        return jsonify({"exception": False})

@app.route("/api/get_contracts")
@token_required
def get_contracts():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    ids = session_sql.query(models.Contracts.id, models.Contracts.name, models.Contracts.date).filter_by(user = pub_id).all()
    result=[]
    for id in ids:
        result.append({"id":id[0], "name": id[1], "date": id[2]})
    return make_response(result)

@app.route("/api/download_file", methods = ["POST"])
@token_required
def download_file():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    data = request.get_json()
    msg = session_sql.query(models.Files.msg).filter_by(name = data["name"], extension = data["extension"]).first()[0]
    room = session_sql.query(models.Messages.roomId).filter_by(_id=msg).first()[0]
    if len(session_sql.query(models.User_Rooms.id).filter_by(room = room, user=pub_id).all())>0:
        return send_file(os.path.join("user_files", "chat", data["name"]+"."+data["extension"]), as_attachment=True)
    else:
        return jsonify(message = "Нет доступа к этому файлу.")

@app.route("/api/change_password", methods = ["POST"])
@token_required
def change_password():
    token = request.headers["X-Access-token"]
    data = request.get_json()
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    user = session_sql.query(models.Users).filter_by(public_id = pub_id).first()
    if check_password_hash(user.password, data["old"]):
        print(generate_password_hash(data["new"]))
        stmt = update(models.Users).filter_by(public_id = pub_id).values({models.Users.password: generate_password_hash(data["new"])})
        session_sql.execute(stmt)
        session_sql.commit()
        return jsonify({"status": "success", "message": "Успешно!"})
    else:
        return jsonify({"status": "error", "message": "Введен неверный пароль"})

@app.route("/api/get_messages", methods = ["POST"])
@token_required
def get_messages():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    room = request.get_json()["room"]
    msgs = session_sql.query(models.Messages).filter_by(roomId = room).all()
    result=[]
    #msgs = dict(zip(msgs.keys(), msgs))
    for m in msgs:
        res = {}
        a=m.__dict__
        for k in a.keys():
            if k!="_sa_instance_state":
                res[k] = m.__dict__[k]
        res["disableReactions"]=True
        res["disableActions"]=True


        user = session_sql.query(models.Users.name, models.Users.second_name).filter_by(
            public_id=res["senderId"]).first()
        res["username"] = user[0] + user[1]
        result.append(res)
    print(msgs)
    for msg in result:
        files = session_sql.query(models.Files).filter_by(msg = msg["_id"]).all()
        h=[]
        for f in files:
            res={}
            a=f.__dict__
            for k in a.keys():
                if k!="_sa_instance_state":
                    res[k]=a[k]
            res["blob"]=str(res["blob"])
            h.append(res)
        msg["files"]=list(files)
    return jsonify(message=result)

@app.route("/api/admin_change_user", methods=["POST"])
@token_required
def admin_change_user():
    try:
        token = request.headers["X-Access-token"]
        data = request.get_json()["data"]
        pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
        user = session_sql.query(models.Users.admin).filter_by(public_id=pub_id).first()
        if user:
            restricted_keys = ["id",  "public_id", "password", "second_password", '_sa_instance_state']
            for i in data:
                voc = {}
                for k in i.keys():
                    if k not in restricted_keys:
                        voc[k]=i[k]
                stmt = update(models.Users).values(voc).filter_by(public_id = i["public_id"])
                session_sql.execute(stmt)
            session_sql.commit()
            return jsonify({"exception": False})
    except Exception as ex:
        print(ex)
        session_sql.rollback()
        raise

@app.route("/api/change_user", methods = ["POST"])
@token_required
def change_user():
    try:
        token = request.headers["X-Access-token"]
        data = request.get_json()["data"]
        pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
        restricted_keys = ["balance", "id", "password", "public_id", "referl", "second_password", "second_name", "phone", '_sa_instance_state', "banned", "verificated", "admin"]
        voc={}
        for i in data.keys():
            if i not in restricted_keys:
                if i=="code":
                    voc["phone"]=data[i]+" "+data["phone"]
                else:
                    voc[i]=data[i]
        print(voc)
        stmt = update(models.Users).filter_by(public_id = pub_id).values(voc)
        session_sql.execute(stmt)
        session_sql.commit()
        return jsonify({"message": "success"})
    except Exception as ex:
        print(str(ex))
        session_sql.rollback()
        if "users.phone" in str(ex):
            return jsonify({"ex": True, "message": "Такой телефон уже зарегестрирован!"})
        elif "users.email" in str(ex):
            return jsonify({"ex": True, "message": "Такой E-mail уже зарегестрирован!"})
        else:
            return jsonify({"ex": True, "message": "Произошла ошибка на сервере. Попробуйте позже"})

@app.route("/api/register",  methods=['POST'])
def register():
    data = request.get_json()
    user = data["user"]

    #stay_long = request["remember"]
    try:
        stmt = insert(models.Users).values(email = user["email"],
                                           phone = user["phone"],
                                           referl = user["referal"],
                                           public_id = str(uuid.uuid4()),
                                           country = user["country"],
                                           password = generate_password_hash(user["password"]))
        session_sql.execute(stmt)
        session_sql.commit()
        return jsonify({"message": "Успешно"})
    except Exception as ex:
        session_sql.rollback()
        ex = str(ex)
        print(ex)
        exception = ""
        if "users.email" in ex :
            exception+="Такая почта уже зарегистрирована"
        if "users.phone" in ex:
            exception+="Такой телефон уже зарегистрирован\n"
        return jsonify({"message": "Exception", "exception": exception})

@app.route("/api/get_deals")
@token_required
def get_deals():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    try:
        deals = session_sql.query(models.Deals).filter_by(user = pub_id).all()
        print(deals)
        if len(deals)==0:
            return jsonify(message = None)
        else:
            result = []
            for deal in deals:
                symbol = deal.symbol
                sum = deal.sum
                course = float("{:.2f}".format(float(deal.course)))
                print(course)
                price = session_sql.query(models.Objects.price, models.Objects.logo).filter_by(symbol = symbol).first()
                history = []
                hist = session_sql.query(models.History.price, models.History.timestamp).filter_by(symbol=symbol).order_by(
                    models.History.counter).all()
                for i in hist:
                    history.append({"time": i[1], "value": i[0]})
                get = "{:.2f}".format(sum/course*float("{:.2f}".format(float(price[0]))))
                get = float(get)
                sum = "{:.2f}".format(sum)
                sum = float(sum)
                print(get)

                color = "red" if get<sum else "green"
                result.append({"symbol": symbol, "sum": sum, "course": course, "price": float("{:.2f}".format(float(price[0]))), "logo": price[1], "history": history, "color": color, "get": get, "id": deal.id, "type": deal.type})
            return jsonify(result)
    except Exception as ex:
        print(ex)
        raise

@app.route("/api/get_pay_url", methods = ["POST"])
@token_required
def get_pay_url():
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    data = request.get_json()
    amount = data["amount"]
    system = data["system"]
    orders = session_sql.query(models.Orders.id).order_by(models.Orders.id).all()
    last_id = orders[len(orders)-1][0]+1 if len(orders)>0 else 1
    systems = {"Bitcoin": [System.BITCOIN, Currency.BTC], "Ethereum": [System.ETHEREUM, Currency.ETH],
               "Litecoin": [System.LITECOIN, Currency.LTC], "USDT TRC-20": [System.TRON_TRC20, Currency.USDT],
               "USDT ERC-20": [System.ETHEREUM_ERC20, Currency.ETH], "USDT BEP-20": [System.BINANCESMARTCHAIN_BEP20, Currency.USDT],
               "Tron": [System.TRON, Currency.TRX], "USD Coin ERC-20": [System.ETHEREUM_ERC20, Currency.USDC]}
    req = GetPaymentUrlRequest().set_order_id(str(last_id)).set_system(systems[system][0]).set_currency(systems[system][1]).set_amount(amount).set_paid_commission(CommissionPayer.CLIENT).set_test(True)
    get = client_merchant.get_payment_url(req)
    url = get.get_url()
    stmt = insert(models.Orders).values(user = pub_id, system = system, amount = amount)
    session_sql.execute(stmt)
    session_sql.commit()
    return jsonify(message = url)

@app.route("/api/change_pass_email", methods=["POST"])
def change_pass_email():
    data = request.get_json()
    user = session_sql.query(models.Users.email).filter_by(email = data["email"]).first()
    if len(user)==0:
        return jsonify({"exception": True, "message": "E-mail не найден!"})
    print(data["pass"])
    while True:
        uid = ''.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
        if len(session_sql.query(models.ChangePassRequests.id).filter_by(code = uid).all())==0:

            msg = MIMEText("Код для восстановления пароля: "+uid)
            msg["To"]=data["email"]
            msg["From"]='Служба поддержки'
            msg["Subject"]="Восстановление пароля"
            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.ehlo()
            s.login('newbinancetest@gmail.com', "pyznbdytqydrjkfe")
            s.sendmail('newbinancetest@gmail.com', [data["email"]], msg.as_string())
            s.quit()

            uid_hash = generate_password_hash(uid)
            stmt1 = delete(models.ChangePassRequests).filter_by(email=data["email"])
            session_sql.execute(stmt1)
            stmt2 = insert(models.ChangePassRequests).values(email = data["email"], passw = generate_password_hash(data["pass"]), code=uid_hash)
            session_sql.execute(stmt2)
            session_sql.commit()
            break
        else:
            continue
    return jsonify(message="Успешно")

@app.route("/api/check_code", methods=["POST"])
def check_code():
    data = request.get_json()
    hash = session_sql.query(models.ChangePassRequests.code, models.ChangePassRequests.passw).filter_by(email = data["email"]).first()
    if check_password_hash(hash[0], data["code"]):
        print(hash[1])
        stmt = update(models.Users).values({"password": hash[1]}).filter_by(email = data['email'])
        session_sql.execute(stmt)
        session_sql.commit()
        return jsonify({"message": "Успешно"})
    else:
        return jsonify({"exception": True, "message": "Введен неверный код!"})
@app.route("/api/login", methods = ["POST"])
def login():
    print(session_sql)
    data = request.get_json()
    user = session_sql.query(models.Users).filter_by(email=data['email']).first()
    if user is None:
        return jsonify({'message': 'Неверный E-mail или пароль'})
    else:
        if check_password_hash(user.password, data["password"]):
            time = 24*60*365 if data["stay_long"] == True else 45
            token = jwt.encode(
                {'public_id': str(user.public_id), 'exp': datetime.utcnow() + timedelta(minutes=time),
                 "type": "access"},
                app.config['SECRET_KEY'], "HS256")
            refresh = jwt.encode(
                {'public_id': str(user.public_id), 'exp': datetime.utcnow() + timedelta(hours=3),
                 "type": "refresh"},
                app.config['SECRET_KEY'], "HS256")
            phone = user.phone.split(" ")
            print(user.second_password is None)
            if (user.second_password is None)==True:
                a = user.__dict__
                send = {}
                for k in a.keys():
                    if k!="_sa_instance_state":
                        send[k]=a[k]
                send["password"] = "NaN"
                send["second_password"] = ""
                send["accessToken"]=token
                send["refreshToken"]=refresh
                return jsonify(send)
            else:
                return jsonify({"secondPass": True})
        else:
            return jsonify({'message': 'Неверный E-mail или пароль'})

@app.route("/api/check_second_pass", methods=["POST"])
def check_second_pass():

    data = request.get_json()
    time = 24 * 60 * 365 if data["stay_long"] == True else 45
    user = session_sql.query(models.Users).filter_by(email=data["email"]).first()
    token = jwt.encode(
        {'public_id': str(user.public_id), 'exp': datetime.utcnow() + timedelta(minutes=time),
         "type": "access"},
        app.config['SECRET_KEY'], "HS256")
    refresh = jwt.encode(
        {'public_id': str(user.public_id), 'exp': datetime.utcnow() + timedelta(hours=3),
         "type": "refresh"},
        app.config['SECRET_KEY'], "HS256")
    second_pass = session_sql.query(models.Users.second_password).filter_by(email = data["email"]).first()[0]
    if check_password_hash(second_pass, data["pass"]):
        a= user.__dict__
        send={}
        for k in a.keys():
            if k!="_sa_instance_state":
                send[k]=a[k]
        send["password"] = "NaN"
        send["second_password"] = ""
        send["accessToken"] = token
        send["refreshToken"] = refresh
        return jsonify(send)
    else:
        return jsonify({"exception": True, "message": "Введен неверный второй пароль"})



@app.route('/api/get_transactions')
@token_required
def get_transactions():
    token = None
    if 'X-Access-token' in request.headers:
        token = request.headers['X-Access-token']

    if not token:
        return jsonify({'message': 'a valid token is missing'})
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        current_user = session_sql.query(models.Users).filter_by(public_id=data['public_id']).first()
        if current_user is None:
            return jsonify({'message': 'Пользователь не найден! Требуется авторизация'})
        transactions = session_sql.query(models.Transactions).filter_by(user = data["public_id"]).order_by(models.Transactions.id.desc()).all()
        out = []
        for i in transactions:
            if i.result>0:
                sign = "+"
                type = "Пополнение баланса"
                sep = " "
            else:
                sign = "-"
                type = "Вывод средств"
                sep = sign
            result = {"type": type, 'sign': sign, 'sum': str(i.result).split(sep)[len(str(i.result).split(sep))-1],
                      'date': i.date, "id": i.pub_id, "balance": i.bal, "status": i.status}
            out.append(result)
        return jsonify(out)
    except Exception as ex:
        print(ex)
@app.route("/api/get_symbols_crypto")
#@token_required
def get_symbols():
    query = text("SELECT * FROM 'stocks-and-coins' WHERE type = :type")
    objects = session_sql.query(models.Objects).from_statement(query).params(type ='crypto').all()
    object2=session_sql.query(models.Objects).from_statement(query).params(type="crypto_custom").all()
    result = []
    for l in objects:


        history = []
        hist = session_sql.query(models.History.price, models.History.timestamp).filter_by(symbol = l.symbol).order_by(models.History.counter).all()
        for i in hist:
            history.append({"time": i[1], "value": i[0]})
        try:
            price = float("{:.2f}".format(float(cryptocurrency[l.symbol][0])))
            change = float("{:.2f}".format(float(cryptocurrency[l.symbol][1])))
        except Exception as ex:
            print(ex)
            continue
        name = l.name
        logo = l.logo
        voc={"symbol": l.symbol,"price": price, "change": change, "name": name, "logo": logo, "history": history}
        result.append(voc)
    for l2 in object2:
        voc = {"symbol": l2.symbol, "price": l2.price, "change": l2.change, "name": l2.name, "logo": None, "history": None}
        result.append(voc)
    return jsonify(message = result)

def cback_stocks(ws, msg):
    symb = msg["id"]
    change = msg["changePercent"]
    price = float("{:.2f}".format(float(msg["price"])))
    tick = yf.Ticker(symb)
    currency = tick.info["currency"]
    rate = 1 / yf.Ticker(currency + "=X").info["bid"]
    price = price * rate
    if symb in stocks.keys():
        stocks[symb]=[price, change]
        sio.emit("changeStock", {"symb": symb, "change": change, "price": price})

@app.route("/api/get_stocks")
def get_stocks():
    query = text("SELECT * FROM 'stocks-and-coins' WHERE type = :type")
    objects = session_sql.query(models.Objects).from_statement(query).params(type='stock').all()
    object2 = session_sql.query(models.Objects).from_statement(query).params(type='stock_custom').all()
    result = []
    for l in objects:
        history = []
        hist = session_sql.query(models.History.price, models.History.timestamp).filter_by(symbol=l.symbol).order_by(
            models.History.counter).all()
        try:
            obj = stocks[l.symbol]
            price = obj[0]
            change=obj[1]
        except:
            continue
        for i in hist:
            history.append({"time": i[1], "value": i[0]})

        name = l.name
        voc = {"symbol": l.symbol, "price": float("{:.2f}".format(float(price))), "change": change, "name": name, "history": history}
        result.append(voc)
    for l2 in object2:
        voc = {"symbol": l2.symbol, "price": float("{:.2f}".format(float(l2.price))), "change": l2.change, "name": l2.name,
               "history": None}
        result.append(voc)
    return jsonify(message=result)



@app.route("/api/buy_crypto", methods=['POST'])
@token_required
def buy_crypto():
    data = request.get_json()
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    user = session_sql.query(models.Users).filter_by(public_id = pub_id).first()
    amount = float(data["sum"])/float(data["course"])
    print(amount)
    withdraw = float(data['course'])*amount
    print(withdraw)
    if user.balance<float(data["sum"]):
        return jsonify({"exception": True, "message": "Недостаточно средств на счету"})

    stmt = insert(models.Deals).values(user = pub_id, symbol = data["symbol"], type = "crypto", sum = withdraw, course = float(data["course"]))

    stmt2 = update(models.Users).filter_by(public_id=pub_id).values(balance = user.balance-withdraw)
    try:
        res = session_sql.execute(stmt)
        #print(res.keys())
        session_sql.commit()
    except:
        session_sql.rollback()
        return jsonify({"exception": True, "message": "Произошла ошибка на сервере. Попробуйте позже"})
    try:
        session_sql.execute(stmt2)
        session_sql.commit()
        return jsonify({"exception": False, "message": "Успешно"})
    except:
        session_sql.rollback()
        return jsonify({"exception": True, "message": "Произошла ошибка на сервере. Попробуйте позже"})


@app.route("/api/buy_stock", methods=['POST'])
@token_required
def buy_stock():
    data = request.get_json()
    print(data)
    token = request.headers["X-Access-token"]
    pub_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    user = session_sql.query(models.Users).filter_by(public_id = pub_id).first()
    amount = floor(float(data["sum"])/float("{:.2f}".format(float(data["course"]))))

    withdraw = float(data['course'])*amount
    print(withdraw)
    if user.balance<float(data["sum"]):
        return jsonify({"exception": True, "message": "Недостаточно средств на счету"})

    stmt = insert(models.Deals).values(user = pub_id, symbol = data["symbol"], type = "stock", sum = withdraw, course = float(data["course"]))

    stmt2 = update(models.Users).filter_by(public_id=pub_id).values(balance = user.balance-withdraw)
    try:
        res = session_sql.execute(stmt)
        #print(res.keys())
        session_sql.commit()
    except:
        session_sql.rollback()
        return jsonify({"exception": True, "message": "Произошла ошибка на сервере. Попробуйте позже"})
    try:
        session_sql.execute(stmt2)
        session_sql.commit()
        return jsonify({"exception": False, "message": "Успешно"})
    except:
        session_sql.rollback()
        return jsonify({"exception": True, "message": "Произошла ошибка на сервере. Попробуйте позже"})

@app.route("/api/get_user")
@token_required
def get_user():
    token = request.headers["X-Access-token"]
    public_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    user = session_sql.query(models.Users).filter_by(public_id=public_id).first()
    ret = {}
    res = user.__dict__
    for i in res.keys():
        if i!="_sa_instance_state":
            ret[i]=res[i]
    res["password"]="NaN"
    res["second_password"]=True if user.second_password is not None else False
    return jsonify({"user": ret})

def add_transaction(sum, token):
    id = str(uuid.uuid4())
    token = None
    args = request.get_json()
    if 'X-Access-token' in request.headers:
        token = token

    if not token:
        return jsonify({'message': 'a valid token is missing'})
    try:

        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])

        stmt = insert(models.Transactions).values(user = data["public_id"], result = float(args['sum']), pub_id = id, date = datetime.today())
        session_sql.execute(stmt)
        session_sql.commit()
    except Exception as ex:
        session_sql.rollback()
        print(ex)

@app.route("/api/create_ticket", methods = ["POST"])
@token_required
def create_ticket():
    token = request.headers["X-Access-token"]
    public_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    args = request.get_json()
    name = args["name"]
    started = datetime.now()
    stmt = insert(models.Rooms).values(name = name, started = started, closed = False, id=str(uuid.uuid4()), user = public_id)
    session_sql.execute(stmt)
    session_sql.commit()
    return jsonify(message="Успешно")

@app.route("/api/set_second_pass", methods=["POST"])
@token_required
def set_second_pass():
    data=request.get_json()["pass"]
    hash_pass = generate_password_hash(data)
    token = request.headers["X-Access-token"]
    public_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    stmt = update(models.Users).filter_by(public_id=public_id).values({"second_password": hash_pass})
    session_sql.execute(stmt)
    session_sql.commit()
    return jsonify(message = "success")

@app.route("/api/get_tickets", methods=["POST"])
@token_required
def get_tickets():
    token = request.headers["X-Access-token"]
    public_id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["public_id"]
    admin = request.get_json()["admin"]
    result = []
    rooms = session_sql.query(models.User_Rooms.room).filter_by(user = public_id, admin=admin).all()
    for i in rooms:
        room = session_sql.query(models.Rooms).filter_by(id = i[0]).first()
        room_s = {}
        for r in room.__dict__.keys():
            if r!="_sa_instance_state":
                room_s[r]= room.__dict__[r]
        room_s["admin"]=session_sql.query(models.User_Rooms.admin).filter_by(room=room_s["id"], user = public_id).first()[0]
        result.append(room_s)
    print(rooms)
    print(result)
    return make_response(result)

@app.route("/api/close_deal", methods = ["POST"])
@token_required
def close_deal():
    args = request.get_json()
    token = request.headers["X-Access-token"]
    data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    public_id = data["public_id"]
    id = args["id"]
    sum = args['course']
    user = session_sql.query(models.Users).filter_by(public_id = public_id).first()
    stmt1 = delete(models.Deals).filter_by(id = id)
    stmt2 = update(models.Users).filter_by(public_id=public_id).values(balance = user.balance+sum)
    try:
        session_sql.execute(stmt1)
        session_sql.commit()
    except:
        session_sql.rollback()
        raise
    try:
        session_sql.execute(stmt2)
        session_sql.commit()
    except:
        session_sql.rollback()
        raise
    return jsonify(message="Успешно")

@app.route("/api/deposit")
@token_required
def deposit():
    token = request.headers["X-Access-token"]
    data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    public_id = data["public_id"]
    args = request.get_json()
    currencies = {"TRC20": [Currency.USDT, System.TRON_TRC20],
                  "BTC": [Currency.BTC, System.BITCOIN],
                  "ETH": [Currency.ETH, System.ETHEREUM],
                  "LTC": [Currency.LTC, System.LITECOIN],
                  "ERC-20": [Currency.USDT, System.ETHEREUM_ERC20],
                  "TRX": [Currency.TRX, System.TRON]}
    user = session_sql.query(models.Users).filter_by(public_id =public_id).first()
    request1 = GetPaymentUrlRequest() \
        .set_amount(args["amount"]) \
        .set_currency(currencies[args["currency"]][0]) \
        .set_system(currencies[args["currency"]][1]) \
        .set_comment("Пополнение баланса для пользователя"+public_id) \
        .set_paid_commission(CommissionPayer.CLIENT)

    response = client_merchant.get_payment_url(request1)
    client_merchant.check_payment()
    if not response.has_error():
        return jsonify({"message": response.get_url()})
    else:
        return jsonify({'error': response.get_message()})



#launched = False
#if __name__ == "__main__" and not launched:
if __name__=="__main__":
    sio.start_background_task(websocket.start)

    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)
    setup_func()
    launched=True
    sio.run(app,  use_reloader=False, allow_unsafe_werkzeug=True, debug=True, log_output=False)