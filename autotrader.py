#!/usr/bin/env python3
##########################################################################################

"""



  ██████╗ ██╗      █████╗  ██████╗██╗  ██╗███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗
  ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
  ██████╔╝██║     ███████║██║     █████╔╝ ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝
  ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗
  ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║
  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
    ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    github.com/darkerego - 2020 - 2021 0- 0x7612E93FF157d1973D0f95Be9E4f0bdF93BAf0DE
    ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
           FTX Trade Mirroring Platform ~ Darkerego, 2020-2021 ~ version 2.6
            - experimental `oscillation arbitrage` - websocket signal support -
            volatility driven auto trader - "maket taker" strategy - incremental, market -  market maker mode -
             global market trend analysis - custom strategy support - automatic positon building -
             auto hedge management - api navigator - and much more

    """

import datetime
import json
import logging
import os
import ssl
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from websocket import create_connection, WebSocketConnectionClosedException

from exchanges.ftx_lib.rest import client
from exchanges.ftx_lib.websocket_api import client as ws_client
#from extras import logo
from trade_engine.api_wrapper import FtxApi
from trade_engine.osc_engine import OscillationArbitrage
from trade_engine.stdev_aggravator import FtxAggratavor
from utils import config_loader
from utils.colorprint import NewColorPrint
from utils.ftx_exceptions import FtxDisconnectError
from utils.get_args import get_args

try:
    import thread
except ImportError:
    import _thread as thread
import time

#logo.start()
use_custom_ts = False
debug = True
logging.basicConfig()
#key, secret, subaccount = config_loader.load_config('utils/conf.json')
key = 'CSKxiLYumiIeyEKF4lTHS4c5NgCEAz3EIchGXe3i'
secret = 'rd8J5wKcM6m6f_FQjvnlviWSysbPthFH0KEvF7Fg'
subaccount = None


class WebSocketSignals:
    ws_signals = []

    def __append__(self, data):
        self.ws_signals.append((data))

    def __get__(self):
        try:
            return self.ws_signals.pop()
        except IndexError:
            return None


ws_signals = WebSocketSignals()



class WsReceiver:
    def __init__(self, server_uri, rest, _ws, sa, contract_size, reenter,
                          data_source, exclude_markets, debug=True):
        self.wss = None
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
                        cp.debug('WS Alive')
                else:
                    #if self.debug:

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
                        cp.red('Closing Long!')
                        self.api.sell_market(market=symbol, qty=size,reduce=True, ioc=False, cid=None)
                    else:
                        cp.red('Closing Short!')
                        self.api.buy_market(market=symbol, qty=size, reduce=True, ioc=False, cid=None)
            else:

                cp.purple(f'Got Signal {sig}!')
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
                    cp.alert('[LONG SIGNAL]: ENTERING!')
                    if self.check_position_exists_diff(future=_symbol):
                        ret = self.api.buy_market(market=_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        cp.red('Cannot enter, position already open!')
                elif _type == 'short':
                    cp.alert('[SHORT SIGNAL] ENTERING!')
                    if self.check_position_exists_diff(future=_symbol):
                        ret = self.api.sell_market(_symbol, qty=qty, reduce=False, ioc=False, cid=None)
                        print(ret)
                    else:
                        cp.red('Cannot enter, position already open!')
            time.sleep(0.25)


class AutoTrader:
    """
    Automatic Trade Engine. Automatically sets stop losses and take profit orders. Trailing stops are used
    unless otherwise specified.
    """

    def __init__(self, api, stop_loss, _take_profit, use_ts=True, ts_pct=0.05, reopen=False, period=300, ot='limit',
                 max_open_orders=None, position_step_size=0.02, disable_stop_loss=False, show_tickers=True,
                 monitor_only=False, close_method='market'):
        self.up_markets = {}
        self.down_markets = {}
        self.trend = 'N/A'
        self.show_tickers = show_tickers
        self.stop_loss = stop_loss
        self._take_profit = _take_profit
        self.use_ts = use_ts
        self.trailing_stop_pct = ts_pct
        self.api = api
        self.monitor_only = monitor_only
        self.logger = logging.getLogger(__name__)
        self.wins = 0
        self.losses = 0
        self.accumulated_pnl = 0
        self.total_contacts_trade = 0
        self.reopen = reopen
        self.close_method = close_method
        self.period = period
        self.order_type = ot
        self.agg = FtxAggratavor()
        self.future_stats = {}
        self.alert_map = []
        self.alert_up_levels = [0.25, 2.5, 5, 10, 12.5, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
        self.alert_down_levels = [-0.25, -2.5, -5, -10, -12.5, -15, -20, -25, -30, -40, -50 - 60, -70, -80, -90, -100]

        self.max_open_orders = max_open_orders
        self.position_step_size = position_step_size
        self.disable_stop_loss = disable_stop_loss
        if self.reopen:
            cp.yellow('Reopen enabled')
        if self.stop_loss > 0.0:
            self.stop_loss = self.stop_loss * -1
        if self.monitor_only:
            cp.red('[!] Monitor Only enabled. Will NOT trade.')

    def trailing_stop(self, market, qty, entry, side, offset=.25, ts_o_type='market'):
        """
         Place a trailing stop order to ensure profit is taken from current position,
         Stop direction determined by current position, so there is no need to pass a negative offset, but
         if the user does then we correct it by `offset * -1`
        :param offset: integer representing how many dollars to trail the stop behind the current position
        """

        entry_price = entry
        qty = qty
        print('Trailing stop triggered')
        if side == 'buy':
            # side = 'sell'
            # long position, so this will be a sell stop
            current_price = self.api.get_ticker(market=market)[1]
            trail_value = (current_price - entry) * self.trailing_stop_pct * -1
            # offset_price = (float(current_price) - float(entry_price)) * (1-offset)
            offset_price = current_price - (current_price - entry) * offset
            text = f'Trailing sell stop for long position, type {ts_o_type}'
            # qty = qty * -1
            opp_side = 'sell'
            cp.green(
                f'Trailing Stop for long position of entry price: {entry_price} triggered: offset price {offset_price}'
                f' current price: {current_price}')
        else:
            # short position, so this will be a buy stop
            # side = 'buy'
            current_price = self.api.get_ticker(market=market)[0]
            trail_value = (entry - current_price) * self.trailing_stop_pct
            # offset_price = (float(current_price) + float(offset))
            offset_price = current_price + (entry - current_price) * offset
            text = f'Trailing buy stop for short position, type {ts_o_type}'
            # qty = qty * -1
            opp_side = 'buy'
            cp.red(
                f'Trailing Stop for short position of entry price: {entry_price} triggered: offset price {offset_price}'
                f' current price: {current_price}')

        while True:
            if side == "sell":
                sell_price = self.api.get_ticker(market=market)[1]
                if (float(sell_price) - float(offset)) > float(offset_price):
                    offset_price = float(sell_price) - float(offset)
                    cp.purple("New low observed: %.8f Updating stop loss to %.8f" % (sell_price, offset_price))
                elif float(sell_price) <= float(offset_price):
                    sell_price = self.api.get_ticker(market=market)[1]
                    """if tschase:
                        self.logger.info(f'Chasing sell order ... max chase: {max_chase}')
                        self.logger.info("Sell triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, sell_price,
                                                                                                 offset_price))
                        chaser = threading.Thread(target=self.limit_chase, args=(qty, max_chase, True))
                        chaser.start()
                    "else:"""
                    cp.purple("Buy triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, sell_price,
                                                                                  offset_price))
                    ret = self.api.buy_market(market=market, qty=float(qty),
                                              ioc=False, reduce=True, cid=None)
                    self.logger.debug(ret)

                    self.triggered = False
                    return True

            if side == "buy":
                current_price = self.api.get_ticker(market=market)[0]
                if (float(current_price) + float(offset)) < float(offset_price):
                    offset_price = float(current_price) + float(offset)
                    print(offset_price)
                    cp.purple(
                        "New high observed: %.8f Updating stop loss to %.8f" % (current_price, offset_price))
                elif float(current_price) >= float(offset_price):
                    current_price = self.api.get_ticker(market=market)[0]
                    """if tschase:
                        self.logger.info(f'Chasing buy order ... max chase: {max_chase}')
                        self.logger.info("Sell triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, current_price,
                                                                                                 offset_price))
                        chaser = threading.Thread(target=self.limit_chase, args=(qty, max_chase, True))
                        chaser.start()
                    else:"""
                    cp.purple("Sell triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, current_price,
                                                                                   offset_price))
                    # ret = self.api.new_order(market=market, side=opp_side, size=qty, _type='market')
                    ret = self.api.sell_market(market=market, qty=float(qty),
                                               ioc=False, reduce=True, cid=None)
                    # ret = self.rest.place_order(market=market, side=opp_side, size=qty, type='market', reduce_only=True, ioc=False)
                    self.logger.debug(ret)

                    self.triggered = False
                    return True

    def stop_loss_order(self, market, side, size):
        if size < 0.0:
            size = size * -1
        self.losses += 1
        if side == 'buy':
            # market sell # market, qty, reduce, ioc, cid
            cp.red('[!] Stop hit!')
            ret = self.api.sell_market(market=market, qty=size, reduce=True, ioc=False, cid=None)
            return ret
        else:
            # market buy # marekt, qty, reduce, ioc, cid
            cp.red('[!] Stop hit!')

            ret = self.api.buy_market(market=market, qty=size, reduce=True, ioc=False, cid=None)
            return ret

    def take_profit(self, market: str, side: str, entry: float, size: float, order_type: str = 'limit'):
        ticker = self.api.get_ticker(market=market)
        bid = price = float(ticker[0])
        ask = inverse = float(ticker[1])

        if side == 'buy':
            opp_side = 'sell'
            trail_value = (ask - entry) * self.trailing_stop_pct
            if self.use_ts:
                cp.white_black(f'[฿] Sending a trailing stop: {trail_value}')
                # executor = ThreadPoolExecutor(max_workers=5)
                # ret = executor.submit(self.trailing_stop, market=market, side=opp_side, qty=float(o_size),
                #                      entry=float(entry), offset=float(self.trailing_stop_pct))
                ret = self.trailing_stop(market=market, side=side, qty=size, offset=self.trailing_stop_pct, entry=entry)
                if ret:
                    print('Success at take profit')
                    self.wins += 1
                    return True
            else:
                cp.yellow(f'[฿] Sending a market order, side: {opp_side}, price: {price}')
                if order_type == 'market':  # market, qty, reduce, ioc, cid):
                    ret = self.api.sell_market(market=market, qty=size, ioc=False, reduce=True)
                else:  # market, qty, price=None, post=False, reduce=False, cid=None):
                    cp.purple(f'[฿] Sending a limit order, side: {opp_side}, price: {price}')
                    ret = self.api.sell_limit(market=market, qty=size, price=ask, reduce=True)
                    self.wins += 1
                    return ret
        else:  # side == sell
            opp_side = 'buy'
            trail_value = (entry - bid) * self.trailing_stop_pct * -1
            if self.use_ts:
                cp.green(f'[฿] Sending a trailing stop: {trail_value}')
                # executor = ThreadPoolExecutor(max_workers=5)
                # ret = executor.submit(self.trailing_stop, market=market, side=opp_side, qty=float(o_size),
                #                      entry=float(entry), offset=float(self.trailing_stop_pct))
                ret = self.trailing_stop(market=market, side=side, qty=size, offset=self.trailing_stop_pct, entry=entry)

            else:
                cp.purple(f'[฿] Sending a market order, side: {opp_side}, price: {price}')
                if order_type == 'market':
                    ret = self.api.buy_market(market=market, side=opp_side, size=size,
                                              _type='market', ioc=False, reduce=True)
                    self.wins += 1
                    return ret
                else:
                    cp.purple(f'[฿] Sending a limit order, side: {opp_side}, price: {price}')
                    ret = self.api.buy_limit(market=market, qty=size, price=ask, reduce=True)
                    self.wins += 1
                    return ret
        cp.red(f"[฿]: ({ret}")

        return ret

    def take_profit_wrap(self, market: str, side: str, entry: float, size: float, order_type: str = 'limit'):
        if side == 'buy':
            opp_side = 'sell'
        else:
            opp_side = 'buy'
        if self.close_method == 'increment':
            return self.increment_orders(market=market, side=opp_side, qty=size, period=self.period, reduce=True)
        else:
            return self.take_profit(market=market, side=side, entry=entry, size=size, order_type=order_type)

    def re_open_limit(self, market, side, qty):
        for _ in range(0, 9):
            bid, ask, last = self.api.get_ticker(market=market)
            if side == 'buy':  # market, qty, price=None, post=False, reduce=False, cid=None):
                ret = self.api.buy_limit(market=market, qty=qty, price=bid, post=False, reduce=False)
                if ret['id']:
                    return ret
            elif side == 'sell':
                ret = self.api.sell_limit(market=market, qty=qty, price=ask, post=False, reduce=False)
                if ret['id']:
                    return ret

    def re_open_market(self, market, side, qty):
        for i in range(0, 9):
            if side == 'buy':  # market, qty, price=None, post=False, reduce=False, cid=None):
                ret = self.api.buy_market(market=market, qty=qty, reduce=False, ioc=False, cid=None)
                if ret['id']:
                    return ret
            if side == 'sell':
                ret = self.api.sell_market(market=market, qty=qty, reduce=False, ioc=False, cid=None)
                if ret['id']:
                    return ret

    def increment_orders(self, market, side, qty, period, reduce=False):
        current_size = 0
        open_order_count = self.api.get_open_orders(market=market)

        for o in open_order_count:
            current_size += o.get('size')
        cp.yellow(f'[i] Open Orders: {len(open_order_count)}, Qty Given: {qty}, Current open Qty: {current_size}')

        if len(open_order_count) >= self.max_open_orders * 4:
            self.api.cancel_orders(market=market)

        buy_orders = []
        sell_orders = []
        max_orders = self.max_open_orders
        stdev = self.agg.get_stdev(symbol=market, period=period)
        cp.yellow(f'Stdev: {stdev}')

        o_qty = qty / max_orders
        # cp.red(f'[!] Killing {open_order_count} currently open orders...')
        # while qty > (qty * 0.95):
        if side == 'buy':
            bid, ask, last = self.api.get_ticker(market=market)
            # last_order_price = bid - (deviation * self.position_step_size)
            for i in range(1, max_orders + 1):
                next_order_price = bid - (stdev * self.position_step_size) * i
                buy_orders.append(['buy', o_qty, next_order_price, market, 'limit'])

                cp.yellow(f'[o] Placing new {side} order on market {market} at price {next_order_price}')
                for x in range(1, 10):  # market, qty, price=None, post=False, reduce=False, cid=None):
                    status = self.api.buy_limit(market=market, price=next_order_price, qty=o_qty,
                                                reduce=reduce, cid=None)
                    if status:
                        cp.red(f"[฿]: {status.get('id')}")
                        break
                    else:
                        time.sleep(0.25)
            cp.debug(f'Debug: : Buy Orders{buy_orders}')
            return True


        else:
            bid, ask, last = self.api.get_ticker(market=market)
            # last_order_price = ask + (deviation * self.position_step_size)
            for i in range(1, max_orders + 1):
                next_order_price = ask + (stdev * self.position_step_size) * i
                sell_orders.append(['sell', o_qty, next_order_price, market, 'limit'])
                for i in range(1, 10):
                    status = self.api.sell_limit(market=market, price=next_order_price, qty=o_qty,
                                                 reduce=reduce, cid=None)
                    if status:
                        cp.purple(f"[฿]: ({status['id']}")
                        break
                    else:
                        time.sleep(0.25)
            cp.debug(f'Debug: : Sell Orders{sell_orders}')
            return True

    def reopen_pos(self, market, side, qty, period=None):
        if self.order_type == 'limit' and self.reopen != 'increment':
            return self.re_open_limit(market, side, qty)
        if self.order_type == 'market' and self.reopen != 'increment':
            return self.re_open_market(market, side, qty)
        if self.reopen == 'increment':
            return self.increment_orders(market, side, qty, period)

    def pnl_calc(self, qty, sell, buy, fee=0.00019):
        """
        Profit and Loss Calculator - assume paying
         two market fees (one for take profit, one for re-opening). This way we can
         set tp to 0 and run as market maker and make something with limit orders.
        """
        if fee <= 0:
            self.pnl = float(qty * (sell - buy) * (1 - fee))
        else:
            self.pnl = float(qty * (sell - buy) * (1 - (fee * 2)))
        if self.pnl is not None:  # pythonic double negative nonsense
            return self.pnl
        return 0.0

    def parse(self, pos, info):
        """
        {'future': 'TRX-0625', 'size': 9650.0, 'side': 'buy', 'netSize': 9650.0, 'longOrderSize': 0.0,
        'shortOrderSize': 2900.0, 'cost': 1089.1955, 'entryPrice': 0.11287, 'unrealizedPnl': 0.0, 'realizedPnl':
        -100.1977075, 'initialMarginRequirement': 0.05, 'maintenanceMarginRequirement': 0.03, 'openSize': 9650.0,
        'collateralUsed': 54.459775, 'estimatedLiquidationPrice': 0.11020060583397326, 'recentAverageOpenPrice':
        0.14736589533678757, 'recentPnl': -332.88539, 'recentBreakEvenPrice': 0.14736589533678757,
        'cumulativeBuySize': 9650.0, 'cumulativeSellSize': 0.0}
        """

        future_instrument = pos['future']
        size = 0
        if debug:
            cp.white_black(f'[d]: Processsing {future_instrument}')
        for f in self.api.futures():

            """{'name': 'BTT-PERP', 'underlying': 'BTT', 'description': 'BitTorrent Perpetual Futures', 
            'type': 'perpetual', 'expiry': None, 'perpetual': True, 'expired': False, 'enabled': True, 'postOnly': 
            False, 'priceIncrement': 5e-08, 'sizeIncrement': 1000.0, 'last': 0.0050772, 'bid': 0.00507655, 
            'ask': 0.00508115, 'index': 0.0050384623482894655, 'mark': 0.0050785, 'imfFactor': 1e-05, 'lowerBound': 
            0.00478655, 'upperBound': 0.00532945, 'underlyingDescription': 'BitTorrent', 'expiryDescription': 
            'Perpetual', 'moveStart': None, 'marginPrice': 0.0050785, 'positionLimitWeight': 20.0, 
            'group': 'perpetual', 'change1h': -0.009169837089064482, 'change24h': 0.3340075388434311, 'changeBod': 
            0.11461053925334153, 'volumeUsd24h': 41050555.11565, 'volume': 9253264000.0} """
            mark_price = f['mark']
            index = f['index']
            name = f['name']
            volumeUsd24h = f['volumeUsd24h']
            change1h = f['change1h']
            change24h = f['change24h']
            min_order_size = f['sizeIncrement']
            self.future_stats[name] = {}
            self.future_stats[name]['mark'] = mark_price
            self.future_stats[name]['index'] = index
            self.future_stats[name]['volumeUsd24h'] = volumeUsd24h
            self.future_stats[name]['change1h'] = change1h
            self.future_stats[name]['change24h'] = change24h
            self.future_stats[name]['min_order_size'] = min_order_size
            # if not self.ticker_stats.__contains__(name):
            #    name = FutureStat(name=name, price=mark_price, volume=volumeUsd24h)
            #    self.ticker_stats.append(name)
            # else:
            #    p, v = name.update(price=mark_price, volume=volumeUsd24h)

            # if self.show_tickers:
            if f['name'] == future_instrument:
                if debug:
                    cp.dark(
                        f"[🎰] [{name}] Future Stats: {change1h}/hour {change24h}/today, Volume: {volumeUsd24h}")
                # print(f'Debug: {f}')
            if float(change1h) > 0.025 and self.show_tickers:
                if float(change24h) > 0:
                    cp.ticker_up(
                        f'[🔺]Future {name} is up {change1h} % this hour! and {change24h} today, Volume: {volumeUsd24h}, ')


                else:
                    cp.ticker_up(f'[🔺] Future {name} is up {change1h} % this hour!')

            if change1h < -0.025 and self.show_tickers:
                if float(change24h) < 0:
                    cp.ticker_down(
                        f'[🔻]Future {name} is down {change1h} % this hour!and {change24h} today, Volume: {volumeUsd24h}!')
                else:
                    cp.ticker_down(f'[🔻] Future {name} is down {change1h} % this hour!')

            if change24h > 0:
                self.up_markets[name] = (volumeUsd24h, change1h)
            elif change24h < 0:
                self.down_markets[name] = (volumeUsd24h, change1h)

        if len(self.up_markets) > len(self.down_markets):
            if self.show_tickers:
                cp.green('[+] Market Average Trend: LONG')
            self.trend = 'up'
        if len(self.up_markets) == len(self.down_markets):
            if self.show_tickers:
                cp.yellow('[~] Market Average Trend: NEUTRAL')
        if len(self.up_markets) < len(self.down_markets):
            if self.show_tickers:
                cp.red('[-] Market Average Trend: SHORT')
            self.trend = 'down'

        # if future_instrument in self.symbols:
        collateral_used = pos['collateralUsed']
        cost = pos['cost']
        buy_size = pos['cumulativeBuySize']
        sell_size = pos['cumulativeSellSize']
        size = pos['netSize']
        entry_price = pos['entryPrice']
        liq_price = pos['estimatedLiquidationPrice']
        avg_open_price = pos['recentAverageOpenPrice']
        avg_break_price = pos['recentBreakEvenPrice']
        recent_pnl = pos['recentPnl']
        unrealized_pnl = pos['unrealizedPnl']
        takerFee = info['takerFee']
        makerFee = info['makerFee']
        side = pos['side']
        # For future implantation
        # Are we a long or a short?
        if side == 'buy':
            pos_side = 'sell'
            self.trailing_stop_pct = self.trailing_stop_pct * -1
            ask, bid, last = self.api.get_ticker(market=future_instrument)
            if not ask:
                return
            current_price = bid
            current_price_inverse = ask
            try:
                pnl = self.pnl_calc(qty=size, sell=ask, buy=avg_open_price, fee=takerFee)
            except:
                pass

            try:
                if pnl <= 0.0:
                    cp.red(f'[🔻] Negative PNL {pnl} on position {future_instrument}')
                else:
                    cp.green(f'[🔺] Positive PNL {pnl} on position {future_instrument}')
            except Exception as err:
                pass
            try:
                pnl_pct = (float(pnl) / float(cost)) * 100
            except Exception as fuck:

                return
        else:
            # short position
            side = 'sell'
            pos_side = 'buy'
            ask, bid, last = self.api.get_ticker(market=future_instrument)
            if not bid:
                return
            current_price = ask
            current_price_inverse = bid
            pnl = self.pnl_calc(qty=(size * -1), sell=avg_open_price, buy=bid, fee=takerFee)
            try:
                if pnl <= 0.0:
                    cp.red(f'[🔻] Negative PNL {pnl} on position {future_instrument}')
                else:
                    cp.green(f'[🔺] Positive PNL {pnl} on position {future_instrument}')
            except Exception as err:
                pass

            try:
                pnl_pct = (float(pnl) / float(cost * -1)) * 100
            except Exception as fuck:
                return

        cp.random_pulse(
            f'[▶] Instrument: {future_instrument}, Side: {side}, Size: {size} Cost: {cost}, Entry: {entry_price},'
            f' Open: {avg_open_price} Liq: {liq_price}, BreakEven: {avg_break_price}, PNL: {recent_pnl}, '
            f'UPNL: {unrealized_pnl}, Collateral: {collateral_used}')
        if recent_pnl is None:
            return

        if pnl_pct > self._take_profit:

            print(f'Target profit level of {self._take_profit} reached! Calculating pnl')
            if float(size) < 0.0:
                size = size * -1
            self.accumulated_pnl += pnl
            cp.alert('----------------------------------------------')
            cp.alert(f'Total Session PROFITS: {self.accumulated_pnl}')
            cp.alert('----------------------------------------------')
            cp.green(f'Reached target pnl of {pnl_pct} on {future_instrument}, taking profit... PNL: {pnl}')
            o_size = size
            self.total_contacts_trade += (o_size * last)

            cp.purple(f'Sending {pos_side} order of size {o_size} , price {current_price}')
            if self.monitor_only:
                cp.red('[!] Not actually trading... ')
            else:
                ret = self.take_profit_wrap(entry=entry_price, side=side, size=o_size, order_type='market',
                                            market=future_instrument)
                if ret:
                    print('Success')

                if ret and self.reopen:
                    # self.accumulated_pnl += pnl
                    cp.yellow('Reopening .... ')
                    ret = self.reopen_pos(market=future_instrument, side=side, qty=o_size, period=self.period)
                    self.total_contacts_trade += (o_size * last)
                    if ret:
                        print('[🃑] Success')


        else:
            cp.yellow(
                f'[$]PNL %: {pnl_pct}/Target %: {self._take_profit}/Target Stop: {self.stop_loss}, PNL USD: {pnl}')
            if pnl_pct < self.stop_loss and not self.disable_stop_loss:
                if self.monitor_only:
                    cp.red('[!] NOT TRADING: Stop Hit.')
                else:
                    self.stop_loss_order(market=future_instrument, side=side, size=size * -1)
                self.accumulated_pnl -= pnl

    def position_parser(self, positions, account_info):
        for pos in positions:
            if float(pos['collateralUsed'] != 0.0) or float(pos['longOrderSize']) > 0 or float(
                    pos['shortOrderSize']) < 0:
                self.parse(pos, account_info)

    def start_process(self):
        cp.purple('[i] Starting AutoTrader, performing sanity check. ...')

        iter = 0
        while True:
            iter += 1
            """{'username': 'xxxxxxxx@gmail.com', 'collateral': 4541.2686261529458, 'freeCollateral': 
                        13.534738011297414, 'totalAccountValue': 4545.7817261529458, 'totalPositionSize': 9535.4797, 
                        'initialMarginRequirement': 0.05, 'maintenanceMarginRequirement': 0.03, 'marginFraction': 
                        0.07802672286726425, 'openMarginFraction': 0.07527591244130713, 'liquidating': False, 'backstopProvider': 
                        False, 'positions': [{'future': 'BAT-PERP', 'size': 0.0, 'side': 'buy', 'netSize': 0.0, 'longOrderSize': 
                        0.0, 'shortOrderSize': 0.0, 'cost': 0.0, 'entryPrice': None, 'unrealizedPnl': 0.0, 'realizedPnl': 
                        5.59641262, 'initialMarginRequirement': 0.05, 'maintenanceMarginRequirement': 0.03, 'openSize': 0.0, 
                        'collateralUsed': 0.0, 'estimatedLiquidationPrice': None}, """
            try:
                info = self.api.info()
                pos = self.api.positions()
            except Exception as fuck:
                self.logger.error(fuck)
                print(repr(fuck))
            except KeyboardInterrupt:
                for i in range(1, 15):
                    cp.random_color('[x] Caught Signal ~ Exiting with graceful vivid technicolor.')
                sys.exit()
            else:
                cp.pulse(f'[$] Account Value: {info["totalAccountValue"]} Collateral: {info["collateral"]} '
                       f'Free Collateral: {info["freeCollateral"]}, Contracts Traded: {self.total_contacts_trade}')
                if self.wins != 0 or self.losses != 0:
                    cp.white_black(f'[🃑] Wins: {self.wins} [🃏] Losses: {self.losses}')
                else:
                    cp.white_black(f'[🃑] Wins: - [🃏] Losses: -')

                try:
                    self.position_parser(positions=pos, account_info=info)
                except Exception as err:
                    print(err)
                except KeyboardInterrupt:
                    sys.exit(0)


class WsSignalEngine:
    def __init__(self, rest, _ws, sa=None, ws_uri='ws://localhost:9000', contract_size=0.1, reenter=False,
                 data_source='binance', exclude_markets=None, ws=None):
        self.ws_uri = ws_uri
        # self.ws_signals = WebSocketSignals().ws_signals
        self.portfolio_pct = contract_size
        self.renter = reenter
        self.data_source = data_source
        self.exclude_markets = exclude_markets
        self.api = FtxApi(rest=rest, ws=_ws, sa=sa)
        wsr = WsReceiver(ws_uri, rest, ws, sa, contract_size, reenter, data_source, exclude_markets, True)
        #t = threading.Thread(target=wsr.connect)
        #t.start()
        # self.signals = self.ws_signals

        cp.yellow(f'[~] Connecting to {self.ws_uri} for signals...')
        self.start_process()


class TradeStrategy:
    def __init__(self, strategy, symbol, contract_size, rest, ws, sa=None, symbol_monitor=None):
        self.symbol = symbol
        self.strategy = strategy
        self.size = contract_size
        self.rest = rest
        self.symbol_monitor = symbol_monitor
        self.ws = ws
        self.api = FtxApi(rest=rest, ws=ws, sa=sa)
        cp.yellow(f'[~] Init Trade Strategy {strategy} on symbol {symbol}')

    def check_position_exists_diff(self, future, s):
        for pos in self.api.positions():

            if float(pos['collateralUsed']) == 0.0 and pos['future'] == future:
                print(pos)
                return True
        return False

    def start_process(self):
        cp.yellow('Starting up the ta engine ...')
        if self.strategy == 'sar':
            from trade_engine.aligning_sar import TheSARsAreAllAligning
            sar = TheSARsAreAllAligning(debug=False)
            while True:
                sig = sar.sar_scalper(instrument=self.symbol_monitor)
                if sig:
                    cp.red(f'[signal]: {sig}')
                    if sig == 'long':
                        cp.green('[LONG]: SAR LONG, ENTERING!')
                        if self.check_position_exists_diff(future=self.symbol, s=self.size):
                            self.api.buy_market(market=self.symbol, qty=self.size, reduce=False, ioc=False, cid=None)
                        else:
                            cp.alert('Cannot enter, position already open!')
                    elif sig == 'short':
                        cp.red('[SHORT]: SAR SHORT, ENTERING!')
                        if self.check_position_exists_diff(future=self.symbol, s=self.size):
                            self.api.sell_market(market=self.symbol, qty=self.size, reduce=False, ioc=False, cid=None)
                        else:
                            cp.purple('Cannot enter, position already open!')
                else:
                    cp.purple('[x] No signal')

    def __start_process__(self):
        restarts = 0
        while True:
            try:
                self.start_process()
            except Exception as fuckyou:
                restarts += 1
                print(f'[e] Error: {fuckyou}, restarting strategy. Restart: {restarts}')
                time.sleep(1)


class Monitor:
    def __init__(self, rest, ws, subaccount, sl, tp, ts, offset, reopen, auto, position_step_size=0.02,
                 max_open_orders=None, no_sl=False, show_tickers=False, monitor_only=False, close_method='market',
                 balance_arbitrage=False, long_symbols=None, short_symbols=None, contract_size=0.0, min_spread=0.25,
                 ot='market', use_strategy=False, strategy=None, symbol=None, symbol_monitor=None, enable_ws=False,
                 ws_uri='localhost:9000', reenter=False, data_source='binance', exclude_markets=None):
        self.rest = rest
        self.ws = ws
        self.sl = sl
        self.tp = tp
        self.ts = ts
        self.ot = ot
        self.show_tickers = show_tickers
        self.monitor_only = monitor_only
        self.use_strategy = use_strategy
        self.strategy = strategy
        self.symbol = symbol
        self.symbol_monitor = symbol_monitor
        self.enable_ws = enable_ws
        self.ws_uri = ws_uri
        self.portfolio_pct = contract_size
        self.reenter = reenter
        self.data_source = data_source
        self.exclude_markets = exclude_markets
        self.offset = offset
        self.subaccount = subaccount
        self.lag = 0
        self.a_restarts = 0
        self.lagging = False
        self.files = []
        self.logger = logging.getLogger(__name__)
        self.api = FtxApi(rest=rest, ws=ws, sa=subaccount)
        self.auto = auto
        self.balance_arbitrage = balance_arbitrage
        self.long_symbols = long_symbols
        self.short_symbols = short_symbols
        self.contract_size = contract_size
        self.min_spread = min_spread
        self.max_open_orders = max_open_orders
        self.position_step_size = position_step_size
        self.reopen = reopen
        self.close_method = close_method
        self.no_sl = no_sl
        self.executor = ThreadPoolExecutor(max_workers=15)
        print(type(self.sl), self.sl)
        if self.sl > 0.0:
            self.sl = self.sl * -1

        if self.balance_arbitrage:
            cp.yellow('Starting balance arbitrage engine ...')
            self.osc_arb = OscillationArbitrage(rest=self.rest, ws=self.ws, subaccount=self.subaccount,
                                                min_spread=self.min_spread, contract_size=self.contract_size)
            self.osc_arb.start_process()

        if self.use_strategy:
            cp.yellow('Starting Trade Strategy Engine ...')
            TaTrader = TradeStrategy(strategy=self.strategy, symbol=self.symbol, contract_size=self.contract_size,
                                     rest=self.rest, ws=self.ws, sa=self.subaccount, symbol_monitor=self.symbol_monitor)
            self.executor.submit(TaTrader.__start_process__)

        if self.enable_ws:
            cp.purple('[ws] Starting the websocket receiver.')
            ws_server = WsReceiver(server_uri=self.ws_uri, rest=self.rest, _ws=self.ws, sa=self.subaccount, contract_size=contract_size, reenter=reenter,
                           data_source=data_source, exclude_markets=exclude_markets)

            t = threading.Thread(target=ws_server.connect)
            t.start()

        if self.auto:
            cp.navy(data='Starting auto trader')
            self.auto_trade = AutoTrader(self.api, stop_loss=self.sl, _take_profit=self.tp, use_ts=self.ts,
                                         ts_pct=self.offset, max_open_orders=self.max_open_orders,
                                         position_step_size=self.position_step_size, reopen=self.reopen,
                                         disable_stop_loss=self.no_sl, show_tickers=self.show_tickers,
                                         monitor_only=self.monitor_only, close_method=close_method, ot=self.ot)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        for file in self.files:
            os.unlink(file)

    def start_auto_trade(self):
        cp.navy('[☠] Starting auto trader...')
        self.executor.submit(self.auto.start_process)
        cp.navy('[☑] Started ...')

    def monitor(self):
        c = 0
        tt = 0
        current_time = 0
        running = True
        time.sleep(0.25)
        if self.auto:
            self.auto_trade.start_process()
        while running:
            try:
                ticker = self.ws.get_ticker(market='BTC-PERP')
            except Exception as fuck:
                self.logger.error(f'Ticker Error {fuck}, lets hope its transient!')
            else:
                if not ticker:
                    pass
                else:

                    last_time = datetime.datetime.utcfromtimestamp(ticker['time']).second
                    current_time = datetime.datetime.utcnow().second.real
                    self.lag = last_time - current_time

            if self.lag >= 10 and current_time > 0:
                self.logger.critical('WS is lagging {} second(s), we are going down!'.format(self.lag))
                running = False

            c += 1
            if c % 2000000 == 0:
                tt += 1


class Bot:

    def api_connection(self, key, secret, subaccount):
        global ws
        global rest
        ws = ws_client.FtxWebsocketClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        rest = client.FtxClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        return rest, ws

    def con(self, key, secret, subaccount_name=None, args=None):
        api = self.api_connection(key=key, secret=secret, subaccount=subaccount_name)
        rest = api[0]
        ws = api[1]

        return Monitor(rest=rest, ws=ws, subaccount=subaccount_name, sl=args.stop_loss_pct, tp=args.take_profit_pct,
                       offset=args.ts_offset, auto=args.auto_trader, ts=args.use_trailing_stop,
                       max_open_orders=args.num_open_orders, reopen=args.reopen_method, no_sl=args.disable_stop_loss,
                       show_tickers=args.show_tickers, monitor_only=args.monitor_only, close_method=args.close_method,
                       balance_arbitrage=args.balance_arbitrage, ot=args.order_type, use_strategy=args.use_strategy,
                       strategy=args.strategy, symbol=args.symbol, contract_size=args.contract_size,
                       enable_ws=args.enable_ws, ws_uri=args.ws_uri,
                       reenter=args.reenter, data_source=args.data_source, exclude_markets=args.exclude_markets)

    def monitor(self, key, secret, subaccount_name=None, args=None):
        restarts = 0

        while True:
            with self.con(key=key, secret=secret, subaccount_name=subaccount_name, args=args) as ftx:
                try:
                    cp.navy('[🌡] Monitoring...')
                    ftx.monitor()
                    cp.red('Done...')
                except KeyboardInterrupt:
                    ftx.__exit__()
                    print('Exiting...')
                    cp.red(1)
                except FtxDisconnectError as err:
                    ftx.__exit__()
                    restarts += 1
                    cp.red(f'Disconnected: {restarts}  {err}')
                except Exception as err:
                    ftx.__exit__()
                    cp.red(f'Unknown Error: {err}, restarting ... ')
                    print(repr(err))
                    restarts += 1
                    cp.red(f'Disconnected: {restarts}')


class InteractiveParser:
    # general opts
    monitor = False  # bool
    subaccount = None  # str
    verbose = False  # bool
    show_tickers = False  # bool
    # strategy opts
    use_strategy = False  # bool
    strategy = 'SAR'  # choices - str - SAR is only current strategy
    symbol = None  # ftx symbol - string 'BTC-PERP'
    symbol_monitor = None  # binance pair - string - 'BTCUSDT
    contract_size = 0.0  # for TA trading, how much (ie BTC) should we buy (like .01)
    # balance arb
    balance_arbitrage = False
    order_type = 'market'
    reenter = False
    data_source = 'binance'
    exclude_markets = None
    enable_ws = False
    ws_uri = False
    long_symbols = []
    short_symbols = []
    min_spread = 0.0
    # auto trader opts
    auto_trader = False  # bool
    monitor_only = True  # bool
    confirm = False  # bool
    disable_stop_loss = False  # bool
    stop_loss_pct = 0.5  # float
    take_profit_pct = 3.0  # float
    use_trailing_stop = True  # bool
    ts_offset = 0.005  # float
    reopen_method = 'market'  # choices, market, increment, None
    close_method = 'market'  # choices, market, increment
    increment_period = 300  # choices, [15, 60, 300, 900, 3600, 14400, 86400]
    num_open_orders = 4  # int
    position_step_size = 0.02  # float


def interactive_call(_args):
    """
    Interactively start the monitor and whatever else
    :param args:
    :return:
    """
    global cp
    _args_ = _args

    bot = Bot()
    cp = NewColorPrint()
    t = threading.Thread(target=bot.monitor, args=(key, secret, subaccount, _args_))
    t.start()


"""
Example usage of interactive_call:
1) assign the InteractiveParser variables
2) Treat this like its an argparse object
3) Pass it to interactive_call
"""


def main():
    global cp
    global ARE_YOU_CERTAIN
    bot = Bot()
    cp = NewColorPrint()
    args = get_args()
    limit_price = 0
    if args.confirm:
        ARE_YOU_CERTAIN = True
        args.monitor_only = False
        for _ in range(0, 3):
            cp.random_color(f'[ATTENTION!] You have specified `--confirm` which means that *THIS BOT WILL DO THINGS '
                            f'AUTOMATICALLY* which will either MAKE or COST you money! You have been WARNED!',
                            static_set='bright')
            time.sleep(0.125)
    else:
        ARE_YOU_CERTAIN = False
        args.monitor_only = True

    if args.balance_arbitrage:
        cp.navy('Loading balance arbitrage engine...')
        bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)
    if args.use_strategy:
        cp.navy(f'Loading TA Strategy Trader ... Strategy: {args.strategy}')
        bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

    if args.enable_ws:
        cp.yellow('Enabling ws signal client')
        bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

    if args.auto_trader or args.monitor:
        #logo.post()
        cp.yellow('[📊] Loading auto trader ... ')
        if not args.confirm:
            cp.purple(f'[~] Monitor only mode. Run with --really to actually trade.')
        else:
            cp.red(f'[!] WARN: Autotrader is enabled! This cam make or cost you money.')
        if args.show_tickers:
            cp.green('[~] Tickers Enabled!')
        bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

    if args.show_portfolio or args.buy or args.sell or args.cancel or args.open_orders:
        api = bot.api_connection(key=key, secret=secret, subaccount=subaccount)
        rest = api[0]
        ws = api[1]
        api = FtxApi(rest=rest, ws=ws, sa=subaccount)
        if args.show_portfolio:
            balances = api.parse_balances()
            cp.yellow('Account Balances:')
            print(balances)
        if args.open_orders:
            cp.yellow('Querying API for open orders...')
            orders = api.get_orders()
            print(orders)

        if args.buy:
            if len(args.buy) < 3:
                cp.red('[⛔] Required parameters: <order type> <market> <qty> Optional Parameters: <price>')
                return False
            else:
                o_type = args.buy[0]
                o_market = args.buy[1]
                o_size = args.buy[2]
                if len(args.buy) == 4:
                    limit_price = args.buy[3]
                if o_type == 'market':
                    cp.green(f'[~] Executing a market buy order on {o_market} of quantity {o_size}!')
                    ret = api.buy_market(market=o_market, qty=o_size, reduce=False, ioc=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
                if o_type == 'limit':
                    if limit_price == 0:
                        bid, ask, last = api.get_ticker(market=o_market)
                        limit_price = bid
                        cp.red(f'[!] No price given, using current bid: {bid}')

                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    ret = api.buy_limit(market=o_market, qty=o_size, price=limit_price, reduce=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')

        if args.sell:
            if len(args.sell) < 3:
                cp.red('[⛔] Required parameters: <order type> <market> <qty> Optional Parameters: <price>')
                return False
            else:
                o_type = args.sell[0]
                o_market = args.sell[1]
                o_size = args.sell[2]
                if len(args.sell) == 4:
                    limit_price = args.sell[3]
                if o_type == 'market':
                    cp.red(f'[~] Executing a market sell order on {o_market} of quantity {o_size}!')
                    ret = api.sell_market(market=o_market, qty=o_size, reduce=False, ioc=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
                if o_type == 'limit':
                    if limit_price == 0:
                        bid, ask, last = api.get_ticker(market=o_market)
                        limit_price = ask
                        cp.yellow(f'[!] No price given, using current ask: {ask}')
                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    ret = api.sell_limit(market=o_market, qty=o_size, price=limit_price, reduce=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
        if args.cancel:
            oid = args.cancel
            cp.red(f'[c] Canceling order #{oid}')
            ret = api.cancel_order(oid=oid)
            if ret:
                cp.purple(f'[~] Status: {ret}')


if __name__ == '__main__':
    main()

