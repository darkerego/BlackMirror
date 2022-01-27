import time

from trade_engine.api_wrapper import FtxApi
from utils import colorprint
cp = colorprint.NewColorPrint()

class OscillationArbitrage:
    def __init__(self, rest, ws, subaccount, contract_size, min_spread=0.25):
        # self.long_symbols = long_symbols
        # self.short_symbols = short_symbols
        self.contract_size = contract_size
        self.min_spread = min_spread
        self.initial_balance = 0.0
        self.last_balance = 0.0
        self.current_balance = 0.0
        self.maker_fee = 0.0
        self.taker_fee = 0.0
        self.rest = rest
        self.ws = ws
        self.subaccount = subaccount
        self.api = FtxApi(rest=self.rest, ws=self.ws, sa=self.subaccount)

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
        return total - (total * self.maker_fee)

    def arbitrage_engine(self):
        cp.red(f'Started arbitrage engine ... Min spread: {self.min_spread}')
        positions = []
        while True:
            info = self.api.info()
            cp.debug(f'Current Balance: {self.current_balance}')
            self.current_balance = info["totalAccountValue"]
            if self.current_balance > self.last_balance:
                percent_change = self.get_change(self.current_balance, self.last_balance)
                if 0 < percent_change < self.min_spread:
                    cp.debug(f'[+] Current spread: {percent_change}')
                if percent_change <= 0:
                    cp.debug(f'[-] Current spread: {percent_change}')
                if percent_change > 0 and percent_change > self.min_spread:
                    cp.debug('[!] Min spread hit!')
                    for x in self.api.info()['positions']:
                        if x['netSize'] != 0:
                            positions.append(x)
                    fees = self.calc_fees(positions=positions)
                    current_minus_fees = self.current_balance - fees
                    cp.debug(f'Current minus fees: {current_minus_fees}')
                    current_spread = self.get_change(current_minus_fees, self.last_balance)
                    if current_spread > self.min_spread:
                        cp.green_black(f'[$] Current spread: {current_spread}')
                    else:
                        cp.red(f'[!] Current spread: {current_spread}')
                    positions = []
            time.sleep(0.25)




    def start_process(self):
        cp.yellow('[~] Starting oscillation arbitrage engine ... ')
        info = self.api.info()
        self.initial_balance = info["totalAccountValue"]
        self.last_balance = self.initial_balance
        self.taker_fee = info['takerFee']
        self.maker_fee = info['makerFee']
        cp.purple(f'[$] Initial Balance: {self.initial_balance}')
        self.arbitrage_engine()