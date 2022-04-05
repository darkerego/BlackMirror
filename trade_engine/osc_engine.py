import sys
import threading
import time

from lib.exceptions import RestartError
from trade_engine.api_wrapper import FtxApi
from utils import colorprint
cp = colorprint.NewColorPrint()

order_type= 'limit'
paper_trade = False

def cdquit(fn_name):
    # print to stderr, unbuffered in Python 2.
    print('{0} took too long'.format(fn_name), file=sys.stderr)
    sys.stderr.flush()  # Python 3 stderr is likely buffered.
    raise RestartError
    # thread.interrupt_main()  # raises KeyboardInterrupt


def exit_after(s):
    '''
    use as decorator to exit process if
    function takes longer than s seconds
    '''

    def outer(fn):
        def inner(*args, **kwargs):
            timer = threading.Timer(s, cdquit, args=[fn.__name__])
            timer.start()
            try:
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
            return result

        return inner

    return outer

class OscillationArbitrage:
    def __init__(self, rest, ws, subaccount, contract_size, min_spread=0.25, long_symbols=[], short_symbols=[],
                 chase_close=False, chase_reopen=False):
        self.long_symbols = long_symbols
        self.short_symbols = short_symbols
        self.contract_size = contract_size
        self.min_spread = min_spread
        self.initial_balance = 0.0
        self.last_balance = 0.0
        self.current_balance = 0.0
        self.maker_fee = 0.0
        self.taker_fee = 0.0
        self.contracts_traded = 0
        self.iter = 0
        self._iter = 0
        self.rest = rest
        self.ws = ws
        self.subaccount = subaccount
        self.last = 0
        self.chase_close = chase_close
        self.chase_reopen = chase_reopen
        self.api = FtxApi(rest=self.rest, ws=self.ws, sa=self.subaccount)
        self.last_pct = 0

    def get_change(self, current, previous):
        if current == previous:
            return 0
        try:
            return (abs(current - previous) / previous) * 100.0
        except ZeroDivisionError:
            return float('inf')

    def calc_fees(self, positions):
        total = 0
        for pos in positions:
            total += pos['size']
        return total - (total * (self.maker_fee * 2))

    def market_close_reopen_position(self, positions, order_type='market'):

        for pos in positions:
            print(pos)
            future_instrument = pos['future']
            cost = pos['cost']
            size = pos['netSize']

            if size < 0:
                size = size * -1
            if cost < 0:
                cost = cost * -1

            side = pos['side']
            if side == 'buy':  # Long Position
                cp.purple(f'[~] Closing LONG position on instrument {future_instrument} of size {size} ...')
                if order_type == 'limit':
                    c_ret = self.api.sell_limit(market=future_instrument, qty=size, reduce=True)
                else:
                    c_ret = self.api.sell_market(market=future_instrument, qty=size, ioc=False, reduce=True)
                if c_ret['id']:
                    cp.blue(f'[~] Opening LONG position on instrument {future_instrument} of size {size}')
                    self.contracts_traded += cost
                b_ret = self.api.buy_market(market=future_instrument, qty=size, ioc=False, reduce=False)
                if b_ret:
                    cp.green('[~] Success!')
                    self.contracts_traded += cost
            else: # Short Position
                cp.purple(f'[~] Closing SHORT position on instrument {future_instrument} of size {size} ...')
                if order_type == 'limit':
                    c_ret = self.api.buy_limit(market=future_instrument, qty=size, reduce=True)
                else:
                    c_ret = self.api.buy_market(market=future_instrument, qty=size, ioc=False, reduce=True)
                if c_ret['id']:
                    cp.blue(f'[~] Opening SHORT position on instrument {future_instrument} of size {size}')
                    self.contracts_traded += cost
                    b_ret = self.api.sell_market(market=future_instrument, qty=size, ioc=False, reduce=False)
                    if b_ret:
                        cp.green(f'[~] Success!')
                        self.contracts_traded += cost

    def chase_close_open_position(self, positions):
        for pos in positions:
            print(pos)
            future_instrument = pos['future']
            cost = pos['cost']
            size = pos['netSize']


            if size < 0:
                size = size * -1
            if cost < 0:
                cost = cost * -1

            side = pos['side']
            if side == 'buy':  # Long Position
                cp.purple(f'[~] Closing LONG position on instrument {future_instrument} of size {size} ...')
                ask, bid, last = self.api.get_ticker(market=future_instrument)
                ret = self.api.sell_limit(market=future_instrument,qty=size, price=ask, post=True, reduce=True)
                if ret['id']:
                    ret = self.api.chase_limit_order(market=future_instrument, oid=ret['id'], max_chase=3)
                    if ret:
                        cp.blue(f'[~] Opening LONG position on instrument {future_instrument} of size {size}')
                        ask, bid, last = self.api.get_ticker(market=future_instrument)
                        ret = self.api.buy_limit(market=future_instrument, qty=bid, price=None, post=True, reduce=False)
                        if ret['id']:
                            ret = self.api.chase_limit_order(market=future_instrument, oid=ret['id'], max_chase=3)
                            if ret:
                                cp.green(f'[~] Success!')
                                self.contracts_traded += cost

            else:

                cp.purple(f'[~] Closing SHORT position on instrument {future_instrument} of size {size} ...')
                ask, bid, last = self.api.get_ticker(market=future_instrument)
                ret = self.api.buy_limit(market=future_instrument, qty=size, price=bid, post=True, reduce=True)
                if ret['id']:
                    ret = self.api.chase_limit_order(market=future_instrument, oid=ret['id'], max_chase=3)
                    if ret:
                        ask, bid, last = self.api.get_ticker(market=future_instrument)
                        cp.blue(f'[~] Opening SHORT position on instrument {future_instrument} of size {size}')
                        ret = self.api.sell_limit(market=future_instrument, qty=size, price=ask, post=True,
                                                 reduce=False)
                        if ret['id']:
                            ret = self.api.chase_limit_order(market=future_instrument, oid=ret['id'], max_chase=3)
                            if ret:
                                cp.green(f'[~] Success!')
                                self.contracts_traded += cost


    @exit_after(30)
    def wrap_arb_engine(self):
        positions = []

        self.iter += 1
        self._iter += 1
        info = self.api.info()
        cp.random_pulse(f'[~] Current Balance: {self.current_balance}, Last Balance: {self.last_balance}, '
                        f'Initial Balance: {self.initial_balance}, Contracts Traded: ${self.contracts_traded} '
                        f'Iteration: {self.iter}')
        if self.iter == 1:

            self.initial_balance = self.current_balance = self.last_balance = info["totalAccountValue"]
        else:
            self.current_balance = info["totalAccountValue"]
        if self._iter == 1:
            self.last_balance = self.current_balance
        else:
            self._iter = 0
        if self.current_balance > self.initial_balance:
            #percent_change = self.get_change(self.current_balance, self.initial_balance)
            fees = self.calc_fees(positions=positions)
            current_minus_fees = self.current_balance - fees
            current_spread = self.get_change(current_minus_fees, self.initial_balance)
            cp.red(f'[~] Current spread: {current_spread} Spread: Current minus fees: {current_minus_fees}')

            if current_spread <= 0:
                cp.debug(f'[-] Current spread: {current_spread}')
            if current_spread > 0 and current_spread > self.min_spread:
                cp.debug('[!] Min spread hit!')
                for x in self.api.info()['positions']:
                    if x['netSize'] != 0:
                        positions.append(x)


                if current_spread >= self.min_spread:
                    cp.green_black(f'[$] Current spread: {current_spread}')
                    if not paper_trade:
                        if self.chase_reopen:
                            self.chase_close_open_position(positions)
                        else:
                            self.market_close_reopen_position(positions, order_type=order_type)


                    else:
                        cp.debug(f'[~] Not trading... ')
                else:
                    cp.red(f'[!] Current spread: {current_spread}')



    def arbitrage_engine(self):
        cp.red(f'[~] Started arbitrage engine ... Min spread: {self.min_spread}, Chase close: {self.chase_close}, '
               f'Chase reopen: {self.chase_reopen}')
        while True:
            try:
                self.wrap_arb_engine()
            except Exception as err:
                print(err)
            except RestartError:
                cp.red('[!] Timeout, redo ... ')
            else:
                time.sleep(0.125)





    def start_process(self):
        cp.yellow('[~] Starting oscillation arbitrage engine ... ')
        info = self.api.info()
        self.initial_balance = info["totalAccountValue"]
        self.last_balance = self.initial_balance
        self.taker_fee = info['takerFee']
        self.maker_fee = info['makerFee']
        cp.purple(f'[$] Initial Balance: {self.initial_balance}')
        self.arbitrage_engine()