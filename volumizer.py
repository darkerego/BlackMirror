from trade_engine import api_wrapper
import talib
import pandas as pd


class Volumizer:
    def __init__(self, res=60):
        self.api = api_wrapper.debug_api()
        self.res = res

    def volume_x(self, vol_arr):
        vol_ma = pd.Series(vol_arr).rolling(200).mean().mean().real


    def markets(self):
        perp = []
        for market  in self.api.markets():
            if market.get('name').split('-')[1] == 'PERP':
                perp.append(market.get('name'))
        return perp

    def start_loop(self):
        markets = self.markets()
        close_array = []
        for market in markets:
            candles = self.api.get_public_k_line(market=market, res=self.res)
            for candle in candles:
                close_array.append(candle.get('close'))




