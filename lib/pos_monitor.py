import datetime
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from lib.auto_trader import AutoTrader
from lib.receivers import WsReceiver
from lib.strategy import TradeStrategy
from trade_engine.api_wrapper import FtxApi
from trade_engine.osc_engine import OscillationArbitrage
from utils.colorprint import NewColorPrint

class Monitor:
    def __init__(self, rest, ws, subaccount, sl, tp, ts, offset, reopen, auto, position_step_size=0.02,
                 max_open_orders=None, no_sl=False, show_tickers=False, monitor_only=False, close_method='market',
                 balance_arbitrage=False, long_symbols=None, short_symbols=None, contract_size=0.0, min_spread=0.25,
                 ot='market', use_strategy=False, strategy=None, symbol=None, symbol_monitor=None, enable_ws=False,
                 ws_uri='localhost:9000', reenter=False, data_source='binance', exclude_markets=None):
        self.rest = rest
        self.cp = NewColorPrint()
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
        self.running = False
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
        # print(type(self.sl), self.sl)
        if self.sl > 0.0:
            self.sl = self.sl * -1

        if self.balance_arbitrage:
            self.cp.yellow('Starting balance arbitrage engine ...')
            self.osc_arb = OscillationArbitrage(rest=self.rest, ws=self.ws, subaccount=self.subaccount,
                                                min_spread=self.min_spread, contract_size=self.contract_size)
            self.osc_arb.start_process()

        if self.use_strategy:
            self.cp.yellow('Starting Trade Strategy Engine ...')
            TaTrader = TradeStrategy(strategy=self.strategy, symbol=self.symbol, contract_size=self.contract_size,
                                     rest=self.rest, ws=self.ws, sa=self.subaccount, symbol_monitor=self.symbol_monitor)
            self.executor.submit(TaTrader.__start_process__)

        if self.enable_ws:
            self.cp.purple('[ws] Starting the websocket receiver.')
            ws_server = WsReceiver(server_uri=self.ws_uri, rest=self.rest, _ws=self.ws, sa=self.subaccount,
                                   contract_size=contract_size, reenter=reenter,
                                   data_source=data_source, exclude_markets=exclude_markets)

            t = threading.Thread(target=ws_server.connect)
            t.start()

        if self.auto:
            self.cp.navy(data='Starting auto trader')
            self.auto_trade = AutoTrader(self.api, stop_loss=self.sl, _take_profit=self.tp, use_ts=self.ts,
                                         ts_pct=self.offset, max_open_orders=self.max_open_orders,
                                         position_step_size=self.position_step_size, reopen=self.reopen,
                                         disable_stop_loss=self.no_sl, show_tickers=self.show_tickers,
                                         monitor_only=self.monitor_only, close_method=close_method, ot=self.ot)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.running = False
        for file in self.files:
            os.unlink(file)

    def start_auto_trade(self):
        self.cp.navy('[☠] Starting auto trader...')
        self.executor.submit(self.auto.start_process)
        self.cp.navy('[☑] Started ...')

    def monitor(self):
        c = 0
        tt = 0
        current_time = 0
        running = self.running = True
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