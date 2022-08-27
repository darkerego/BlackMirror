import numpy as np

from trade_engine.api_wrapper import debug_api


class FtxStats:
    def __init__(self):
        self.api = debug_api()

    def klines(self, market, res):
        return self.api.get_public_k_line(market, res)

    def fib(self, market, res, trend=0):
        candles = self.api.get_public_k_line(market, res)
        close_array = [x.get('close') for x in candles]
        close_max = np.amax(close_array)
        close_min = np.amin(close_array)
        stdev = close_max - close_min
        if trend == 0:
            # uptrend
            first_level = close_max - stdev * 0.236
            second_level = close_max - stdev * 0.382
            third_level = close_max - stdev * 0.5
            fourth_level = close_max - stdev * 0.618
            fifth_level = close_max - stdev * 0.786
        else:
            first_level = close_min + stdev * 0.236
            second_level = close_min + stdev * 0.382
            third_level = close_min + stdev * 0.5
            fourth_level = close_min + stdev * 0.618
            fifth_level = close_min + stdev * 0.786

        arr = [first_level, second_level, third_level, fourth_level, fifth_level]
        return arr.reverse()


if __name__ == '__main__':
    api = FtxStats()
    print(api.fib(market='ETC-PERP', res=300, trend=1))
    print(api.api.get_ticker('ETH-PERP'))