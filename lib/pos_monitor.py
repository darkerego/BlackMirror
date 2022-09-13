import asyncio
import datetime
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import lib.logmod
from lib.auto_trader import AutoTrader
from lib.receivers import WsReceiver, MqReceiver
from lib.strategy import TradeStrategy
from trade_engine.api_wrapper import FtxApi
from trade_engine.osc_engine import OscillationArbitrage
from utils.colorprint import NewColorPrint
import sys
from exchanges.ftx_lib.rest import client
from exchanges.ftx_lib.websocket_api import client as ws_client
from utils.ftx_exceptions import FtxDisconnectError


class Monitor:
    """
    This is the spine of the program. User supplied options are parsed here
    for consumption by the required libraries.
    """
    def __init__(self, api, conf):
        """
        :param rest: restful api object
        :param ws: websocket api object
        :param conf: dictionary containing
            everything from argparse
        """
        #self.key = key
        #self.secret = secret
        #self.ws = ws_client.FtxWebsocketClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        #self.rest = client.FtxClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        #self.subaccount = subaccount

        self.cp = NewColorPrint()

        self.running = False
        self.lag = 0
        self.a_restarts = 0
        self.lagging = False
        self.files = []
        self.new_listing_percent =  conf.new_listing_percent,
        self.long_new_listings = conf.long_new_listings,
        self.short_new_listings = conf.short_new_listings,
        self.executor = ThreadPoolExecutor(max_workers=25)
        self.lock = threading.Lock()
        self.lock2 = threading.Lock()
        self.logger = lib.logmod.CustomLogger(log_file='debug2.log')
        self.logger.setup_file_handler()
        self.api = api
        self.auto_stop_only=conf.auto_stop_only
        self.update_db = conf.update_db
        self.logger = logging.getLogger()
        self.mitigate_fees = conf.mitigate_fees
        self.auto = conf.auto_trader
        self.sl = conf.stop_loss_pct
        self.tp = conf.take_profit_pct
        self.ts = conf.use_trailing_stop
        self.ot = conf.order_type
        self.show_tickers = conf.show_tickers
        #self.monitor_only = conf.monitor
        self.use_strategy = conf.use_strategy
        self.strategy = conf.strategy
        self.symbol = conf.symbol
        self.symbol_monitor = conf.symbol_monitor
        self.enable_ws = conf.enable_ws
        self.enable_mqtt = conf.enable_mqtt
        self.mqtt_uri = conf.ws_uri
        self.min_score = conf.min_score
        self.ws_uri = conf.ws_uri
        self.portfolio_pct = conf.portfolio_pct
        self.reenter = conf.reenter
        self.data_source = conf.data_source
        self.exclude_markets = conf.exclude_markets
        self.offset = conf.ts_offset
        self.position_close_pct = conf.position_close_pct
        self.balance_arbitrage = conf.balance_arbitrage
        self.long_symbols = conf.long_symbols
        self.short_symbols = conf.short_symbols
        self.contract_size = conf.contract_size
        self.max_collateral = conf.max_collateral
        self.min_spread = conf.min_spread
        self.max_open_orders = conf.num_open_orders
        self.position_step_size = conf.position_step_size
        self.reopen = conf.reopen_method
        self.close_method = conf.close_method
        self.mm_mode = conf.mm_mode
        self.mm_long_market = conf.mm_long_market
        self.mm_short_market = conf.mm_short_market
        self.mm_spread = conf.mm_spread
        self.no_sl = conf.disable_stop_loss
        self.chase_close = conf.chase_close
        self.chase_reopen = conf.chase_reopen
        self.relist_iterations = conf.relist_iterations
        self.increment_period = conf.increment_period
        self.hedge_ratio = conf.hedge_ratio
        self.hedge_mode = conf.hedge_mode
        self.mqtt_topic = conf.mqtt_topic
        self.live_score = conf.live_score
        self.confirm = conf.confirm
        self.anti_liq = conf.anti_liq
        self.tp_fib_enable = conf.tp_fib_enable
        self.tp_fib_res = conf.tp_fib_res
        self.min_adx = conf.min_adx
        self.sar_sl = conf.sar_sl
        self.check_before_reopen = conf.check_before_reopen
        self.arrayOfFutures = []

        """if conf.verbose:
            file_handler = logging.FileHandler(filename='tmp.log')
            stdout_handler = logging.StreamHandler(sys.stdout)
            handlers = [file_handler, stdout_handler]

            logging.basicConfig(
                level=logging.DEBUG,
                format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
                handlers=handlers
            )
            self.logger = logging.getLogger('LOGGER_NAME')
            self.logger.addHandler(stdout_handler)"""



        if self.sl > 0.0:
            self.sl = self.sl * -1

        if self.balance_arbitrage:
            self.cp.yellow('Starting balance arbitrage engine ...')
            self.osc_arb = OscillationArbitrage(rest=self.rest, ws=self.ws, subaccount=self.subaccount,
                                                min_spread=self.min_spread, contract_size=self.contract_size,
                                                chase_close=self.chase_close, chase_reopen=self.chase_reopen)
            self.osc_arb.start_process()

        if self.use_strategy:
            self.cp.yellow('Starting Trade Strategy Engine ...')
            TaTrader = TradeStrategy(strategy=self.strategy, symbol=self.symbol, contract_size=self.contract_size,
                                     rest=self.rest, ws=self.ws, sa=self.subaccount, symbol_monitor=self.symbol_monitor)
            self.executor.submit(TaTrader.__start_process__)

        if self.enable_ws:
            self.cp.purple('[ws] Starting the websocket receiver.')
            ws_server = WsReceiver(server_uri=self.ws_uri, rest=self.rest, _ws=self.ws, sa=self.subaccount,
                                   contract_size=self.contract_size, reenter=self.reenter,
                                   data_source=self.data_source, exclude_markets=self.exclude_markets)

            t = threading.Thread(target=ws_server.connect)
            t.start()

        if self.enable_mqtt:
            if self.lock.locked():
                print('ERROR RECEIVER IS LOCKED!')
            else:
                self.lock.acquire()

                self.cp.purple(f'[mq] Starting mqtt receiver ... ')
                mq_server = MqReceiver(server_uri=self.mqtt_uri, api=api,
                                       collateral_pct=self.portfolio_pct, reenter=self.reenter, data_source=self.data_source,
                                       exclude_markets=self.exclude_markets, debug=False, min_score=self.min_score, min_adx = self.min_adx,
                                       topic=self.mqtt_topic, live_score=self.live_score, confirm=self.confirm)

                self.executor.submit(self.wrapper, mq_server.start_process())




        if self.auto or self.update_db:
            self.cp.navy(data='[+] Starting auto trader')
            self.auto_trade = AutoTrader(self.api,
                                         stop_loss=self.sl,
                                         _take_profit=self.tp,
                                         use_ts=self.ts,
                                         ts_pct=self.offset,
                                         max_open_orders=self.max_open_orders,
                                         position_step_size=self.position_step_size,
                                         reopen=self.reopen,
                                         disable_stop_loss=self.no_sl,
                                         show_tickers=self.show_tickers,
                                         close_method=self.close_method,
                                         ot=self.ot,
                                         relist_iterations=self.relist_iterations,
                                         period=self.increment_period,
                                         hedge_mode=self.hedge_mode,
                                         hedge_ratio=self.hedge_ratio,
                                         max_collateral=self.max_collateral,
                                         position_close_pct=self.position_close_pct,
                                         chase_close=self.chase_close,
                                         chase_reopen=self.chase_reopen,
                                         update_db=self.update_db,
                                         anti_liq = self.anti_liq,
                                         min_score = self.min_score,
                                         check_before_reopen = self.check_before_reopen,
                                         mitigate_fees = self.mitigate_fees,
                                         confirm = self.confirm,
                                         sar_sl = self.sar_sl,
                                         mm_mode = self.mm_mode,
                                         mm_long_market = self.mm_long_market,
                                         mm_short_market = self.mm_short_market,
                                         mm_spread = self.mm_spread,
                                         long_new_listings = self.long_new_listings,
                                        short_new_listings= self.short_new_listings,
                                        new_listing_percent=self.new_listing_percent)

    def __enter__(self):
        print('Entering monitor')
        return self

    def __exit__(self, *a):
        print("Exiting monitor")
        self.running = False
        MqReceiver.running = False
        for file in self.files:
            os.unlink(file)
        sys.exit()



    def start_auto_trade(self):
        self.cp.navy('[☠] Starting auto trader...')
        self.executor.submit(self.auto_trade.start_process)
        self.a_restarts += 1
        self.cp.navy(f'[☑] Started ... {self.a_restarts}')


    def wrapper(self, coro):
        return asyncio.run(coro)

    #async def receiver(self):
    #    if self.enable_mqtt:
    #        await asyncio.gather(*self.arrayOfFutures)
    def rest_ticker(self):
        ret = self.rest.list_markets()
        for _ in ret:
            if _.get('name') == 'BTC-PERP':
                return _.get('last')

    def percentage_change(self, current, previous):
        if previous != 0:
            return float(current - previous) / abs(previous) * 100
        else:
            return 0

    def monitor(self):
        self.cp.navy('[☠] Starting auto trader...')
        #self.executor.submit(self.auto_trade.start_process)
        self.auto_trade.start_process()
        self.a_restarts += 1
        self.cp.navy(f'[☑] Started ... {self.a_restarts}')


