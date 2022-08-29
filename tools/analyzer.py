#!/usr/bin/env python3

from exchanges.ftx_lib.rest import client
from trade_engine import api_wrapper
from exchanges.ftx_lib.websocket_api import client as ws
from logging import getLogger
from utils import colorprint
import argparse
import time
from decimal import Decimal

class ArbitrageAnalyzer:
    def __init__(self, markets: list = None, index: str = None, out_file: str = None, delay: float = 0.25,
                 precision: int = 4):
        self.markets = markets
        self.index = index
        self.delay = delay
        self.out_file = out_file
        self.precision = precision
        self.history = {}
        self.averages = {}
        self.rest = client.FtxClient()
        self.ws = ws.FtxWebsocketClient()
        self.api = api_wrapper.FtxApi(self.rest, self.ws)
        self.logger = getLogger()
        self.cp = colorprint.NewColorPrint()

    def spread_calc(self, market_price: str, index_price:str):
        """
        arr: array of markets and prices
        index: last price of index market
        """
        try:
            ret = float(((index_price - market_price) * 100) / index_price)
        except ZeroDivisionError:
            return None
        else:
            return ret

    def historical_avg(self):
        #print(self.history)
        for key, value in self.history.items():
            try:
                self.averages[key] = round(sum(value) / len(value), self.precision)
            except ZeroDivisionError:
                pass

    def manage_averages(self, pair, value):
        self.history[pair].append(value)
        self.historical_avg()

    def start(self):
        last_prices = {}
        self.logger.info('Starting analysis engine ... please wait ...  ')
        iter = 0
        for _ in self.markets:
            pair = f'{_}_{self.index}'
            self.history[pair] = []
            self.averages[pair] = []
        while True:
            i_ask, i_bid, i_last = self.api.get_ticker(self.index)
            if not i_last:
                self.cp.red('[~] Booting ... ')
                time.sleep(5)
            else:

                for _ in self.markets:
                    self.cp.yellow(f'[+] Retrieving {_}')
                    ask, bid, last = self.api.get_ticker(_)
                    last_prices[_] = last
                    pair = f'{_}_{self.index}'
                    spread = self.spread_calc(last, i_last)
                    self.manage_averages(pair, spread)
                    self.historical_avg()

                    spread = round(spread, self.precision)
                    _log = f'[~] Spread: {pair} {spread}%'

                    self.cp.white(_log)
                    self.logger.info(_log)
            time.sleep(self.delay)
            if iter % 100 == 0:
                self.cp.purple(f'[~] Averages: {self.averages}')




def main():
    args = argparse.ArgumentParser()
    args.add_argument('-i', '--index', dest='index', type=str, help='Index Ticker')
    args.add_argument('-m', '--markets', dest='markets', type=str, nargs='+', help='Markets to compare with index')
    args.add_argument('-f', '--file', dest='log_file', type=str, default='arb.log')
    args.add_argument('-d', '--delay', dest='delay', type=float, default=0.25, help='Time delay between calculations')
    args.add_argument('-p', '--precision', dest='precision', type=int, default=4, help='Decimal precision.')
    args = args.parse_args()
    api = ArbitrageAnalyzer(args.markets, args.index, args.log_file, args.delay, args.precision)
    api.start()


if __name__ == '__main__':

    main()