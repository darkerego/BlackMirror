import logging
import re
import threading
import time
import sys
from utils.colorprint import NewColorPrint
from trade_engine.stdev_aggravator import FtxAggratavor
from lib.exceptions import *
from utils import profit_tracker
from lib.func_timer import exit_after, cdquit
from lib import sql_lib
from concurrent.futures import ThreadPoolExecutor
from lib.score_keeper import scores

try:
    import thread
except ImportError:
    import _thread as thread

debug = True

import threading


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, *init_args, **init_kwargs):
        threading.Thread.__init__(self, *init_args, **init_kwargs)
        self._return = None
    def run(self):
        self._return = self._target(*self._args, **self._kwargs)
    def join(self):
        threading.Thread.join(self)
        return self._return


def logwrapper(func):
    '''Decorator that reports the execution time.'''

    def wrap(*args, **kwargs):
        for a in kwargs:
            if a == 'n':
                print(a)
        result = func(*args, **kwargs)
        #end = time.time()

        #print(func.__name__, end - start)
        return result

    return wrap


@logwrapper
def countdown(n):
    '''Counts down'''
    while n > 0:
        n -= 1


class Tally:
    wins = 0
    losses = 0


tally = Tally()

class AutoTrader:
    """
    Automatic Trade Engine. Automatically sets stop losses and take profit orders. Trailing stops are used
    unless otherwise specified.
    """

    def __init__(self, api, stop_loss, _take_profit, use_ts=True, ts_pct=0.05, reopen=False, period=300, ot='limit',
                 max_open_orders=None, position_step_size=0.02, disable_stop_loss=False, show_tickers=True,
                 monitor_only=False, close_method='market', relist_iterations=100, hedge_mode=False, hedge_ratio=0.5,
                 max_collateral=0.5, position_close_pct=1, chase_close=0, chase_reopen=0, update_db=False, anti_liq=False,
                 min_score=0.0, check_before_reopen=False):
        self.cp = NewColorPrint()
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
        self.tally = tally
        self.wins = self.tally.wins
        self.losses = self.tally.losses
        self.accumulated_pnl = 0
        self.pnl_trackers = []
        self.position_close_pct = position_close_pct
        self.chase_close = chase_close
        self.chase_reopen = chase_reopen
        self.min_score = min_score
        self.check_before_reopen = check_before_reopen

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
        self.relist_iterations = relist_iterations
        self.hedge_mode = hedge_mode
        self.hedge_ratio = hedge_ratio
        self.max_collateral = max_collateral
        self.delta_weight = None
        self.sql = sql_lib.SQLLiteConnection()
        self.relist_iter = {}
        self.update_db = update_db
        self.open_positions = {}
        self.ta_scores = scores
        if self.reopen:
            self.cp.yellow('Reopen enabled')
        if self.stop_loss > 0.0:
            self.stop_loss = self.stop_loss * -1

        if self.hedge_mode:
            if self.hedge_ratio < 0:
                self.delta_weight = 'short'
            else:
                self.delta_weight = 'long'
            self.cp.green(f'[~] Hedged Trading Mode Enabled.')
            self.cp.yellow(f'[/] Hedge Ratio: {self.hedge_ratio}, Delta: {self.delta_weight}')
        if self.monitor_only:
            self.cp.red('[!] Monitor Only enabled. Will NOT trade.')

    def sanity_check(self, positions):
        print(f'[~] Performing sanity check ...')
        for pos in positions:
            if float(pos['collateralUsed'] != 0.0) or float(pos['longOrderSize']) > 0 or float(
                    pos['shortOrderSize']) < 0:
                instrument = pos['future']
                self.api.cancel_orders(market=instrument, limit_orders=True)

    def api_trailing_stop(self, market, qty, entry, side, offset=.25, ts_o_type='market'):
        """
        {
              "market": "XRP-PERP",
              "side": "sell",
              "trailValue": -0.05,
              "size": 31431.0,
              "type": "trailingStop",
              "reduceOnly": false,
            }
        """
        entry_price = entry
        qty = qty
        print('Trailing stop triggered')
        if side == 'buy':
            current_price = self.api.get_ticker(market=market)[1]
            trail_value = (current_price - entry) * self.trailing_stop_pct * -1
            # offset_price = (float(current_price) - float(entry_price)) * (1-offset)
            offset_price = current_price - (current_price - entry) * offset
            text = f'Trailing sell stop for long position, type {ts_o_type}'
            # self.cp.yellow(f'[~] Taking {self.position_close_pct}% of profit ..')

            # qty = qty * (self.take_profit_pct / 100)
            # qty = qty * -1
            opp_side = 'sell'
            self.cp.green(
                f'Trailing Stop for long position of entry price: {entry_price} triggered: offset: {offset_price}'
                f' current price: {current_price}, qty: {qty}')

            ret = self.api.trailing_stop(market=market, side=opp_side, trail_value=trail_value, size=float(qty), reduce_only=True)
            print(ret)
            return ret

        else:
            # short position, so this will be a buy stop
            # side = 'buy'
            current_price = self.api.get_ticker(market=market)[0]
            trail_value = (entry - current_price) * self.trailing_stop_pct
            # offset_price = (float(current_price) + float(offset))
            offset_price = current_price + (entry - current_price) * offset
            text = f'Trailing buy stop for short position, type {ts_o_type}'

            opp_side = 'buy'
            self.cp.red(
                f'Trailing Stop for short position of entry price: {entry_price} triggered: offset price {offset_price}'
                f' current price: {current_price}, qty: {qty}')

            ret = self.api.trailing_stop(market=market, side=opp_side, trail_value=trail_value, size=float(qty), reduce_only=True)
            print(ret)
            return ret

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
            #self.cp.yellow(f'[~] Taking {self.position_close_pct}% of profit ..')

            # qty = qty * (self.take_profit_pct / 100)
            # qty = qty * -1
            opp_side = 'sell'
            self.cp.green(
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

            opp_side = 'buy'
            self.cp.red(
                f'Trailing Stop for short position of entry price: {entry_price} triggered: offset price {offset_price}'
                f' current price: {current_price}')

        while True:
            if side == "sell":
                sell_price = self.api.get_ticker(market=market)[1]
                if (float(sell_price) - float(offset)) > float(offset_price):
                    offset_price = float(sell_price) - float(offset)
                    self.cp.purple("New low observed: %.8f Updating stop loss to %.8f" % (sell_price, offset_price))
                elif float(sell_price) <= float(offset_price):
                    sell_price = self.api.get_ticker(market=market)[1]
                    """if tschase:
                        self.logger.info(f'Chasing sell order ... max chase: {max_chase}')
                        self.logger.info("Sell triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, sell_price,
                                                                                                 offset_price))
                        chaser = threading.Thread(target=self.limit_chase, args=(qty, max_chase, True))
                        chaser.start()
                    "else:"""
                    self.cp.purple("Buy triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, sell_price,
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
                    self.cp.purple(
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
                    self.cp.purple("Sell triggered: %s | Price: %.8f | Stop loss: %.8f" % (ts_o_type, current_price,
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
            self.cp.red('[!] Stop hit!')
            ret = self.api.sell_market(market=market, qty=size, reduce=True, ioc=False, cid=None)
            return ret
        else:
            # market buy # marekt, qty, reduce, ioc, cid
            self.cp.red('[!] Stop hit!')

            ret = self.api.buy_market(market=market, qty=size, reduce=True, ioc=False, cid=None)
            return ret

    def api_stop_loss(self, market, side, size, limit_price=None):
        if limit_price is None:
            self.api.stop_loss(market, side, size, reduce_only=True)
        else:
            self.api.stop_loss(market, side, size, reduce_only=True)

    def api_take_profit(self, market, side, size, trigger_price, order_price=None, reduce_only=True):

        self.api.take_profit(market, side, size, trigger_price, order_price, reduce_only)

    def take_profit(self, market: str, side: str, entry: float, size: float, order_type: str = 'limit'):
        ticker = self.api.get_ticker(market=market)
        bid = price = float(ticker[0])
        ask = inverse = float(ticker[1])

        if side == 'buy':
            opp_side = 'sell'
            trail_value = ((ask - entry) * self.trailing_stop_pct) * -1
            if self.use_ts:
                self.cp.white_black(f'[฿] Sending a trailing stop: {trail_value}')
                ret = self.api_trailing_stop(market=market, side=side, qty=size, offset=self.trailing_stop_pct, entry=entry,
                                         ts_o_type=self.order_type)
                if ret:
                    print('Success at take profit')
                    self.wins += 1
                    return True
            else:

                if order_type == 'market':  # market, qty, reduce, ioc, cid):
                    self.cp.yellow(f'[฿] Sending a market order, side: {opp_side}, price: {price}')
                    ret = self.api.sell_market(market=market, qty=size, ioc=False, reduce=True)
                else:  # market, qty, price=None, post=False, reduce=False, cid=None):
                    self.cp.purple(f'[฿] Sending a limit order, side: {opp_side}, price: {price}')
                    ret = self.api.sell_limit(market=market, qty=size, price=ask, reduce=True)
                    self.wins += 1
                    return ret
        else:  # side == sell
            opp_side = 'buy'
            trail_value = (entry - bid) * self.trailing_stop_pct
            if self.use_ts:
                self.cp.green(f'[฿] Sending a trailing stop: {trail_value}')
                # executor = ThreadPoolExecutor(max_workers=5)
                # ret = executor.submit(self.trailing_stop, market=market, side=opp_side, qty=float(o_size),
                #                      entry=float(entry), offset=float(self.trailing_stop_pct))
                ret = self.api_trailing_stop(market=market, side=side, qty=size, offset=self.trailing_stop_pct, entry=entry,
                                         ts_o_type=self.order_type)

                if ret:
                    self.cp.purple(f'[~] Success at taking profit.')
                    self.wins += 1
                    return True

            else:

                if order_type == 'market':
                    self.cp.purple(f'[฿] Sending a market order, side: {opp_side}, price: {price}')
                    ret = self.api.buy_market(market=market, side=opp_side, size=size,
                                              _type='market', ioc=False, reduce=True)
                    self.wins += 1
                    return ret
                else:
                    self.cp.purple(f'[฿] Sending a limit order, side: {opp_side}, price: {price}')
                    ret = self.api.buy_limit(market=market, qty=size, price=ask, reduce=True)
                    self.wins += 1
                    return ret
        self.cp.red(f"[฿]: ({ret}")

        return ret

    def take_profit_wrap(self, market: str, side: str, entry: float, size: float, order_type: str = 'limit'):

        open_orders = self.api.rest_get_open_orders(market=market)
        open_buy = []
        open_sell = []
        if side == 'buy':
            opp_side = 'sell'
        elif side == 'sell':
            opp_side = 'buy'

        for o in open_orders:
            _side = o['side']
            if _side == 'buy':
                open_buy.append(o)
            if _side == 'sell':
                open_sell.append(o)

        print(f'[~] {len(open_orders)} orders on market: {market} open currently ... ')
        #for o in open_orders:
        #    print(f'DEBUG: {o}')
        if not self.relist_iter.get(market):
            self.relist_iter[market] = 0
        if len(open_orders) and self.relist_iter[market] == self.relist_iterations:
            self.api.cancel_orders(market=market, limit_orders=True)
        if len(open_orders) and self.relist_iter[market] < self.relist_iterations:
            self.relist_iter[market] += 1
            leftover_iterations = self.relist_iterations - self.relist_iter[market]
            self.cp.blue(f'[!] We have open orders, relisting in {leftover_iterations} iterations.  ... ')
            return
        if self.relist_iter[market] == self.relist_iterations:
            self.relist_iter[market] = 0

        if self.close_method == 'increment':

            return self.increment_orders(market=market, side=opp_side, qty=size, period=self.period, reduce=True)
        elif self.close_method == 'market' or self.close_method == 'limit':
            return self.take_profit(market=market, side=side, entry=entry, size=size, order_type=order_type)

    def re_open_limit(self, market, side, qty):
        for _ in range(9):
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
        for i in range(9):
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
        open_buy_order_count = 0
        open_sell_order_count = 0
        current_buy_orders_qty = 0
        current_sell_orders_qty = 0
        open_order_count = self.api.rest_get_open_orders(market=market)

        for o in open_order_count:
            o_side = o.get('side')
            if o_side == 'buy':
                open_buy_order_count += 1
                current_buy_orders_qty += o.get('size')
            else:
                open_sell_order_count +=1
                current_sell_orders_qty += o.get('size')
        self.cp.yellow(f'[i] Open Orders: {len(open_order_count)}, Qty Given: {qty}, Current open Qty: {current_size}')

        #if len(open_order_count) > self.max_open_orders * 2:
        #    self.api.cancel_orders(market=market)

        buy_orders = []
        sell_orders = []
        max_orders = self.max_open_orders
        stdev = self.agg.get_stdev(symbol=market, period=period)
        self.cp.yellow(f'Standard deviation: {stdev}')
        stdev_each_side = stdev / 2

        #o_qty = qty / max_orders
        o_qty = qty

        # self.cp.red(f'[!] Killing {open_order_count} currently open orders...')
        # while qty > (qty * 0.95):
        buy_order_que = []
        sell_order_que = []
        if side == 'buy':
            if open_buy_order_count == self.max_open_orders:
                print('Not doing anything as max orders ..')
                return
            min_qty = self.future_stats[market]['min_order_size']
            bid, ask, last = self.api.get_ticker(market=market)
            # print(bid, ask, last)
            # last_order_price = bid - (deviation * self.position_step_size)
            for i in range(max_orders):
                qty -= qty / 2
                if qty < min_qty:
                    if i == 0:
                        self.cp.red(f'[!] Order size {qty} is too small for {market}, min size: {min_qty}')
                        return False
                    else:
                        buy_orders[-1] += qty
                        break
                else:
                    buy_orders.append(qty)

            buy_orders = [x for x in buy_orders.__reversed__()]
            # print(buy_orders)
            c = 1
            for i in buy_orders:
                if c == 1:
                    next_order_price = bid
                    buy_order_que.append(['buy', i, next_order_price, market, 'limit'])
                else:
                    next_order_price = bid - (stdev * self.position_step_size) * c
                    buy_order_que.append(['buy', i, next_order_price, market, 'limit'])
                c += 1
                self.cp.yellow(f'[o] Placing new {side} order of size {i} on market {market} at price {next_order_price}')
                for x in range(10):  # market, qty, price=None, post=False, reduce=False, cid=None):
                    try:
                        status = self.api.buy_limit(market=market, price=next_order_price, qty=i,
                                                    reduce=reduce, cid=None)
                    except Exception as err:
                        print(f'[!] Error placing limit order: {err}')
                    else:
                        if status:
                            self.cp.red(f"[฿]: {status.get('id')}")
                            break
                        else:
                            time.sleep(0.25)
            # self.cp.debug(f'Debug: : Buy Orders{buy_orders}')
            return True


        else:
            if open_sell_order_count == self.max_open_orders:
                print('Not doing anything as max open sell orders')
                return
            min_qty = self.future_stats[market]['min_order_size']
            bid, ask, last = self.api.get_ticker(market=market)
            # print(bid, ask, last)
            # last_order_price = bid - (deviation * self.position_step_size)
            for i in range(max_orders):
                qty -= qty / 2
                if qty < min_qty:
                    if i == 0:
                        self.cp.red(f'[!] Order size {qty} is too small for {market}, min size: {min_qty}')
                        return False
                    else:
                        sell_orders[-1] += qty
                        break
                else:
                    sell_orders.append(qty)

            sell_orders = [x for x in sell_orders.__reversed__()]
            # print(sell_orders)
            c = 1
            for i in sell_orders:
                if i == 1:
                    next_order_price = ask
                    sell_order_que.append(['sell', i, next_order_price, market, 'limit'])
                else:
                    next_order_price = ask + (stdev * self.position_step_size) * c
                    sell_order_que.append(['sell', i, next_order_price, market, 'limit'])
                c += 1
                self.cp.yellow(f'[o] Placing new {side} order of size {i} on market {market} at price {next_order_price}')
                for x in range(10):  # market, qty, price=None, post=False, reduce=False, cid=None):
                    try:
                        status = self.api.sell_limit(market=market, price=next_order_price, qty=i,
                                                    reduce=reduce, cid=None)
                    except Exception as fuck:
                        print(f'[!] Error:', fuck)
                    else:
                        if status:
                            self.cp.purple(f"[฿]: ({status['id']}")
                            break
                        else:
                            time.sleep(0.25)
            # self.cp.debug(f'Debug: : Sell Orders{sell_orders}')
            return True

    def reopen_pos(self, market, side, qty, period=None, info=None):
        coll = info["collateral"]
        free_coll = info["freeCollateral"]
        new_qty = 0
        self.cp.yellow(f'[~] Taking {self.position_close_pct}% of profit ..')
        # qty = (qty * self.position_close_pct)
        if self.hedge_mode:
            self.cp.blue(f'[⌖] Hedge Mode Enabled ... ')
            if self.hedge_ratio > 0:
                # delta long
                max_allocate_short = (coll * (1 - float(self.hedge_ratio)) * self.max_collateral)
                max_allocate_long = (coll * (float(self.hedge_ratio)) * self.max_collateral)
                if qty > max_allocate_long:
                    new_qty = (free_coll * (float(self.hedge_ratio)) * self.max_collateral)
                    self.cp.red(f'[~] Δ+ Notice: recalculated position size from {qty} to {new_qty}  ... ')
                elif qty > max_allocate_short:
                    new_qty = (free_coll * (1 - float(self.hedge_ratio)) * self.max_collateral)
                    self.cp.red(f'[~] Δ+ Notice: recalculated position size from {qty} to {new_qty}  ... ')
            elif self.hedge_ratio < 0:
                # delta short
                max_allocate_short = (coll * (1 - float(self.hedge_ratio) * -1) * self.max_collateral)
                max_allocate_long = (coll * (float(self.hedge_ratio) * -1) * self.max_collateral)

                if qty > max_allocate_long:
                    new_qty = (free_coll * (float(self.hedge_ratio) * -1) * self.max_collateral) # invert if negative
                    self.cp.red(f'[~] Δ- Notice: recalculated position size from {qty} to {new_qty} from  ... ')
                elif qty > max_allocate_short:
                    new_qty = (free_coll * (1 - float(self.hedge_ratio)) * self.max_collateral)
                    self.cp.red(f'[~] Δ- Notice: recalculated position size from {qty} to {new_qty}  ... ')

            else:
                max_allocate = (coll * 0.5 * self.max_collateral)
                if qty > max_allocate:
                    new_qty = (free_coll * 0.5 * self.max_collateral)
                    self.cp.red(f'[~] Δ Notice: recalculated position size from {qty} to {new_qty}  ... ')
        if new_qty:
            qty = new_qty

        if self.check_before_reopen:
            ta_score = self.ta_scores.get(market)
            if ta_score:
                if ta_score.get('status') == 'closed':
                    print(f'[!] Not reopening because the signal has closed.')
                    return False
                if ta_score.get('score') <= self.min_score:
                    print(f'[!] Not reopening because the score is too low.')
                    return False
            else:
                print(f'[!] Score not available. Bailing.')
                return
        if self.order_type == 'limit' and self.reopen != 'increment':
            return self.re_open_limit(market, side, qty)
        if self.order_type == 'market' and self.reopen != 'increment':
            return self.re_open_market(market, side, qty)
        if self.reopen == 'increment':
            return self.increment_orders(market, side, qty, period)

    def pnl_calc(self, qty, sell, buy, side, cost, future_instrument, fee=0.00019):
        """
        Profit and Loss Calculator - assume paying
         two market fees (one for take profit, one for re-opening). This way we can
         set tp to 0 and run as market maker and make something with limit orders.
        """
        if fee <= 0:
            pnl = float(qty * (sell - buy) * (1 - fee))
        else:
            pnl = float(qty * (sell - buy) * (1 - (fee * 2)))
        if pnl is not None:  # pythonic double negative nonsense
            if side == 'buy':
                try:
                    if pnl <= 0.0:
                        self.cp.red(f'[🔻] Negative PNL {pnl} on position {future_instrument}')
                    else:
                        self.cp.green(f'[🔺] Positive PNL {pnl} on position {future_instrument}')
                except Exception as err:
                    print('Error calculating PNL: ', err)
                else:
                    try:
                        pnl_pct = (float(pnl) / float(cost)) * 100
                    except Exception as err:
                        print('Error calculating PNL%: ', err)
                    else:
                        return pnl, pnl_pct
            else:
                try:
                    pnl_pct = (float(pnl) / float(cost * -1)) * 100
                except Exception as err:
                    print('DEBUG Error calculating PNL line 683: ', err)
                else:
                    return pnl, pnl_pct
            return 0.0, 0.0

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
        if not self.open_positions.get(future_instrument):
            self.open_positions[future_instrument] = time.time()
            #print('Init')

        if time.time() - self.open_positions.get(future_instrument) < 2:
            #print('Returning')
            return

        pnl_track = profit_tracker.SessionProfits(instrument=future_instrument)
        size = 0
        if debug:
            self.cp.white_black(f'[d]: Processing {future_instrument}')
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
            err = None
            if self.update_db:
                print('[~] Updating ..')
                current = self.sql.get_list(table='futures')
                entry = {'instrument': {'name': self.future_stats['name'], 'min_order_size': self.future_stats['min_order_size']}}
                if current.__contains__(entry):
                    pass
                else:
                    self.sql.append(entry, table='futures')
                exit()
            # if not self.ticker_stats.__contains__(name):
            #    name = FutureStat(name=name, price=mark_price, volume=volumeUsd24h)
            #    self.ticker_stats.append(name)
            # else:
            #    p, v = name.update(price=mark_price, volume=volumeUsd24h)

            # if self.show_tickers:
            if f['name'] == future_instrument:
                if debug:
                    self.cp.dark(
                        f"[🎰] [{name}] Future Stats: {change1h}/hour {change24h}/today, Volume: {volumeUsd24h}")
                # print(f'Debug: {f}')
            if float(change1h) > 0.025 and self.show_tickers:
                if float(change24h) > 0:
                    self.cp.ticker_up(
                        f'[🔺]Future {name} is up {change1h} % this hour! and {change24h} today, Volume: {volumeUsd24h}, ')


                else:
                    self.cp.ticker_up(f'[🔺] Future {name} is up {change1h} % this hour!')

            if change1h < -0.025 and self.show_tickers:
                if float(change24h) < 0:
                    self.cp.ticker_down(
                        f'[🔻]Future {name} is down {change1h} % this hour!and {change24h} today, Volume: {volumeUsd24h}!')
                else:
                    self.cp.ticker_down(f'[🔻] Future {name} is down {change1h} % this hour!')

            if change24h > 0:
                self.up_markets[name] = (volumeUsd24h, change1h)
            elif change24h < 0:
                self.down_markets[name] = (volumeUsd24h, change1h)

        if len(self.up_markets) > len(self.down_markets):
            if self.show_tickers:
                self.cp.green('[+] Market Average Trend: LONG')
            self.trend = 'up'
        if len(self.up_markets) == len(self.down_markets):
            if self.show_tickers:
                self.cp.yellow('[~] Market Average Trend: NEUTRAL')
        if len(self.up_markets) < len(self.down_markets):
            if self.show_tickers:
                self.cp.red('[-] Market Average Trend: SHORT')
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
        pnl = 0
        pnl_pct = 0
        tpnl = 0
        tsl = 0
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
                pnl, pnl_pct = self.pnl_calc(qty=(size * -1), sell=avg_open_price, buy=bid, side=side,
                                             cost=cost, future_instrument=future_instrument, fee=takerFee)
            except Exception as err:
                print('DEBUG Error calculating PNL line 647: ', err)


        else:
            # short position
            side = 'sell'
            pos_side = 'buy'
            ask, bid, last = self.api.get_ticker(market=future_instrument)
            if not bid:
                return
            current_price = ask
            current_price_inverse = bid
            pnl, pnl_pct = self.pnl_calc(qty=(size * -1), sell=avg_open_price, buy=bid, side=side,
                                         cost=cost, future_instrument=future_instrument, fee=takerFee)
            try:
                if pnl <= 0.0:
                    self.cp.red(f'[🔻] Negative PNL {pnl} on position {future_instrument}')
                else:
                    self.cp.green(f'[🔺] Positive PNL {pnl} on position {future_instrument}')
            except Exception as err:
                print('DEBUG Error calculating PNL line 677: ', err)
                pass

        self.cp.random_pulse(
            f'[▶] Instrument: {future_instrument}, Side: {side}, Size: {size} Cost: {cost}, Entry: {entry_price},'
            f' Open: {avg_open_price} Liq: {liq_price}, BreakEven: {avg_break_price}, PNL: {recent_pnl}, '
            f'UPNL: {unrealized_pnl}, Collateral: {collateral_used}')
        if recent_pnl is None:
            return

        if pnl_pct > self._take_profit:

            print(f'Target profit level of {self._take_profit} reached! Calculating pnl')
            if float(size) < 0.0:
                size = size * -1

            o_size = size
            self.total_contacts_trade += (o_size * last)
            new_qty = size * self.position_close_pct
            if float(new_qty) < float(self.future_stats[name]['min_order_size']):
                new_qty = size
            self.cp.purple(f'Sending {pos_side} order of size {new_qty} , price {current_price}')
            if self.monitor_only:
                self.cp.red('[!] Not actually trading... ')

            else:

                try:

                    ret = self.take_profit_wrap(entry=entry_price, side=side, size=new_qty, order_type=self.order_type,
                                            market=future_instrument)
                except Exception as err:
                    print('ERROR', err)
                    if re.match(r'^(.*)margin for order(.*)$',
                                err.__str__()):
                        self.cp.red('[!] Not enough margin!')
                        ret = False
                    elif re.match(r'^(.*)Size too small(.*)$', err.__str__()):
                        qty = size
                        self.cp.red('[!] Size too small! Fail ...')
                    else:
                        self.cp.red(f'[!] Error with order: {err}')
                else:
                    if ret:
                        self.accumulated_pnl += pnl

                        self.cp.alert('----------------------------------------------')
                        self.cp.alert(f'Total Session PROFITS: {self.accumulated_pnl}')
                        self.cp.alert('----------------------------------------------')
                        self.cp.green(
                            f'Reached target pnl of {pnl_pct} on {future_instrument}, taking profit... PNL: {pnl}')
                        self.total_contacts_trade += (new_qty * last)

                        print('[🃑] Success')

                    if ret and self.reopen:
                        # self.accumulated_pnl += pnl
                        self.cp.yellow(f'Reopening .... {side} {new_qty}')
                        try:
                            ret = self.reopen_pos(market=future_instrument, side=side, qty=new_qty, period=self.period, info=info)
                        except Exception as err:
                            print(err)
                            #if re.match(r'^(.*)margin for order(.*)$', err.__str__()):
                            self.cp.red(f'[~] Error with order: {err.__str__()}')
                        else:

                            if ret:
                                self.total_contacts_trade += (new_qty * last)
                                print('[🃑] Success')
        else:
            try:
                tpnl = (self._take_profit / pnl_pct) * pnl
            except ZeroDivisionError:
                pass

            try:
                tsl = (self.stop_loss / pnl_pct) * pnl
            except ZeroDivisionError:
                pass

            self.cp.yellow(
                f'[$]PNL %: {pnl_pct}/Target %: {self._take_profit}/Target Stop: {self.stop_loss}, PNL USD: {pnl}, '
                f'Target PNL USD: ${tpnl}, Target STOP USD: ${tsl}')
            if pnl_pct < self.stop_loss and not self.disable_stop_loss:
                if self.monitor_only:
                    self.cp.red('[!] NOT TRADING: Stop Hit.')
                else:
                    self.stop_loss_order(market=future_instrument, side=side, size=size * -1)
                self.accumulated_pnl -= pnl

    @exit_after(30)
    def position_parser(self, positions, account_info):
        for pos in positions:

            if float(pos['collateralUsed'] != 0.0) or float(pos['longOrderSize']) > 0 or float(
                    pos['shortOrderSize']) < 0:
                self.parse(pos, account_info)
            else:
                try:
                    for _ in self.open_positions:
                        if pos['future'] == _:

                            self.open_positions.pop(_)
                except:
                    pass




    def start_process_(self):

        restarts = 0
        _iter = 0
        while True:
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
                err = None
                if self.update_db:
                    print('[~] Updating ..')
                    current = self.sql.get_list(table='futures')
                    entry = {'instrument': {'name': self.future_stats['name'],
                                            'min_order_size': self.future_stats['min_order_size']}}
                    if current.__contains__(entry):
                        pass
                    else:

                        self.sql.append(entry, table='futures')
                    exit()
            _iter += 1
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

            except KeyboardInterrupt:
                print('[~] Caught Sigal...')
                exit(0)

            except Exception as err:
                _iter = 0
                print(f'[!] Error: {err}')

            else:
                if _iter == 1:
                    restarts += 1
                    self.cp.purple('[i] Starting AutoTrader, performing sanity check. ...')
                    self.sanity_check(positions=pos)
                self.cp.pulse(f'[$] Account Value: {info["totalAccountValue"]} Collateral: {info["collateral"]} '
                              f'Free Collateral: {info["freeCollateral"]}, Contracts Traded: {self.total_contacts_trade}'
                              f' Restarts: {restarts}')
                if self.wins != 0 or self.losses != 0:
                    self.cp.white_black(f'[🃑] Wins: {self.wins} [🃏] Losses: {self.losses}')
                else:
                    self.cp.white_black(f'[🃑] Wins: - [🃏] Losses: -')
            try:


                self.position_parser(positions=pos, account_info=info)

            except RestartError as fuck:
                self.logger.error(fuck)
                print(repr(f'Restart: {fuck} {_iter}'))
                _iter = 0
            except Exception as fuck:
                self.logger.error(fuck)
                print(repr(f'Restart: {fuck} {_iter}'))
                _iter = 0


    def start_process(self):
        try:
            self.start_process_()
        except KeyboardInterrupt:
            exit()