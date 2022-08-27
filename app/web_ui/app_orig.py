# -*- coding: utf-8 -*-
import logging
import threading
import time
from ftxtool import InteractiveParser, interactive_call
from utils.colorprint import message_que
from flask import Flask, render_template, request, flash, Markup, jsonify
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField, BooleanField, PasswordField, IntegerField, TextField, \
    FormField, SelectField, FieldList
from wtforms.validators import DataRequired, Length
from wtforms.fields import *
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask import Response
from datetime import datetime
from time import sleep
from flaskthreads import AppContextThread
from flask import g
from flask_socketio import SocketIO, emit
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
MessageQue = message_que
app = Flask(__name__)
app.secret_key = 'dev'
app.config['BOOTSTRAP_BOOTSWATCH_THEME'] = 'slate'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['BOOTSTRAP_BTN_STYLE'] = 'primary'
app.config['BOOTSTRAP_BTN_SIZE'] = 'sm'
app.config['BOOTSTRAP_TABLE_VIEW_TITLE'] = 'Read'
app.config['BOOTSTRAP_TABLE_EDIT_TITLE'] = 'Update'
app.config['BOOTSTRAP_TABLE_DELETE_TITLE'] = 'Remove'
app.config['BOOTSTRAP_TABLE_NEW_TITLE'] = 'Create'

socketio = SocketIO(app)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
threadarray = []

#demo msgs
demo_msgs = [
    "[$]PNL %: -2.784912392696565/Target %: 0.5/Target Stop: -1.5, PNL USD: -2.487167661600001",
    "[$] Account Value: 5.672779793083521 Collateral: 5.995609793083521 Free Collateral: 1.1070519599897939 Wins: 7 Losses: 0",
    "[d]: Processsing THETA-0625",
    " [🔻] Negative PNL -2.487167661600001 on position THETA-0625",
    "[▶] Instrument: THETA-0625, Side: buy, Size: 10.2 Cost: 89.30865, Entry: 8.75575, Open: 9.292714705882354 Liq: 8.465215214207499, BreakEven: 9.618429411764707, PNL: -8.79933, UPNL: 0.0, Collateral: 4.4654325",
    "[$]PNL %: -2.784912392696565/Target %: 0.5/Target Stop: -1.5, PNL USD: -2.487167661600001",
    "[$] Account Value: 5.672779793083521 Collateral: 5.995609793083521 Free Collateral: 1.1070519599897939 Wins: 7 Losses: 0",
    "[d]: Processsing THETA-0625",
    " [🔻] Negative PNL -2.487167661600001 on position THETA-0625",
]

@dataclass
class LogRecord(db.Model):
    id: int
    msg: str

    id = db.Column('msg_id', db.Integer, primary_key = True)
    msg = db.Column(db.String(200))



class FtxOptions(FlaskForm):
    """An example form that contains all the supported bootstrap style form fields."""
    monitor = BooleanField(default=True, description="Start the account monitor. See current status.")
    subaccount = StringField(description="Subaccount to connect to. None for mainaccount.", default='bot_test')
    symbol = StringField(description="symbol")
    symbol_monitor = StringField(description="binance pair - string - BTCUSDT")
    contract_size = StringField(description="for TA trading, how much (ie BTC) should we buy (like .01)")
    monitor_only = BooleanField(default=False)
    verbose = BooleanField(description="Verbose mode.")
    portfolio = BooleanField(description="Get current balances")
    ws_signals = BooleanField(default=False, description="enable ws sockets")
    ws_uri = StringField(default="ws://localhost:8000", description="where to put em yo")
    reenter = BooleanField(default=False, description="Re enter position before it closes if price hits entry again.")
    data_source = SelectField(choices=['binance'], description="Exchange where the signals were aggravated.")
    exclude_markets = SelectField(choices=['binance'], description="markets to say lol nah to")
    buy = StringField(description="Execute a buy order: --buy <limit> <ETH-PERP> <0.5> 2898.89 ")
    sell = StringField(description="Execute a sell order --sell <market> <BTC-USD> <0.1> ")
    cancel = StringField(description="Cancel this order id.")
    auto_trader = BooleanField(description="Use AutoTrader")
    disable_stop_loss = BooleanField(description="Do not use stop losses.")
    balance_arbitrage = BooleanField(description='use oscillation arb', default=False)
    long_symbols = StringField(description='long symbols to oscillate', default=None)
    short_symbols = StringField(description='short symbols to oscillate', default=None)
    min_spread = DecimalField(description='min target spread', default=0.0)
    stop_loss_pct = DecimalField(default=1)
    take_profit_pct = DecimalField(
        description="Percentage to take profitat, represented as a floating point number, 0.2 would be 20 percent",
        default=5.0)
    use_trailing_stop = BooleanField(
        description="Use Trailing Stops. Not sure why you would not to, but the option is here!", default=True)
    ts_offset = DecimalField(
        description="Trailing stop offset, represented as a floating point number, percentage of pnl.", default=0.005)
    order_type = SelectField(choices=['limit', 'market'], description="Take profit order type.", default='market')
    reopen = SelectField(choices=['increment', 'market', False], default='market',
                         description="Method to use to reopen positions. Market just sends a limit or market order. Increment splits size into several smaller orders according to standard deviation")
    close = SelectField(choices=['increment', 'market', False], default='market',
                         description="Method to use to reopen positions. Market just sends a limit or market order. Increment splits size into several smaller orders according to standard deviation")
    increment_period = SelectField(choices=[15, 60, 300, 900, 3600, 14400, 86400], default=300,
                                   description="Period (in seconds) to spread limit order over when rebuilding position using increment mode")
    num_orders = IntegerField(default=4, description="Number of open orders to reopen position in increments")
    position_step_size = DecimalField(default=0.02,
                                     description="Percentage to spread limit orders apart represented as  floating point number.")
    save = SubmitField()


clients = []


@socketio.on('my event')
def test_message(message):
    emit('my response', {'data': message['data']})

@socketio.on('my broadcast event')
def test_message(message):
    emit('my response', {'data': message['data']}, broadcast=True)

@socketio.on('connect')
def test_connect():
    clients.append(request.sid)
    print('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')
    clients.remove(request.sid)

def send_message(client_id, data):
    socketio.emit('output', data, room=client_id)
    print('sending message "{}" to client "{}".'.format(data, client_id))

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/status')
def status():
    return render_template('status.html')



@app.route("/time/")
def time():
    def streamer():
        while True:
            yield "<div>{}</div>".format(datetime.now())
            sleep(1)
    return Response(streamer())


@app.route('/message_popper')
def message_popper():
    t = AppContextThread(target=pop_msgs)
    t.start()
    return 'ok'

def pop_msgs():
    while True:
        try:
            poppedmsg = message_que.get()
            if not poppedmsg:
                for client in clients:
                    send_message(client, {'botmsg': poppedmsg})
                sleep(0.1)
        except:
            pass

@app.route('/startbot')
def startbot():
    opts = InteractiveParser
    ftxoptions = FtxOptions()
    opts.monitor = ftxoptions.monitor
    opts.subaccount = ftxoptions.subaccount.data
    opts.verbose = ftxoptions.verbose
    opts.show_tickers = False
    opts.use_strategy = False
    opts.balance_arbitrage = False
    opts.use_strategy = False
    opts.order_type = 'limit'
    opts.symbol = ftxoptions.symbol
    opts.symbol_monitor = ftxoptions.symbol_monitor
    opts.contract_size = ftxoptions.contract_size
    # auto trader opts
    opts.auto_trader = ftxoptions.auto_trader
    opts.monitor_only = ftxoptions.monitor_only
    opts.disable_stop_loss = ftxoptions.disable_stop_loss
    opts.stop_loss_pct = 0.5
    opts.take_profit_pct = ftxoptions.take_profit_pct
    opts.use_trailing_stop = ftxoptions.use_trailing_stop
    opts.ts_offset = ftxoptions.ts_offset
    opts.reopen_method = ftxoptions.reopen
    opts.close_method = ftxoptions.close
    opts.increment_period = ftxoptions.increment_period
    opts.num_open_orders = ftxoptions.num_orders
    opts.position_step_size = ftxoptions.position_step_size
    opts.enable_ws = ftxoptions.ws_signals
    opts.ws_uri = ftxoptions.ws_uri.data
    opts.reenter = ftxoptions.reenter
    opts.data_source = ftxoptions.data_source
    opts.exclude_markets = ftxoptions.exclude_markets
    interactive_call(opts)
    return render_template('status.html')

@app.route('/config', methods=['GET', 'POST'])
def config():
    return render_template('config.html', ftxoptions=FtxOptions())

class MultiUserInterface:
    def __init__(self):
        print('MultiThread Bot')
        self.current = {}
        self.traders = []
        self.started = False

    def start_trading(self, args, user_id='demo_001'):
        try:

            instance = interactive_call(_args=args)
            print(f'Starting scraper id: {user_id}')
            t = threading.Thread(target=interactive_call, args=(args,))
            t.start()
            self.traders.append(instance)
            sleep(5)

        except Exception as s:
            print(repr(s))
            print(str(s))
            logging.debug('Error starting scraper:', s)

    def stop_trading(self, strategy):
        _id = strategy['id']
        print(f'Stopping scraper id: {_id}')
        for trader in self.traders:
            if trader.FtxClientConnection._id == _id:
                # trader.FtxClientConnection.stop() # TODO: kill thread
                self.traders.remove(trader)
                break


if __name__ == '__main__':
    socketio.run(app,debug=True)
else:

    print('Imported')
    executor = ThreadPoolExecutor(max_workers=5)
    try:
        args = InteractiveParser()
        mui = MultiUserInterface()
        mui.start_trading(args, user_id='demo')
    except KeyboardInterrupt:
        print("main exiting")
        executor.shutdown(wait=False)
        exit(1)

socketio.run(app,debug=True)

