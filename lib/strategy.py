import json
import time
from utils import config_loader
from utils.colorprint import NewColorPrint
from websocket import create_connection, WebSocketConnectionClosedException
from trade_engine.api_wrapper import FtxApi

class TradeStrategy:
    def __init__(self, strategy, symbol, contract_size, rest, ws, sa=None, symbol_monitor=None):
        self.symbol = symbol
        self.cp = NewColorPrint()
        self.strategy = strategy
        self.size = contract_size
        self.rest = rest
        self.symbol_monitor = symbol_monitor
        self.ws = ws
        self.api = FtxApi(rest=rest, ws=ws, sa=sa)
        self.cp.yellow(f'[~] Init Trade Strategy {strategy} on symbol {symbol}')

    def check_position_exists_diff(self, future, s):
        for pos in self.api.positions():
            if float(pos['collateralUsed']) == 0.0 and pos['future'] == future:
                print(pos)
                return True
        return False

    def start_process(self):
        self.cp.yellow('Starting up the ta engine ...')
        if self.strategy == 'sar':
            from trade_engine.aligning_sar import TheSARsAreAllAligning
            sar = TheSARsAreAllAligning(debug=False)
            while True:
                sig = sar.sar_scalper(instrument=self.symbol_monitor)
                if sig:
                    self.cp.red(f'[signal]: {sig}')
                    if sig == 'long':
                        self.cp.green('[LONG]: SAR LONG, ENTERING!')
                        if self.check_position_exists_diff(future=self.symbol, s=self.size):
                            self.api.buy_market(market=self.symbol, qty=self.size, reduce=False, ioc=False, cid=None)
                        else:
                            self.cp.alert('Cannot enter, position already open!')
                    elif sig == 'short':
                        self.cp.red('[SHORT]: SAR SHORT, ENTERING!')
                        if self.check_position_exists_diff(future=self.symbol, s=self.size):
                            self.api.sell_market(market=self.symbol, qty=self.size, reduce=False, ioc=False, cid=None)
                        else:
                            self.cp.purple('Cannot enter, position already open!')
                else:
                    self.cp.purple('[x] No signal')

    def __start_process__(self):
        restarts = 0
        while True:
            try:
                self.start_process()
            except Exception as fuckyou:
                restarts += 1
                print(f'[e] Error: {fuckyou}, restarting strategy. Restart: {restarts}')
                time.sleep(1)
