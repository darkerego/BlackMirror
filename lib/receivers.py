import json
import ssl
import threading
import time
from utils import config_loader
from utils.colorprint import NewColorPrint
from websocket import create_connection, WebSocketConnectionClosedException
from trade_engine.api_wrapper import FtxApi
from utils.mq_skel import MqSkel, mqtt_que


class WebSocketSignals:
    ws_signals = []

    def __append__(self, data):
        self.ws_signals.append(data)

    def __get__(self):
        try:
            return self.ws_signals.pop()
        except IndexError:
            return None


class WsReceiver:
    def __init__(self, server_uri, rest, _ws, sa, contract_size, reenter,
                 data_source, exclude_markets, debug=True):
        self.wss = None
        self.cp = NewColorPrint()
        self.debug = debug
        self.api = FtxApi(rest, _ws)
        self.sa = sa
        self.contract_size = contract_size
        self.reenter = reenter
        self.data_source = data_source
        self.exclude_markets = exclude_markets
        self.debug = debug
        self.server_uri = server_uri
        self.i = 0
        self.sig_ = {}
        self._connect()

    # def authenticate(self):
    #    self.ws.send(enc_secret)

    def _connect(self):
        self.wss = create_connection(url=self.server_uri, sslopt={"cert_reqs": ssl.CERT_NONE})

    def check_position_exists_diff(self, future, s=None):
        for pos in self.api.positions():

            if float(pos['collateralUsed']) == 0.0 and pos['future'] == future:
                print(pos)

                return True, pos['size']
        else:
            print('No pos')
        return False

    def connect(self):
        while True:
            self.wss.send(f"request_signal")
            try:
                sig = self.wss.recv()
            except WebSocketConnectionClosedException:
                pass
            else:
                if sig == 'No Signal':
                    self.i += 1
                    if self.i % 20 == 0:
                        self.cp.debug('WS Alive')
                else:

                    try:
                        self.parse_sig(sig[0])
                    except json.decoder.JSONDecodeError:
                        pass

    def disconnect(self):
        self.wss.close()

    def parse_sig(self, sig):
        if sig:
            sig = json.loads(sig)
            for x in sig.keys():
                if x.pop('Exit'):
                    symbol = x.pop('symbol')
                    side = x.pop('side')
                    ok, size = self.check_position_exists_diff(future=symbol, s=None)
                    if side == 'Long':
                        self.cp.red('Closing Long!')
                        self.api.sell_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)
                    else:
                        self.cp.red('Closing Short!')
                        self.api.buy_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)
            else:

                self.cp.purple(f'Got Signal {sig}!')
                self.sig_.update(json.loads(sig))
                print(self.sig_)
                _type = self.sig_.get('signal')
                _instrument = self.sig_.get('instrument')
                _symbol = str(_instrument[:-4] + '-PERP')
                print(_symbol)
                _entry = self.sig_['entry']
                print(_type, _instrument, _entry)
                b, a, l = self.api.get_ticker(market=_symbol)
                print(l)
                info = self.api.info()
                positions = info['positions']
                balance = info["freeCollateral"]
                leverage = info['leverage']

                qty = (float(balance) * leverage) / float(l) * 0.25
                print(balance, leverage, qty)
                if _type == 'long':
                    self.cp.alert('[LONG SIGNAL]: ENTERING!')
                    if self.check_position_exists_diff(future=_symbol):
                        ret = self.api.buy_market(market=_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        self.cp.red('Cannot enter, position already open!')
                elif _type == 'short':
                    self.cp.alert('[SHORT SIGNAL] ENTERING!')
                    if self.check_position_exists_diff(future=_symbol):
                        ret = self.api.sell_market(_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        self.cp.red('Cannot enter, position already open!')
            time.sleep(0.25)


class MqReceiver:
    def __init__(self, server_uri, rest, _ws, sa, collateral_pct, reenter,
                 data_source, exclude_markets, debug=True, min_score=10, topic='/signals', live_score=False):
        self.debug = debug
        self.api = FtxApi(rest, _ws)
        self.sa = sa
        self.collateral_pct = collateral_pct
        self.reenter = reenter
        self.data_source = data_source
        self.exclude_markets = exclude_markets
        self.server_uri = server_uri
        self.topic = topic
        self.host = self.server_uri.split(':')[0]
        self.port = int(self.server_uri.split(':')[1])
        self.cp = NewColorPrint()
        self.mq = MqSkel(host=self.host, port=self.port, topic=self.topic)
        self.cp.red('Starting ... mqtt')
        self.mq.mqStart(streamId='blackmirrorclient')
        self.live_score = live_score

        self.sig_ = {}
        self.min_score = min_score

    def position_close(self, symbol, side, size, min_score=10):
        self.api.cancel_orders(market=symbol)
        if side == 'LONG':
            self.cp.red('Closing Long!')
            self.api.sell_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)
            return True
        else:
            self.cp.red('Closing Short!')
            self.api.buy_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)

    def handle_message(self, message):
        self.cp.purple(f'Received Trade Signal {message}!')
        message = json.loads(message)
        if message.get('Status') == 'closed':
            _type = message.get('Signal')
            _type = _type.lower()
            _instrument = self.sig_.get('Instrument')
            symbol = str(_instrument[:-4] + '-PERP')
            score = message.get('Score')
            self.cp.blue(f'[X] Received {_type} EXIT Signal for {symbol}')
            ok, size = self.check_position_exists_diff(future=symbol, s=None)
            self.position_close(symbol=symbol, side=_type, size=size)
        if message.get('Status') == 'open':
            self.sig_.update(message)
            if self.live_score:
                score = float(message.get('Live_score'))
            else:
                score = float(message.get('score'))
            _type = self.sig_.get('Signal')
            _instrument = self.sig_.get('Instrument')
            _symbol = str(_instrument[:-4] + '-PERP')
            if float(score) < 0:
                score = float(score) * -1
            if self.live_score:
                if float(score) < self.min_score:
                    ok, size = self.check_position_exists_diff(future=_symbol, s=None)
                    self.position_close(symbol=symbol, side=_type, size=size)

            for i in range(1, 10):
                b, a, l = self.api.get_ticker(market=_symbol)
                if l == 0:
                    break

            info = self.api.info()
            positions = info['positions']
            balance = info["freeCollateral"]
            leverage = info['leverage']

            qty = (float(balance) * leverage) / float(l) * self.collateral_pct
            print(balance, leverage, qty)

            if _type == 'LONG':
                #self.cp.blue(f'[E] Received {_type} Enter Signal for instrument {_instrument} of Score {score} %')
                if float(score) > float(self.min_score):
                    self.cp.alert('[LONG SIGNAL]: {_instrument} Score {score} % ENTERING!')
                    check, size = self.check_position_exists_diff(future=_symbol)
                    if check:
                        ret = self.api.buy_market(market=_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        self.cp.purple(ret)
                        #time.sleep(2)
                    else:
                        self.cp.red('Cannot enter, position already open!')
                else:
                    self.cp.yellow('[-] Score too low')
            elif _type == 'SHORT':
                if float(score) > float(self.min_score):
                    self.cp.alert('[SHORT SIGNAL]: {_instrument} Score {score} % ENTERING!')
                    check, size = self.check_position_exists_diff(future=_symbol)
                    if check:
                        ret = self.api.sell_market(_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        self.cp.purple(ret)
                        #time.sleep(2)
                    else:
                        self.cp.red('Cannot enter, position already open!')
                else:
                    self.cp.yellow('[-] Score too low')

    def run(self):
        while True:
            message = mqtt_que.__mq__signal__()
            if message:
                try:
                    self.handle_message(message)
                except Exception as err:
                    print(err)
            else:
                time.sleep(0.25)

    def start_process(self):
        t = threading.Thread(target=self.run())
        t.start()

    def check_position_exists_diff(self, future, s=None):
        for pos in self.api.positions():

            if float(pos['collateralUsed']) == 0.0 and pos['future'] == future:
                print(pos)

                return True, pos['size']
        else:
            print('No pos')
        return False, 0
