from datetime import datetime

import numpy as np
from binance.client import Client

class BinanceApi:
    class Trader:
        def __init__(self, file=None):
            if file:
                lines = [line.rstrip('\n') for line in open(file)]
                key = lines[0]
                secret = lines[1]
                self.client = Client(key, secret)
            else:
                self.client = Client()



        def getBalances(self):
            """ Gets all account balances """
            prices = self.client.get_withdraw_history()
            return prices

        def get_tickers(self):
            return self.client.get_all_tickers()

        def ticker(self, market):
            for ticker in self.get_tickers():
                if ticker.get('symbol') == market:
                    return ticker

        def get_klines(self, trading_pair, interval):
            return self.client.get_klines(symbol=trading_pair, interval=interval)

        def aggravate(self, symbol, interval):
            klines = self.client.get_klines(symbol=symbol, interval=interval)
            open_time = [int(entry[0]) for entry in klines]
            low = [float(entry[1]) for entry in klines]
            mid = [float(entry[2]) for entry in klines]
            high = [float(entry[3]) for entry in klines]
            close = [float(entry[4]) for entry in klines]
            close_array = np.asarray(close)
            high_array = np.asarray(high)
            low_array = np.asarray(low)
            new_time = [datetime.fromtimestamp(time / 1000) for time in open_time]
            return open_time, low, mid, high, close, close_array, high_array, low_array, new_time