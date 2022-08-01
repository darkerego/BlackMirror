import pandas as pd
import time
from utils.colorprint import NewColorPrint as cp
import logging
cp = cp()
from exchanges.ftx_lib.rest import client
from exchanges.ftx_lib.websocket_api import client as ws_client

class FtxApi:
    """
    Api Function Wrapper
    """

    def __init__(self, key, secret, sa=None):
        self.ws = ws_client.FtxWebsocketClient(api_key=key, api_secret=secret, subaccount_name=sa)
        self.rest = client.FtxClient(api_key=key, api_secret=secret, subaccount_name=sa)
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
                o = self.ws_get_order_by_id(oid=oid)
                if o:
                    print('o', o)
                    break
            if not o:
                    print('No orders .. must have filled or never placed')
                    return False
            else:
                    ask, bid, last = self.get_ticker(market=market)
                    print(ask, bid, last)
                    last_price = o['price']
                    print('order:', o)
                    if o['id'] == oid:
                        size = o['remainingSize']
                        _type = o['type']
                        if o['status'] == 'filled' or o['status'] == 'closed':
                            cp.red(f'[*] Order {oid}: Status: {o["status"]}')
                            break
                        else:

                            if o['side'] == 'buy':
                                current_price = bid
                                print(current_price)
                                print('Chase Buy order')
                                if count < max_chase:
                                    if current_price > last_price:

                                        print(f'Modify order from {last_price} to {current_price}')
                                        cret = self.cancel_order(oid)
                                        if cret:
                                            while True:
                                                ret = self.buy_limit(market=market, qty=size, price=current_price, post=True)

                                                if ret['id']:
                                                    break
                                        last_price = current_price
                                        if ret:
                                            self.logger.info('Success: ', ret.__str__)
                                            oid = ret['id']
                                            count += 1
                                        else:
                                            self.logger.info('Fail: ', ret.__str__)
                                            time.sleep(0.125)
                                    else:
                                        time.sleep(0.125)
                            else:
                                    print('Chase Sell order')
                                    current_price = ask
                                    if current_price < last_price:
                                        last_price = current_price
                                        cret = self.cancel_order(oid)
                                        if cret:
                                            ret = self.post_limit_retry(market=market, side='buy', qty=size)
                                        if ret:
                                            self.logger.info('Success: ', ret.__str__)
                                            oid = ret['id']
                                            count += 1
                                        else:
                                            self.logger.info('Fail: ', ret.__str__)
                                        time.sleep(0.125)

                                    if count >= max_chase:
                                        self.logger.info('Give up.')
                                        if failsafe_market:
                                            cp.red('[m] Give up, market order...')
                                            cret = self.rest.cancel_order(oid=oid)
                                            if cret:
                                                ret = ret = self.post_limit_retry(market=market, side='sell', qty=size)
                                                if ret:
                                                    return ret
                                                else:
                                                    cp.red(f'[!] FAILED TO PLACE MARKET ORDER!')
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

    def get_market(self, market):
        ret = self.get_markets()
        for _ in ret:
            if _.get('name') == market:
                return _

    def get_markets(self):
        return self.rest.list_markets()

    def rest_ticker(self, market):
        ret = self.get_market(market)
        #ret = self.rest.list_markets()
        bid = ret['bid']
        ask = ret['ask']
        last = ret['last']
        return bid, ask, last

    def post_limit_retry(self, market, side, qty, reduce=False):
        if side == 'buy':
            while True:
                price = self.rest_ticker(market=market)[0]
                ret = self.buy_limit(market, qty, price=price, post=True, reduce=reduce)
                if ret['id']:
                    break
                time.sleep(0.125)
        else:
            while True:
                price = self.rest_ticker(market=market)[1]
                ret = self.sell_limit(market, qty, price=price, post=True, reduce=reduce)
                if ret['id']:
                    break
                time.sleep(0.125)
        return ret

    def leverage(self, lev):
        return self.rest.leverage(lev)



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

    def rest_get_open_orders(self, market=None, oid=None):
        orders = self.rest.get_open_orders(market=market)
        #print(orders)
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
        ret = self.rest.place_conditional_order(market=market, side=side, size=size, trail_value=trail_value,
                                                  type='trailingStop', reduce_only=reduce_only)
        return ret

    def stop_loss(self, market, side, size, trigger_price, limit_price=None, reduce_only=True):
        """
        market: str, side: str, size: float, type: str = 'stop',
            limit_price: float = None, reduce_only: bool = False, cancel: bool = True,
            trigger_price: float = None, trail_value: float = None
        """
        if limit_price is None:
            # stop market
            return self.rest.place_conditional_order(market=market, size=size, side=side, type='stop', trigger_price=trigger_price,
                                                     reduce_only=reduce_only)
        else:
            return self.rest.place_conditional_order(market=market, side=side, size=size, type='stopLimit', trigger_price=trigger_price,
                                                     reduce_only=reduce_only)

    def take_profit(self, market, side, size, triggerPrice, limit_price=None, reduce_only=True):
        """
                market 	string 	XRP-PERP
                side 	string 	sell 	"buy" or "sell"
                size 	number 	31431.0
                type 	string 	stop 	"stop", "trailingStop", "takeProfit"; default is stop
                reduceOnly 	boolean 	false 	optional; default is false
                retryUntilFilled 	boolean 	false 	Whether or not to keep re-triggering until filled. optional, default
                true for market orders
                triggerPrice 	number 	0.306525
                orderPrice 	number 	0.3063 	optional; order type is limit if this is specified; otherwise market
        """
        return self.rest.place_conditional_order(market=market, side=side, size=size, type='takeProfit',
                                                 trigger_price=triggerPrice, limit_price=limit_price,
                                                 reduce_only=reduce_only)

    def info(self):
        return self.rest.get_account_info()

    def get_public_k_line(self, market, res, limit=20, start=None, end=None):
        return self.rest.get_public_k_line(market=market, resolution=res, limit=limit, start_time=start, end_time=end)

    def futures(self):
        return self.rest.list_futures()

    def markets(self):
        return self.rest.list_markets()

    def addresses(self):
        return self.rest.get_deposit_address()

    def get_ticker(self, market):
        for i in range(10):
            ticker = self.ws.get_ticker(market=market)
            #print(ticker)
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
            # print('orders', orders)
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
                    if o['id'] == oid:
                        return o
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

    def get_subaccounts(self):
        return self.rest.get_subaccounts()

    def new_subaccount(self, nickname):
        return self.rest.create_subaccount(nickname=nickname)

    def get_subaccount_balances(self, nickname: str):
        return self.rest.get_subaccount_balances(nickname=nickname)

    def transfer(self, coin, size, source, destination):
        return self.rest.tranfer(coin, size, source, destination)

    def latency(self):
        return self.rest.get_latency_stats()

    def ws_order_stream(self):
        return self.ws.get_orders()

    def rest_trigger_order_history(self):
        return self.rest.get_conditional_order_history()


def debug_api(subacct=None, config_path='conf.json'):
    """
    Load keys and return functional api object
    :return:
    """
    from utils import config_loader
    from exchanges.ftx_lib.rest import client
    from exchanges.ftx_lib.websocket_api import client as ws
    k, s, a, l = config_loader.load_config(config_path)
    if subacct:
        a = subacct
    rest = client.FtxClient(api_key=k, api_secret=s, subaccount_name=a)
    ws = ws.FtxWebsocketClient(api_key=k, api_secret=s, subaccount_name=a)
    return FtxApi(rest, ws, a)
