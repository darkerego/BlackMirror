#!/usr/bin/env python3
import argparse
import numpy as np
import pandas as pd
import requests
from statsmodels.stats.weightstats import DescrStatsW
from utils.colorprint import  NewColorPrint
import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt
#plt.style.use('fivethirtyeight')
cp = NewColorPrint()

class FtxAggratavor:
    """
    Grab kline data from ftx and calculate a standard deviation
    """

    def __init__(self, api=None):
        self.api = api
        self.rolling_stdev = 0.0
        self.stdev_1d = 0.0
        self.stdev_4h = 0.0
        self.stdev_1h = 0.0

        self.stdev_15_m = 0.0
        self.stdev_5m = 0.0
        self.stdev_1m = 0.0
        self.stdev_15s = 0.0

    def weighted_std(self, values, weights):
        # For simplicity, assume len(values) == len(weights)
        # assume all weights > 0
        sum_of_weights = np.sum(weights)
        weighted_average = np.sum(values * weights) / sum_of_weights
        n = len(weights)
        numerator = np.sum(n * weights * (values - weighted_average) ** 2.0)
        denominator = (n - 1) * sum_of_weights
        weighted_std = np.sqrt(numerator / denominator)
        return weighted_std

    def calcweightedavg(self, data, weights):

        # X is the dataset, as a Pandas' DataFrame
        mean = np.ma.average(data, axis=0,
                             weights=weights)  # Computing the weighted sample mean (fast, efficient and precise)

        # Convert to a Pandas' Series (it's just aesthetic and more
        # ergonomic; no difference in computed values)
        mean = pd.Series(mean, index=list(data.keys()))
        xm = data - mean  # xm = X diff to mean
        xm = xm.fillna(
            0)  # fill NaN with 0 (because anyway a variance of 0 is just void, but at least it keeps the other covariance's values computed correctly))
        sigma2 = 1. / (weights.sum() - 1) * xm.mul(weights, axis=0).T.dot(
            xm)  # Compute the unbiased weighted sample covariance

    # Add your function below!
    def average(self, numbers):
        total = sum(numbers)
        total = float(total)
        total /= len(numbers)
        return total

    def variance(self, data, ddof=0):
        n = len(data)
        mean = sum(data) / n
        return sum((x - mean) ** 2 for x in data) / (n - ddof)

    def stdev(self, data):
        import math
        _max = max(data)
        _min = min(data)
        var = self.variance(data)
        std_dev = math.sqrt(var)
        return std_dev, _max, _min

    def gen_fib(self, stdev, _mx, _mi, p):
        levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
        retrace_long = []
        retrace_short = []
        #df = pd.read_csv()
        print(f'Up: {p}')
        for _ in levels:
            #
            diff_ = _mx - _mi
            val = _mx - (diff_ * _)
            #print(f'Level: {_} , Value: {val} ')
            retrace_long.append((_, val))
        print(f'Down: {p}')
        for _ in levels:
            #
            diff_ = _mx - _mi
            val = _mi + (diff_ * _)
            #print(f'Level: {_} , Value: {val} ')
            retrace_short.append((_, val))
        return retrace_long, retrace_short

    def next_fib_level(self, symbol, retrace_levels):
        ask, bid, last = self.api.get_ticker(symbol)
        retrace_levels.append((0, last))
        level_map = sorted(retrace_levels, key=lambda tup: tup[1])
        for x, y in enumerate(level_map):
            if y[0] == 0:
                try:
                    above = level_map[x+1]
                except IndexError:
                    above = 0
                try:
                    below = level_map[x-1]
                except IndexError:
                    below = 0
            return above, below








    def get_stdev(self, symbol, period=None, side='LONG'):
        """
        Periods in number of seconds:
        15s, 1m,  5m,  15m,  1h,   4h,   1d
        15, 60, 300, 900, 3600, 14400, 86400
        0.01736111111111111 %, 0.06944444444444445 %  0.3472222222222222 % 1.0416666666666665% 4.166666666666666%
        16.666666666666664 % 77%


        """
        candle_dict = []
        std_dict = []
        std_periods = []
        close_array = []
        if period is not None:
            if period not in [15, 60, 300, 900, 3600, 14400, 86400]:
                return False
            cp.yellow(f'[i] Calculating varience for period {period}')

            # candles = api.ftx_api.fetchOHLCV(symbol=symbol, timeframe=period)
            _candles = requests.get(f'https://ftx.com/api/markets/{symbol}/candles?resolution={period}')
            for c in _candles.json()['result']:
                close_array.append(c['close'])
            s, _mx, _mi = self.stdev(close_array)
            self.gen_fib(s, _mx, _mi, period)
            return s,
        else:
            period_list = [15, 60, 300, 900, 3600, 14400, 86400]
            for p in period_list:
                close_array = []
                _candles = requests.get(f'https://ftx.com/api/markets/{symbol}/candles?resolution={p}')
                if _candles.status_code != 200:
                    cp.red(f'[!] HTTP Status Code: {_candles.status_code}')
                for c in _candles.json()['result']:
                    close_array.append(c['close'])
                candle_dict.append((p, _candles.json()))
                # close_array = [float(entry[5]) for entry in _candles.json()['result']]
                close_array = np.asarray(close_array)
                std_dev, _mx, _mi = self.stdev(close_array)
                up, down = self.gen_fib(std_dev, _mx, _mi, p)
                if side == 'LONG':
                    return self.next_fib_level(symbol, up)
                else:
                    return self.next_fib_level(symbol, down)


                std_dict.append(std_dev)
                std_periods.append((std_dev, p))
                if p == 15:
                    self.stdev_15s = std_dev
                elif p == 60:
                    self.stdev_1m = std_dev
                elif p == 300:
                    self.stdev_5m = std_dev
                elif p == 900:
                    self.stdev_15_m = std_dev
                elif p == 3600:
                    self.stdev_1h = std_dev
                elif p == 14400:
                    self.stdev_4h = std_dev
                elif p == 86400:
                    self.stdev_1d = std_dev
                for _ in _candles:
                    timestamp = _[0]
                    high = _[1]
                    low = _[2]
                    try:
                        close = _[3]
                    except IndexError:
                        close = 0
                    volume = _[4]
                    candle_dict.append(
                        f'{{"peroid":{p} "timestamp": {timestamp},"high": {high}, "low":{low}, "close":{close},'
                        f' "volume":{volume}}}')
            std_dict = np.asarray(std_dict)
            cp.blue(f'Stdev by periods (timeframes in # of seconds): {std_periods}')
            weights = [0.017361111111111112, 0.06944444444444445, 0.3472222222222222, 1.0416666666666665,
                       4.166666666666666,
                       16.666666666666664, 77]
            weighted_stats = DescrStatsW(std_dict, weights=np.asarray(weights), ddof=0)
            cp.purple(f'Weighted Statistical Standard Deviation: {weighted_stats.std}')
            cp.yellow(f'Weighted Statistical Variance: {weighted_stats.var}')
            cp.red(f'Weighted Statistical Standard Error: {weighted_stats.std_mean}')
            cp.green(f'Weighted Statistical Mean: {weighted_stats.mean}')
            return weighted_stats.mean


#levels=[0,0.236, 0.382, 0.5 , 0.618, 0.786,1]
args = argparse.ArgumentParser()
args.add_argument('-s', '--symbol', type=str, help='symbol')
args.add_argument('-p', '--period', type=int, help='period', default=None, choices=[15, 60, 300, 900, 1800, 3600, 14400, 86400])

args=args.parse_args()
api = FtxAggratavor()
ret=api.get_stdev(args.symbol, args.period)
print(ret)