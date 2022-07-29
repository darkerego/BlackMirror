#!/usr/bin/env python3
from exchanges.ftx_lib.rest import client
from trade_engine import api_wrapper
from exchanges.ftx_lib.websocket_api import client as ws
from logging import getLogger
from utils import colorprint
import argparse

class ArbitrageAnalyzer:
    def __init__(self, markets: list = None, index: str = None, out_file: str = None):
        self.markets = markets
        self.index = index
        self.out_file = out_file
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
        return float(((index_price - market_price) * 100) / index_price)

    def start(self):
        last_prices = {}
        self.logger.info('Starting analysis engine ... ')
        i_ask, i_bid, i_last = self.ws.get_ticker(self.index)
        for _ in self.markets:
            self.cp.yellow(f'[+] Retrieving {_}')
            ask, bid, last = self.ws.get_ticker(_)
            last_prices[_] = last
            spread = self.spread_calc(last, i_last)
            _log = f'[~] Spread: {_}:{self.index} {spread}%'
            self.cp.white(_log)
            self.logger.info(_log)



if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('-i', '--index', dest='index', type=str, help='Index Ticker')
    args.add_argument('-m', '--markets', dest='markets', type=str, nargs='+', help='Markets to compare with index')
    args.add_argument('-f', '--file', dest='log_file', type=str, default='arb.log')
    args = args.parse_args()
    api = ArbitrageAnalyzer(args.markets, args.index, args.log_file)
    api.start()