import pandas as pd
import requests
from utils import colorprint
from trade_engine import api_wrapper



class MarketMaker:
    """
    [15, 60, 300, 900, 3600, 14400, 86400]
    """
    def __init__(self, api: api_wrapper.FtxApi, long_sy: str, short_sy: str, min_spread: float, pct_col: float,
                 hedge_ratio: float = 0.5, mode='hedged', ma_window: int =26, period=300):
        """
        @param api: api wrapper
        @param long_sy : long symbol
        @param short_sy: short symbol
        @param min_spread: spread of orders
        @param pct_col: percent collateral
        @param hedge_ratio: long/short ratio
        """
        self.long_sy = long_sy
        self.short_sy = short_sy
        self.min_spread = min_spread
        self.api = api
        self.pct_col = pct_col
        self.hedge_ratio = hedge_ratio
        self.mode = mode
        self.ma_window = ma_window
        self.period = period
        self.cp = colorprint.NewColorPrint()

    def get_stdev(self, symbol, period=None):
        """
        Periods in number of seconds:
        15s, 1m,  5m,  15m,  1h,   4h,   1d
        15, 60, 300, 900, 3600, 14400, 86400
        0.01736111111111111 %, 0.06944444444444445 %  0.3472222222222222 % 1.0416666666666665% 4.166666666666666%
        16.666666666666664 % 77%


        """
        close_array = []
        open_array=[]
        if period is not None:
            if period not in [15, 60, 300, 900, 3600, 14400, 86400]:
                return False
            self.cp.yellow(f'[i] Calculating varience for period {period}')

            # candles = api.ftx_api.fetchOHLCV(symbol=symbol, timeframe=period)
            _candles = requests.get(f'https://ftx.com/api/markets/{symbol}/candles?resolution={period}')
            for c in _candles.json()['result']:
                close_array.append(c['close'])
                open_array.append(c['open'])
            # candle_open = open_array[-1:]
            s = pd.Series(close_array).rolling(self.ma_window).std(ddof=0)[-1:]
            return float(s)

    def get_delta_hedge(self):
        if self.hedge_ratio > 0:
            long = self.hedge_ratio
            short = 1 - self.hedge_ratio
        else:
            long = 1 - (self.hedge_ratio * -1)
            short = (self.hedge_ratio * -1)
        return long, short


    def calc_pos_size(self, symbol):
        long,short = self.get_delta_hedge()
        if symbol == self.long_sy:
            multiplier = long
        else:
            multiplier = short

        ask, bid, last = self.api.rest_ticker(market=symbol)
        info = self.api.info()
        free_col = info["freeCollateral"] * (self.pct_col * multiplier)
        qty = free_col / last
        return qty


    def get_spread(self):
        ask, bid, last = self.api.get_ticker(market=self.market)
        spread = 1 - (bid / ask)
        if spread < 0:
            spread = spread * -1
        return spread



    def start_loop(self):
        while True:
            spread = self.get_spread()
            if spread >= self.min_spread:
                print(f'Spread is: {spread}, which is above the set min spread. Executing ... ')
                qty = self.get_spread()

