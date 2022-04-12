import pandas as pd
import time
from utils.colorprint import NewColorPrint as cp
import logging
from lib.func_timer import exit_after, cdquit
cp = cp()


class FtxApi:
    """
    Api Function Wrapper
    """

    def __init__(self, rest, ws, sa=None):
        self.rest = rest
        self.ws = ws
        self.sa = sa
        self.logger = logging.getLogger(__name__)

    def chase_limit_order(self, market, oid, max_chase=3, failsafe_market=False):
        self.logger.info(f'Chasing order {market}, {oid}')
        time.sleep(1.5)
        last_price = 0
        count = 0
        time.sleep(1)
        while True:
            for _ in range(3):
                o = self.rest_get_open_orders(market=market, oid=oid)


                if o:
                    print('order:', o)
                    ask, bid, last = self.get_ticker(market=market)
                    last_price = o['price']

                    if o['id'] == oid:
                        size = o['size']
                        if o['status'] == 'filled' or o['status'] == 'closed':
                            cp.red(f'[*] Order {oid}: Status: {o["status"]}')
                            return
                        else:
                            if o['side'] == 'buy':
                                current_price = bid
                                print(current_price)
                                if current_price > last_price:

                                    print(f'Modify order from {last_price} to {current_price}')
                                    ret = self.modify_order(oid=oid, price=current_price)
                                    last_price = current_price
                                    if ret:
                                        self.logger.info('Success: ', ret.__str__)
                                        count += 1
                                    else:
                                        self.logger.info('Fail: ', ret.__str__)
                                    time.sleep(0.125)
                            else:
                                current_price = ask
                                if current_price < last_price:
                                    last_price = current_price
                                    ret = self.modify_order(oid=oid, price=current_price,
                                                            size=o['remainingSize'])
                                    if ret:
                                        self.logger.info('Success: ', ret.__str__)
                                        count += 1
                                    else:
                                        self.logger.info('Fail: ', ret.__str__)
                                    time.sleep(0.125)

                            if count >= max_chase:
                                self.logger.info('Give up.')
                                if failsafe_market:
                                    cp.red('[m] Give up, market order...')
                                    r = self.rest.cancel_order(oid=oid)
                                    if r:
                                        ret = self.rest.place_order(market=market, side=o['side'], price=None,
                                                                    size=o['remainingSize'],
                                                                    _type='market',
                                                                    reduce=o['reduce'], ioc=o['ioc'])
                                        if ret:
                                            return ret
                                        else:
                                            cp.red(f'[!] FAILED TO PLACE MARKET ORDER!')
                                            return False
                    else:
                        return
                else:
                    print('No orders ..')
                    return False

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



    """def trailing_stop(self, market, side, offset, qty, reduce=True):
       '''
        self, market: str, side: str, size: float, type: str = 'stop',
            limit_price: float = None, reduce_only: bool = False, cancel: bool = True,
            trigger_price: float = None, trail_value: float = None
        '''
        return self.rest.place_conditional_order(market=market, side=side, size=qty, type='trailing_stop',
                                                 reduce_only=reduce, trail_value=offset)"""


    def positions(self):
        return self.rest.get_positions()

    def balances(self):
        return self.rest.get_balances()

    def rest_get_open_orders(self, market=None, oid=None):
        orders = self.rest.get_open_orders(market=market)
        if oid:
            for _ in orders:
                if _['id'] == oid:
                    return _
        else:
            return orders

    def cancel_order(self, oid):
        return self.rest.cancel_order(order_id=oid)

    def cancel_orders(self, market, conditional_orders=False, limit_orders=False):
        return self.rest.cancel_orders(market_name=market, conditional_orders=conditional_orders,
                                       limit_orders=limit_orders)

    def modify_order(self, oid, price=None, size=None, cid=None):
        return self.rest.modify_order(existing_order_id=oid, price=price, size=size, client_order_id=cid)

    def trailing_stop(self, market, side, size, trail_value, reduce_only):
        #print(market, side, size, trail_value, reduce_only)
        ret = self.rest.place_conditional_order(market=market, side=side, size=size, trail_value=trail_value,
                                                  type='trailingStop', reduce_only=reduce_only)
        #print(ret)
        return ret

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
                time.sleep(0.125)
        return 0, 0, 0

    def get_fills(self):
        for i in range(10):
            fills = self.ws.get_fills()
            if fills.items():
                return fills
            else:
                time.sleep(0.25)
            return None

    def ws_get_orders(self):
        for i in range(10):
            orders = self.ws.get_orders()
            print('orders', orders)
            if orders.items():
                print(orders)
                return orders
            else:
                time.sleep(0.25)
        return None

    def ws_get_order_by_id(self, oid):
        for i in range(10):
            orders = self.ws_get_orders()
            if orders:
                print(orders.get('id'))

                for o in orders:
                    print(o)
                    if o['id'] == oid:
                        return o
        return

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

    def get_subaccounts(self):
        return self.rest.get_subaccounts()

    def new_subaccount(self, nickname):
        return self.rest.create_subaccount(nickname=nickname)

    def get_subaccount_balances(self, nickname: str):
        return self.rest.get_subaccount_balances(nickname=nickname)

    def transfer(self, coin, size, source, destination):
        return self.rest.tranfer(coin, size, source, destination)


def debug_api(subacct=None, config_path='conf.json'):
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
