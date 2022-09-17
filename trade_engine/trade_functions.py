import threading
import time

from fibber import FtxAggratavor
from lib import logmod
from trade_engine.aligning_sar import TheSARsAreAllAligning
from utils.colorprint import NewColorPrint


class TradeFunctions:
    """
    Automatic Trade Engine. Automatically sets stop losses and take profit orders. Trailing stops are used
    unless otherwise specified.
    """

    def __init__(self, api, args):
        # self.trade_logger = TradeLog()
        self.listings_checked = []
        self.long_new_listings = args.long_new_listings
        self.short_new_listings = args.short_new_listings
        self.new_listing_percent = args.new_listing_percent
        self.position_fib_levels = None
        self.cp = NewColorPrint()
        self.up_markets = {}
        self.down_markets = {}
        self.trend = 'N/A'
        self.auto_stop_only = args.auto_stop_only
        self.show_tickers = args.show_tickers
        self.stop_loss = args.stop_loss
        self._take_profit = args._take_profit
        self.tp_fib_enable = args.tp_fib_enable
        self.tp_fib_res = args.tp_fib_res
        self.use_ts = args.use_ts
        self.trailing_stop_pct = args.ts_pct
        self.api = api
        self.confirm = args.confirm
        self.sql = sql_lib.SQLLiteConnection('blackmirror.sqlite')
        self.logger = logmod.CustomLogger(log_file='autotrader.log')
        self.logger.setup_file_handler()
        self.logger = self.logger.get_logger()
        #self.anti_liq_api = AntiLiq(self.api, self.api.getsubaccount())

        self.anti_liq_api = None
        self.fib_api = None
        self.tally = args.tally
        self.sar_sl = args.sar_sl
        self.ta_engine = TheSARsAreAllAligning(debug=True)
        self.accumulated_pnl = 0
        self.position_sars = []
        self.pnl_trackers = []
        self.sar_dict = {}
        self.lock = threading.Lock()
        self.position_close_pct = args.position_close_pct
        self.chase_close = args.chase_close
        self.chase_reopen = args.chase_reopen
        self.min_score = args.min_score
        self.check_before_reopen = args.check_before_reopen
        self.mitigate_fees = args.mitigate_fees
        self.total_contacts_trade = 0.0
        self.reopen = args.reopen
        self.close_method = args.close_method
        self.period = args.period
        self.order_type = args.ot
        self.agg = FtxAggratavor()
        self.future_stats = {}
        self.alert_map = []
        self.alert_up_levels = [0.25, 2.5, 5, 10, 12.5, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
        self.alert_down_levels = [-0.25, -2.5, -5, -10, -12.5, -15, -20, -25, -30, -40, -50 - 60, -70, -80, -90, -100]

        self.max_open_orders = args.max_open_orders
        self.position_step_size = args.position_step_size
        self.disable_stop_loss = args.disable_stop_loss
        self.relist_iterations = args.relist_iterations
        self.iter = 0
        self.hedge_mode = args.hedge_mode
        self.hedge_ratio = args.hedge_ratio
        self.anti_liq = args.anti_liq
        self.max_collateral = args.max_collateral
        self.delta_weight = None
        self.start_time = time.time()
        self.balance_start = 0.0

        self.relist_iter = {}
        self.update_db = args.update_db
        self.open_positions = {}
        self.ta_scores = args.scores
        self.mm_mode = args.mm_mode
        self.mm_long_market = args.mm_long_market
        self.mm_short_market =args. mm_short_market
        self.mm_spread = args.mm_spread
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
        if not self.confirm:
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
        self.logger.info('Trailing stop triggered')
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

            ret = self.api.trailing_stop(market=market, side=opp_side, trail_value=trail_value, size=float(qty),
                                         reduce_only=True)
            #print(ret)
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

            ret = self.api.trailing_stop(market=market, side=opp_side, trail_value=trail_value, size=float(qty),
                                         reduce_only=True)
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
        self.logger.info('Trailing stop triggered')
        if side == 'buy':
            # side = 'sell'
            # long position, so this will be a sell stop
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
        #self.logger.info(f'Stop loss triggered for {market}, size: {size}, side: {side}')
        a, b, l = self.api.get_ticker(market)
        if size < 0.0:
            size = size * -1
        #self.tally.loss()
        if side == 'buy':
            # market sell # market, qty, reduce, ioc, cid
            self.cp.red('[!] Stop hit!')
            ret = self.api.sell_market(market=market, qty=size, reduce=True, ioc=False, cid=None)

            if ret.get('id'):
                tally.loss()
                self.log_order(market=market, price=b, trigger_price=0.0, offset=0.0,
                               _type='limit', qty=size, order_id={ret.get('id')}, status='open',
                               text='%s stop via sell market', side='sell')
            return ret
        else:
            # market buy # marekt, qty, reduce, ioc, cid
            self.cp.red('[!] Stop hit!')

            ret = self.api.buy_market(market=market, qty=size, reduce=True, ioc=False, cid=None)
            if ret.get('id'):
                tally.loss()
                self.log_order(market=market, price=a, trigger_price=0.0, offset=0.0,
                               _type='limit', qty=size, order_id={ret.get('id')}, status='open',
                               text='%s stop via buy market', side='buy')
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
                ret = self.api_trailing_stop(market=market, side=side, qty=size, offset=self.trailing_stop_pct,
                                             entry=entry,
                                             ts_o_type=self.order_type)
                if ret:
                    print('Success at take profit')
                    # self.wins += 1
                    return ret
            else:

                if order_type == 'market':  # market, qty, reduce, ioc, cid):
                    self.cp.yellow(f'[฿] Sending a market order, side: {opp_side}, price: {price}')
                    ret = self.api.sell_market(market=market, qty=size, ioc=False, reduce=True)
                    return ret
                else:  # market, qty, price=None, post=False, reduce=False, cid=None):
                    self.cp.purple(f'[฿] Sending a limit order, side: {opp_side}, price: {price}')
                    ret = self.api.sell_limit(market=market, qty=size, price=ask, reduce=True)
                    # self.wins += 1
                    return ret
        else:  # side == sell
            opp_side = 'buy'
            trail_value = (entry - bid) * self.trailing_stop_pct
            if self.use_ts:
                self.cp.green(f'[฿] Sending a trailing stop: {trail_value}')
                # executor = ThreadPoolExecutor(max_workers=5)
                # ret = executor.submit(self.trailing_stop, market=market, side=opp_side, qty=float(o_size),
                #                      entry=float(entry), offset=float(self.trailing_stop_pct))
                ret = self.api_trailing_stop(market=market, side=side, qty=size, offset=self.trailing_stop_pct,
                                             entry=entry,
                                             ts_o_type=self.order_type)

                if ret:
                    self.cp.purple(f'[~] Success at taking profit.')
                return ret

            else:

                if order_type == 'market':
                    self.cp.purple(f'[฿] Sending a market order, side: {opp_side}, price: {price}')
                    ret = self.api.buy_market(market=market, side=opp_side, size=size,
                                              _type='market', ioc=False, reduce=True)
                    # self.tally.win()
                    return ret
                    # return ret
                else:
                    self.cp.purple(f'[฿] Sending a limit order, side: {opp_side}, price: {price}')
                    ret = self.api.buy_limit(market=market, qty=size, price=ask, reduce=True)
                    # self.wins += 1
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
        # for o in open_orders:
        #    print(f'DEBUG: {o}')
        if not self.relist_iter.get(market):
            self.relist_iter[market] = 0
        if len(open_orders) and self.relist_iter[market] == self.relist_iterations:
            self.api.cancel_orders(market=market, limit_orders=True)
        if len(open_orders) and self.relist_iter[market] < self.relist_iterations:
            self.relist_iter[market] += 1
            leftover_iterations = self.relist_iterations - self.relist_iter[market]
            self.cp.blue(f'[!] We have open orders, relisting in {leftover_iterations} iterations.  ... ')
            relist =False
        else:
            relist = True
            self.api.cancel_orders(market)

        if self.relist_iter[market] == self.relist_iterations:
            self.relist_iter[market] = 0


        if self.close_method == 'increment':
            #if run_now:

            return self.increment_orders(market=market, side=opp_side, qty=size, period=self.period, reduce=True)
        elif self.close_method == 'market' or self.close_method == 'limit':
            return self.take_profit(market=market, side=side, entry=entry, size=size, order_type=order_type)

    def re_open_limit(self, market, side, qty):
        for _ in range(9):
            bid, ask, last = self.api.get_ticker(market=market)
            if side == 'buy':  # market, qty, price=None, post=False, reduce=False, cid=None):
                ret = self.api.buy_limit(market=market, qty=qty, price=bid, post=False, reduce=False)
                if ret['id']:
                    self.log_order(market=market, price=bid, trigger_price=0.0, offset=0.0,
                                   _type='limit', qty=qty, order_id={ret.get('id')}, status='open',
                                   text='%s reopen buy', side='buy')
                    return ret
            elif side == 'sell':
                ret = self.api.sell_limit(market=market, qty=qty, price=ask, post=False, reduce=False)
                if ret['id']:
                    self.log_order(market=market, price=bid, trigger_price=0.0, offset=0.0,
                                   _type='limit', qty=qty, order_id={ret.get('id')}, status='open',
                                   text='%s reopen sell', side='sell')
                    return ret

    def re_open_market(self, market, side, qty):
        a, b, l = self.api.get_ticker(market=market)
        for i in range(9):
            if side == 'buy':  # market, qty, price=None, post=False, reduce=False, cid=None):
                ret = self.api.buy_market(market=market, qty=qty, reduce=False, ioc=False, cid=None)

                if ret['id']:
                    self.log_order(market=market, price=b, trigger_price=0.0, offset=0.0,
                                   _type='limit', qty=qty, order_id={ret.get('id')}, status='open',
                                   text='%s reopen buy', side='buy')
                    return ret
            if side == 'sell':
                ret = self.api.sell_market(market=market, qty=qty, reduce=False, ioc=False, cid=None)
                if ret['id']:
                    self.log_order(market=market, price=a, trigger_price=0.0, offset=0.0,
                                   _type='limit', qty=qty, order_id={ret.get('id')}, status='open',
                                   text='%s reopen sell', side='sell')
                    return ret

    def cancel_limit_side(self, side, market):
        open_order_count = self.api.rest_get_open_orders(market=market)
        if len(open_order_count):
            for o in open_order_count:
                o_side = o.get('side')
                if o_side == side:
                    self.api.cancel_order('id')

    def increment_orders(self, market, side, qty, period, reduce=False, text=None):
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
                open_sell_order_count += 1
                current_sell_orders_qty += o.get('size')
            #current_size
        self.cp.yellow(f'[i] Open Orders: {len(open_order_count)}, Qty Given: {qty}, Current open buy Qty: {current_buy_orders_qty}, current open sell qty: {current_sell_orders_qty}')

        # if len(open_order_count) > self.max_open_orders * 2:
        #    self.api.cancel_orders(market=market)

        buy_orders = []
        sell_orders = []
        max_orders = self.max_open_orders
        stdev, candle_open = self.agg.get_stdev(symbol=market, period=period)
        self.cp.yellow(f'Standard deviation: {stdev}')
        increment_ = stdev / max_orders

        # o_qty = qty / max_orders
        o_qty = qty

        # self.cp.red(f'[!] Killing {open_order_count} currently open orders...')
        # while qty > (qty * 0.95):
        buy_order_que = []
        sell_order_que = []
        if side == 'buy':
            if open_buy_order_count >= (self.max_open_orders):
                print(f'Not doing anything as max orders: {self.max_open_orders} ..')
                return
            else:
                print(f'Max is : {self.max_open_orders}')
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
            #buy_orders.reverse()
            c = 1
            for x, i in enumerate(buy_orders):
                #if c == 1:
                #    next_order_price = bid
                #    buy_order_que.append(['buy', i, next_order_price, market, 'limit'])
                #else:
                next_order_price = ((bid+ask)/2) - (increment_ * x)
                    # next_order_price = bid - (stdev * self.position_step_size) * c
                buy_order_que.append(['buy', i, next_order_price, market, 'limit'])
                c += 1
                self.cp.yellow(
                    f'[o] Placing new {side} order of size {i} on market {market} at price {next_order_price}')
                for x in range(10):  # market, qty, price=None, post=False, reduce=False, cid=None):
                    try:
                        status = self.api.buy_limit(market=market, price=next_order_price, qty=i,
                                                    reduce=reduce, cid=None)

                    except Exception as err:
                        print(f'[!] Error placing limit order: {err}')
                    else:
                        if status:
                            self.cp.red(f"[฿]: {status.get('id')}")
                            self.log_order(market=market, price=next_order_price, trigger_price=0.0, offset=0.0,
                                           _type='limit', qty=i, order_id={status.get('id')}, status='open',
                                           text=f'{text} increment buy', side='buy')
                            break
                        else:
                            time.sleep(0.25)
            # self.cp.debug(f'Debug: : Buy Orders{buy_orders}')
            return True


        else:
            if open_sell_order_count >= (self.max_open_orders):
                print(f'Not doing anything as max open sell orders: max{self.max_open_orders}')
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
            #sell_orders.
            for x, i in enumerate(sell_orders):
                #if i == 1:
                #    next_order_price = ask
                #    sell_order_que.append(['sell', i, next_order_price, market, 'limit'])
                #else:
                #next_order_price = ask + (stdev * self.position_step_size) * c
                next_order_price = ((bid+ask)/2) + (increment_ * x)
                sell_order_que.append(['sell', i, next_order_price, market, 'limit'])
                c += 1
                self.cp.yellow(
                    f'[o] Placing new {side} order of size {i} on market {market} at price {next_order_price}')
                for x in range(10):  # market, qty, price=None, post=False, reduce=False, cid=None):
                    try:
                        status = self.api.sell_limit(market=market, price=next_order_price, qty=i,
                                                     reduce=reduce, cid=None)
                    except Exception as fuck:
                        print(f'[!] Error:', fuck)
                    else:
                        if status:
                            self.cp.purple(f"[฿]: {status['id']}")
                            self.log_order(market=market, price=next_order_price, trigger_price=0.0, offset=0.0,
                                           _type='limit', qty=i, order_id={status.get('id')}, status='open',
                                           text=f'{text} increment sell', side='sell')
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
                    new_qty = (free_coll * (float(self.hedge_ratio) * -1) * self.max_collateral)  # invert if negative
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
            return self.increment_orders(market, side, qty, period, text='reopen')

    def pnl_calc(self, qty, sell, buy, side, cost, future_instrument, fee=0.00019, double_check=False):
        """
        Profit and Loss Calculator - assume paying
         two market fees (one for take profit, one for re-opening). This way we can
         set tp to 0 and run as market maker and make something with limit orders.
        """
        if double_check:
            ask, bid, last = self.api.rest_ticker(market=future_instrument)
            if side == 'buy':
                buy = bid
            else:
                buy = ask

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

    def check_pnl(self, side, future_instrument, size, avg_open_price, cost, takerFee, double_check=False):
        if side == 'buy':

            self.trailing_stop_pct = self.trailing_stop_pct * -1
            ask, bid, last = self.api.get_ticker(market=future_instrument)
            if not ask:
                return
            try:
                pnl, pnl_pct = self.pnl_calc(qty=(size * -1), sell=avg_open_price, buy=bid, side=side,
                                             cost=cost, future_instrument=future_instrument, fee=takerFee,
                                             double_check=double_check)
            except Exception as err:
                self.logger.error('DEBUG Error calculating PNL line 647: ', err)
            else:
                return pnl, pnl_pct


        else:
            # short position
            side = 'sell'
            ask, bid, last = self.api.get_ticker(market=future_instrument)
            if not bid:
                return
            pnl, pnl_pct = self.pnl_calc(qty=(size * -1), sell=avg_open_price, buy=ask, side=side,
                                         cost=cost, future_instrument=future_instrument, fee=takerFee,
                                         double_check=double_check)
            try:
                if pnl <= 0.0:
                    self.cp.red(f'[🔻] Negative PNL {pnl} on position {future_instrument}')
                else:
                    self.cp.green(f'[🔺] Positive PNL {pnl} on position {future_instrument}')
            except Exception as err:
                self.logger.error('DEBUG Error calculating PNL line 677: ', err)
                pass
            else:
                return pnl, pnl_pct