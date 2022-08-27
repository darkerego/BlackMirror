import asyncio
import json
import ssl
import threading
import time

from websocket import create_connection, WebSocketConnectionClosedException

import trade_engine.aligning_sar
from lib import score_keeper
from lib.mq import async_client
from trade_engine.api_wrapper import FtxApi
from utils.colorprint import NewColorPrint


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
        self.api = FtxApi(rest, _ws, sa)
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
                return False, 0
        return True, pos['size']

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
                # print(_symbol)
                _entry = self.sig_['entry']
                print(_type, _instrument, _entry)
                b, a, l = self.api.get_ticker(market=_symbol)
                # print(l)
                info = self.api.info()
                positions = info['positions']
                balance = info["freeCollateral"]
                leverage = info['leverage']

                qty = (float(balance) * leverage) / float(l) * 0.25
                # print(balance, leverage, qty)
                if _type == 'long':
                    self.cp.alert('[LONG SIGNAL]: ENTERING!')
                    if not self.check_position_exists_diff(future=_symbol):
                        ret = self.api.buy_market(market=_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        self.cp.red('Cannot enter, position already open!')
                elif _type == 'short':
                    self.cp.alert('[SHORT SIGNAL] ENTERING!')
                    if not self.check_position_exists_diff(future=_symbol):
                        ret = self.api.sell_market(_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        self.cp.red('Cannot enter, position already open!')
            time.sleep(0.25)


class MqReceiver:
    def __init__(self, server_uri, api, collateral_pct, reenter, sar_validation,
                 data_source, exclude_markets, debug=True, min_score=10, topic='/signals', live_score=False, min_adx=20,
                 confirm=False):
        self.lock = asyncio.Lock()
        self.debug = debug
        self.running = False
        self.api = api
        # self.sa = sa
        self.collateral_pct = collateral_pct
        self.reenter = reenter
        self.data_source = data_source
        self.exclude_markets = exclude_markets
        self.server_uri = server_uri
        self.topic = topic
        self.confirm = confirm
        self.host = self.server_uri.split(':')[0]
        self.port = int(self.server_uri.split(':')[1])
        self.positions = {}
        self.cp = NewColorPrint()
        # self.mq = async_client.MqttClient(host=self.host, port=self.port)
        self.live_score = live_score
        self.score_keeper = score_keeper.scores
        self.sig_ = {}
        self.min_score = min_score
        self.min_adx = min_adx
        self.sar_validation = sar_validation
        self.validator = trade_engine.aligning_sar.TheSARsAreAllAligning()

    def sell_market(self, *args, **kwargs):
        if self.confirm:
            return self.api.sell_market(*args, **kwargs)

    def buy_market(self, *args, **kwargs):
        if self.confirm:
            return self.api.buy_market(*args, **kwargs)

    def position_close(self, symbol, side, size):
        # self.api.cancel_orders(market=symbol)
        if side == 'LONG':
            self.cp.red(f'Closing Long on {symbol}!')
            self.sell_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)

            return True
        else:
            self.cp.red(f'Closing Short on {symbol}!')
            self.buy_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)

    def sar_validate(self, _symbol, res=300):
        return self.validator.get_sar(symbol=_symbol, period=res)


    def handle_message(self, topic, message):

        # print(message)

        if topic == '/echo':
            print(f'[~] Echo command: {message}')
            return
        if self.live_score:
            message = json.loads(message)
            self.sig_.update(message)
            if topic == '/signals':
                return
            try:
                score = float(message.get('Live_score'))
            except KeyError:
                return
        else:
            message = json.loads(message)
            self.sig_.update(message)
            if topic == '/stream':
                return
            score = float(message.get('Score'))
        _adx = float(self.sig_.get('Mean_Adx'))
        _type = self.sig_.get('Signal')
        _instrument = self.sig_.get('Instrument')
        _symbol = str(_instrument[:-4] + '-PERP')
        live_score = float(message.get('Live_score'))
        self.score_keeper[_symbol] = {'status': 'open', 'score': float(live_score)}
        if self.exclude_markets.__contains__(_symbol):
            return

        self.cp.purple(f'Received Trade Signal {message} with score {score}!')

        if message.get('Status') == 'closed':
            _type = message.get('Signal')
            _type = _type.lower()
            _instrument = self.sig_.get('Instrument')
            _symbol = str(_instrument[:-4] + '-PERP')

            self.score_keeper[_symbol] = {'status': 'closed', 'score': float(score)}
            size = self.check_position_exists(future=_symbol, s=None)
            if size:
                self.cp.blue(f'[X] Received {_type} EXIT Signal for {_symbol}, closing!')
                self.position_close(symbol=_symbol, side=_type, size=size)

        if message.get('Status') == 'open':

            _type = self.sig_.get('Signal')
            _instrument = self.sig_.get('Instrument')
            _symbol = str(_instrument[:-4] + '-PERP')

            if float(score) < 0:
                score = float(score) * -1
            """if self.live_score:

                if float(score) < self.min_score:
                    ok, size = self.check_position_exists(future=_symbol, s=None)
                    if ok:
                        print(f'[!] Closing position" {_symbol}')
                        self.position_close(symbol=_symbol, side=_type, size=size)
                        #tally.loss()"""

            for i in range(1, 10):
                b, a, l = self.api.get_ticker(market=_symbol)
                if l == 0:
                    break

            info = self.api.info()
            balance = info["freeCollateral"]
            leverage = info['leverage']

            qty = (float(balance) * leverage) / float(l) * self.collateral_pct
            # print(balance, leverage, qty)

            if _type == 'LONG':
                # self.cp.blue(f'[E] Received {_type} Enter Signal for instrument {_instrument} of Score {score} %')
                if float(score) > float(self.min_score):
                    if float(_adx) >= self.min_adx:
                        self.cp.alert(f'[LONG SIGNAL]: {_instrument} Score {score} % VALIDATING!!')

                        size = self.check_position_exists(future=_symbol)
                        print(size)
                        if not size:
                            side, sar = self.validator.get_sar(symbol=_symbol, period=300)
                            print(side, sar)
                            if side == 1:
                                side, sar = self.validator.get_sar(symbol=_symbol, period=60)
                                print(side, sar)
                                if side == 1:
                                    self.cp.purple('[+] Trade validated! ... ENTERING!')
                                    ret = self.buy_market(market=_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                                    self.cp.purple(ret)
                                else:
                                    self.cp.navy('[-] Trade not valid! ... DISCARDING!')
                            else:
                                self.cp.navy('[-] Trade not valid! ... DISCARDING!')
                        else:
                            self.cp.red(f'Cannot enter {_symbol}, position already open!')
                    else:
                        self.cp.yellow('[-] ADX too low')
                else:
                    self.cp.yellow('[-] Score too low')
            elif _type == 'SHORT':
                if float(score) > float(self.min_score):
                    if float(_adx) >= self.min_adx:
                        self.cp.alert(f'[SHORT SIGNAL]: {_instrument} Score {score} % --  !')
                        size = self.check_position_exists(future=_symbol)
                        if not size:

                            side, sar = self.validator.get_sar(symbol=_symbol, period=300)
                            if side == -1:
                                side, sar = self.validator.get_sar(symbol=_symbol, period=60)
                                if side == -1:
                                    self.cp.purple('[+] Trade validated! ... ENTERING!')
                                    ret = self.sell_market(_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                                    self.cp.purple(ret)
                                else:
                                    self.cp.navy('[-] Trade not valid! ... DISCARDING!')
                            else:
                                self.cp.navy('[-] Trade not valid! ... DISCARDING!')
                        else:
                            self.cp.red(f'Cannot enter {_symbol}, position already open!')
                    else:
                        self.cp.yellow('[-] ADX too low')
                else:
                    self.cp.yellow('[-] Score too low')

    def run(self):
        print('Start run')
        self.running = True
        while self.running:
            message = async_client.message_que.read_incoming()
            ts = time.time()

            if message is not None:
                topic = message[0]
                message = message[1]
                time.sleep(0.24)
                try:
                    self.handle_message(topic, message)
                except Exception as err:
                    print('ERROR: ', err)
            else:
                time.sleep(0.25)

    def launch_event_loops(self, mq):
        # get a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(mq.start_loop())

    async def start_process(self):
        if not self.lock.locked():
            await self.lock.acquire()
            print('Start mqtt')
            mq = async_client.MqttClient(host=self.host, port=int(self.port))

            threading.Thread(target=self.launch_event_loops, args=(mq,)).start()
            print('Started')
            t = threading.Thread(target=self.run())
            t.start()

    def check_position_exists(self, future, s=None):
        """
        Return True if position exists
        """
        positions = self.api.positions()
        for pos in positions:
            if pos.get('future') == future:
                print('OK')
                return pos['collateralUsed']
        return 0.0
