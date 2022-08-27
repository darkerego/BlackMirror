from trade_engine import api_wrapper

class MarketMaker:
    def __init__(self, api: api_wrapper.FtxApi, market: str, min_spread: float, pct_col: float):
        self.market = market
        self.min_spread = min_spread
        self.api = api
        self.pct_col = pct_col

    def calc_pos_size(self):
        ask, bid, last = self.api.rest_ticker(market=self.market)
        info = self.api.info()
        free_col = info["freeCollateral"]
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

