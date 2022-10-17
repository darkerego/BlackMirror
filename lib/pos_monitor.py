import asyncio
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from lib.auto_trader import AutoTrader
from lib.receivers import MqReceiver
from utils.colorprint import NewColorPrint


class Monitor:
    """
    This is the spine of the program. User supplied options are parsed here
    for consumption by the required libraries.
    """

    def __init__(self, api, args):
        """
        :param rest: restful api object
        :param ws: websocket api object
        :param conf: dictionary containing
            everything from argparse
        """
        # self.key = key
        # self.secret = secret
        # self.ws = ws_client.FtxWebsocketClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        # self.rest = client.FtxClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        # self.subaccount = subaccount

        self.executor = ThreadPoolExecutor()
        self.cp = NewColorPrint()
        self.running = False
        self.lag = 0
        self.a_restarts = 0
        self.lagging = False
        self.files = []
        self.args = args
        self.lock = threading.Lock()
        self.api = api

        if self.args.stop_loss_pct > 0.0:
            self.args.stop_loss_pct = self.args.stop_loss_pct * -1

        """if self.args.balance_arbitrage:
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
            t.start()"""

        if self.args.enable_mqtt:
            if self.lock.locked():
                print('ERROR RECEIVER IS LOCKED!')
            else:
                self.lock.acquire()

                self.cp.purple(f'[mq] Starting mqtt receiver ... ')
                mq_server = MqReceiver(server_uri=self.args.ws_uri, api=api,
                                       collateral_pct=self.args.portfolio_pct, reenter=self.args.reenter,
                                       data_source=self.args.data_source,
                                       exclude_markets=self.args.exclude_markets, debug=False,
                                       min_score=self.args.min_score, min_adx=self.args.min_adx,
                                       topic=self.args.mqtt_topic, live_score=self.args.live_score,
                                       confirm=self.args.confirm)

                self.executor.submit(self.wrapper, mq_server.start_process())

        if self.args.monitor or self.args.update_db:
            self.cp.navy(data='[+] Starting auto trader')
            self.auto_trade = AutoTrader(self.api, self.args)

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

    # async def receiver(self):
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
        # self.executor.submit(self.auto_trade.start_process)
        self.auto_trade.start_process()
        self.a_restarts += 1
        self.cp.navy(f'[☑] Started ... {self.a_restarts}')
