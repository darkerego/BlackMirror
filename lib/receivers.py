import json
import ssl
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
    def __init__(self, server_uri, rest, _ws, sa, contract_size, reenter,
                 data_source, exclude_markets, debug=True, min_score=10):
        self.debug = debug
        self.api = FtxApi(rest, _ws)
        self.sa = sa
        self.contract_size = contract_size
        self.reenter = reenter
        self.data_source = data_source
        self.exclude_markets = exclude_markets
        self.server_uri = server_uri
        self.host = self.server_uri.split(':')[0]
        self.port = int(self.server_uri.split(':')[1])
        self.cp = NewColorPrint()
        self.mq = MqSkel(host=self.host, port=self.port)
        self.cp.red('Starting ... mqtt')
        self.mq.mqStart(streamId='blackmirrorclient')

        self.sig_ = {}
        self.min_score = min_score

    def position_close(self, symbol, side, size, min_score=10):
        if min_score >= 10 or min_score <= -10:
            if side == 'long':
                self.cp.red('Closing Long!')
                self.api.sell_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)
                return True
            else:
                self.cp.red('Closing Short!')
                self.api.buy_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)

    def handle_message(self, message):
        self.cp.purple(f'Got Signal {message}!')
        message = json.loads(message)
        if message.get('Exit'):
            """TODO: Incomplete logic here
            """
            print('Got Exit Signal')
            side = message.get('Exit')
            side = side.lower()
            symbol = message.get('Instrument')
            score = message.get('Confidence Score')
            ok, size = self.check_position_exists_diff(future=symbol, s=None)
            self.position_close(symbol=symbol, side=side, size=size)
        if message.get('Enter'):
            print('Got Enter Signal')
            side = message.get('Enter')
            # side = side.lower()
            # symbol = message.get('Instrument')
            score = message.get('Confidence Score')
            score = score.strip('%')
            print(message.get("Enter"))
            print(message.get("Confidence Score"))
            print(message.get('Instrument'))
            score = float(score)
            if float(score) < 0:
                score = float(score) * -1
            print(score)

            self.sig_.update(message)
            print(self.sig_)
            _type = self.sig_.get('Enter')
            # _type = _type.lower()
            _instrument = self.sig_.get('Instrument')
            _symbol = str(_instrument[:-4] + '-PERP')
            print(_symbol)
            # _entry = self.sig_['Enter']
            # print(_type, _instrument, _entry)
            for i in range(1, 10):
                b, a, l = self.api.get_ticker(market=_symbol)
                if l == 0:
                    pass
                else:
                    print(l)
                    break

            info = self.api.info()
            # print(info)
            positions = info['positions']
            balance = info["freeCollateral"]
            leverage = info['leverage']

            qty = (float(balance) * leverage) / float(l) * 0.25
            print(balance, leverage, qty)

            if _type == 'LONG':
                if float(score) > float(self.min_score):
                    self.cp.alert('[LONG SIGNAL]: ENTERING!')
                    check, size = self.check_position_exists_diff(future=_symbol)
                    if check:
                        ret = self.api.buy_market(market=_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        self.cp.red('Cannot enter, position already open!')
                else:
                    print('Score too low')
            elif _type == 'SHORT':
                if float(score) > float(self.min_score):
                    self.cp.alert('[SHORT SIGNAL] ENTERING!')
                    check, size = self.check_position_exists_diff(future=_symbol)
                    if check:
                        ret = self.api.sell_market(_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        self.cp.red('Cannot enter, position already open!')
                else:
                    print('Score too low')

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

    def check_position_exists_diff(self, future, s=None):
        for pos in self.api.positions():

            if float(pos['collateralUsed']) == 0.0 and pos['future'] == future:
                print(pos)

                return True, pos['size']
        else:
            print('No pos')
        return False, 0
