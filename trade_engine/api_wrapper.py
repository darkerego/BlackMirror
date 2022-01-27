import pandas as pd
import time
from utils.colorprint import NewColorPrint as cp

cp = cp()

class FtxApi:
    """
    Api Function Wrapper
    """

    def __init__(self, rest, ws, sa=None):
        self.rest = rest
        self.ws = ws
        self.sa = sa

    def chase_limit_order(self, market, oid, max_chase=3):
        print(f'Chasing order {market}, {oid}')
        time.sleep(1)
        last_price = 0
        count = 0
        while True:
            orders = self.get_open_orders(market=market)
            print(orders)
            ask, bid, last = self.get_ticker(market=market)
            if len(orders):
                for o in orders:
                    if o['id'] == oid:
                        if o['status'] == 'filled' or o['status'] == 'closed':
                            cp.red(f'[*] Order {oid}: Status: {o["status"]}')
                            return
                        else:
                            if o['side'] == 'buy':
                                current_price = bid
                                if current_price > last_price:
                                    last_price = current_price
                                    ret = self.modify_order(oid=oid, price=current_price, size=o['remainingSize'])
                                    if ret:
                                        print('Success: ', ret.__str__)
                                        count += 1
                                    else:
                                        print('Fail: ', ret.__str__)
                                    time.sleep(0.125)
                            else:
                                current_price = ask
                                if current_price < last_price:
                                    last_price = current_price
                                    ret = self.modify_order(oid=oid, price=current_price, size=o['remainingSize'])
                                    if ret:
                                        print('Success: ', ret.__str__)
                                        count += 1
                                    else:
                                        print('Fail: ', ret.__str__)
                                    time.sleep(0.125)

                            if count >= max_chase:
                                cp.red('[m] Give up, market order...')
                                r = self.cancel_order(oid=oid)
                                if r:
                                    self.rest.place_order(market=market, side=o['side'], price=None, size=o['remainingSize'],
                                                  _type='market',
                                                  reduce=o['reduce'], ioc=o['ioc'])
            else:
                return

    def parse_balances(self):
        bals = []
        for x in self.balances():
            if x['total'] == 0.0:
                pass
            else:
                bals.append(x)
        result = pd.DataFrame(bals)
        result.sort_values(by=['total'], ascending=False)
        return result

    def buy_limit(self, market, qty, price=None, post=False, reduce=False, cid=None):
        """
        Place a limit buy order
        """
        return self.rest.place_order(market=market, side='buy', price=price, size=qty, type='limit', reduce_only=reduce,
                                     post_only=post, client_id=cid)

    def buy_market(self, market, qty, reduce, ioc, cid=None):
        """
        Place a market buy order
        """
        return self.rest.place_order(market=market, side='buy', size=qty, type='market', reduce_only=reduce,
                                     post_only=False, client_id=cid, ioc=ioc, price=None)

    def sell_limit(self, market, qty, price=None, post=False, reduce=False, cid=None):
        """
        Place a sell limit order
        """
        return self.rest.place_order(market=market, side='sell', price=price, size=qty, type='limit',
                                     reduce_only=reduce,
                                     post_only=post, client_id=cid)

    def sell_market(self, market, qty, reduce, ioc, cid=None):
        """
        Place a market sell order
        """
        return self.rest.place_order(market=market, side='sell', size=qty, type='market', reduce_only=reduce,
                                     post_only=False, client_id=cid, ioc=ioc, price=None)

    def positions(self):
        return self.rest.get_positions()

    def balances(self):
        return self.rest.get_balances()

    def get_open_orders(self, market=None):
        return self.rest.get_open_orders(market=market)

    def cancel_order(self, oid):
        return self.rest.cancel_order(order_id=oid)

    def cancel_orders(self, market, conditional_orders=False, lmit_orders=False):
        return self.rest.cancel_orders(market_name=market, conditional_orders=conditional_orders,
                                       lmit_orders=lmit_orders)

    def modify_order(self, oid, price, size, cid=None):
        return self.rest.modify_order(existing_order_id=oid, price=price, size=size, client_order_id=cid)

    def trailing_stop(self, market, side, size, trail_value, reduce_only):
        return self.rest.place_conditional_order_(market=market, side=side, size=size, trailValue=trail_value,
                                                  _type='trailingStop', reduceOnly=reduce_only, triggerPrice=0.0)

    def stop_loss(self, market, side, triggerPrice):
        return self.rest.set_private_create_trigger_order(market=market, side=side, triggerPrice=triggerPrice)

    def info(self):
        return self.rest.get_account_info()

    def get_public_k_line(self, market, res, start, end):
        return self.rest.get_public_k_line(market=market, res=res, start_time=start, end_time=end)

    def futures(self):
        return self.rest.list_futures()

    def markets(self):
        return self.rest.list_markets()

    def addresses(self):
        return self.rest.get_deposit_address()

    def get_ticker(self, market):
        for i in range(10):
            ticker = self.ws.get_ticker(market=market)
            if ticker.items():
                return ticker['bid'], ticker['ask'], ticker['last']
            else:
                time.sleep(0.25)
            return 0, 0, 0

    def get_fills(self):
        for i in range(10):
            fills = self.ws.get_fills()
            if fills.items():
                return fills
            else:
                time.sleep(0.25)
            return None

    def get_orders(self):
        for i in range(10):
            orders = self.ws.get_orders()
            if orders.items():
                return orders
            else:
                time.sleep(0.25)
            return None

    def get_trades(self, market):
        for i in range(10):
            trades = self.ws.get_trades(market=market)
            if len(trades):
                return trades
            else:
                time.sleep(0.25)
            return None

    def get_orderbook(self, market):
        for i in range(10):
            orderbook = self.ws.get_orderbook(market=market)
            if orderbook.items:
                return orderbook
            else:
                time.sleep(0.25)
            return None

def debug_api(subacct=None, config_path='utils/conf.json'):
    """
    Load keys and return functional api object
    :return:
    """
    from utils import config_loader
    from exchanges.ftx_lib.rest import client
    from exchanges.ftx_lib.websocket_api import client as ws
    k, s, a = config_loader.load_config(config_path)
    if subacct:
        a = subacct
    rest = client.FtxClient(api_key=k, api_secret=s, subaccount_name=a)
    ws = ws.FtxWebsocketClient(api_key=k, api_secret=s, subaccount_name=a)
    return FtxApi(rest, ws, a)


