#!/usr/bin/env python3
##########################################################################################

"""



  ██████╗ ██╗      █████╗  ██████╗██╗  ██╗███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗
  ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
  ██████╔╝██║     ███████║██║     █████╔╝ ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝
  ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗
  ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║
  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
    ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    github.com/darkerego - 2020 - 2021 0- 0x7612E93FF157d1973D0f95Be9E4f0bdF93BAf0DE
    ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
           FTX Trade Mirroring Platform ~ Darkerego, 2020-2021 ~ version 2.6
            - experimental `oscillation arbitrage` - websocket signal support -
            volatility driven auto trader - "maket taker" strategy - incremental, market -  market maker mode -
             global market trend analysis - custom strategy support - automatic position building -
             auto hedge management - api navigator - and much more

             Use this FTX Referral for a discount on fees and to support my work!!! :
                                  https://ftx.com/referrals#a=blackmirror

    """

import logging
import time
from exchanges.ftx_lib.rest import client
from exchanges.ftx_lib.websocket_api import client as ws_client
from lib.pos_monitor import Monitor
from lib.receivers import WebSocketSignals
from trade_engine.api_wrapper import FtxApi
# from trade_engine.stdev_aggravator import FtxAggratavor
from utils import config_loader
from utils import logo
from utils.colorprint import NewColorPrint
from utils.ftx_exceptions import FtxDisconnectError
from utils.get_args import get_args

try:
    import thread
except ImportError:
    import _thread as thread

logo.start()
use_custom_ts = False
debug = True
logging.basicConfig()
ws_signals = WebSocketSignals()


class Bot:
    restarts = 0

    def api_connection(self, key, secret, subaccount):
        global ws
        global rest
        ws = ws_client.FtxWebsocketClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        rest = client.FtxClient(api_key=key, api_secret=secret, subaccount_name=subaccount)
        return rest, ws

    def con(self, key, secret, subaccount_name=None, args=None):
        api = self.api_connection(key=key, secret=secret, subaccount=subaccount_name)
        rest = api[0]
        ws = api[1]

        return Monitor(rest=rest, ws=ws, subaccount=subaccount_name, conf=args)

    def monitor(self, key, secret, subaccount_name=None, args={}):
        while True:
            with self.con(key=key, secret=secret, subaccount_name=subaccount_name, args=args) as ftx:
                try:
                    cp.navy('[🌡] Monitoring...')
                    ftx.monitor()
                    cp.red('Done...')
                except KeyboardInterrupt:
                    ftx.__exit__()
                    print('\bCaught SIGINT - Terminate. \n')
                    cp.red(1)
                    exit(0)
                except FtxDisconnectError as err:
                    ftx.__exit__()
                    self.restarts += 1
                    cp.red(f'[!] Websocket Disconnected: Restarts #: {self.restarts}, Error Message: {err}')


def parse_and_exec(args):
    limit_price = 0
    key, secret, subaccount = config_loader.load_config('conf.json')
    bot = Bot()



    if args.monitor_only:
        cp.navy('[🌡] Monitoring only mode.')
        #bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

    if args.monitor or args.auto_trader or args.monitor_only:
        logo.post()
        if args.balance_arbitrage:
            cp.navy('WARNING: EXPERIMENTAL !! -- Loading balance arbitrage engine...')
            # bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)
        if args.use_strategy:
            cp.navy(f'WARNING: EXPERIMENTAL !! -- Loading TA Strategy Trader ... Strategy: {args.strategy}')
            # bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

        if args.enable_ws:
            cp.yellow('Enabling ws signal client')
            # bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)
        if args.enable_mqtt:
            cp.yellow('Enabling mqtt signal client')

        if args.confirm and not args.monitor_only:
            cp.red(f'[!] WARN: Autotrader is enabled! This cam make or cost you money.')
            cp.yellow('[📊] Loading auto trader ... ')
        if args.show_tickers:
            cp.green('[~] Tickers Enabled!')
        bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

    if args.show_portfolio or args.buy or args.sell or args.cancel or args.open_orders:
        api = bot.api_connection(key=key, secret=secret, subaccount=subaccount)
        rest = api[0]
        ws = api[1]
        api = FtxApi(rest=rest, ws=ws, sa=subaccount)
        if args.show_portfolio:
            balances = api.parse_balances()
            cp.yellow('Account Balances:')
            print(balances)
        if args.open_orders:
            cp.yellow('Querying API for open orders...')
            orders = api.ws_get_orders()
            print(orders)

        if args.buy:
            if len(args.buy) < 3:
                cp.red('[⛔] Required parameters: <order type> <market> <qty> Optional Parameters: <price>')
                return False
            else:
                o_type = args.buy[0]
                o_market = args.buy[1]
                o_size = args.buy[2]
                if len(args.buy) == 4:
                    limit_price = args.buy[3]
                if o_type == 'market':
                    cp.green(f'[~] Executing a market buy order on {o_market} of quantity {o_size}!')
                    ret = api.buy_market(market=o_market, qty=o_size, reduce=False, ioc=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
                if o_type == 'limit':
                    if limit_price == 0:
                        bid, ask, last = api.get_ticker(market=o_market)
                        limit_price = bid
                        cp.red(f'[!] No price given, using current bid: {bid}')

                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    ret = api.buy_limit(market=o_market, qty=o_size, price=limit_price, reduce=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
                    if args.limit_chase > 0:
                        cp.yellow(f'[-] Chasing limit order up the books ... Max Chase: {args.limit_chase} '
                                  f'Revert to market: {args.chase_failsafe}')
                        ret = api.chase_limit_order(market=o_market, oid=ret['id'], max_chase=args.limit_chase,
                                              failsafe_market=args.chase_failsafe)
                        cp.purple(f'[~] {ret}')


        if args.sell:
            if len(args.sell) < 3:
                cp.red('[⛔] Required parameters: <order type> <market> <qty> Optional Parameters: <price>')
                return False
            else:
                o_type = args.sell[0]
                o_market = args.sell[1]
                o_size = args.sell[2]
                if len(args.sell) == 4:
                    limit_price = args.sell[3]
                if o_type == 'market':
                    cp.red(f'[~] Executing a market sell order on {o_market} of quantity {o_size}!')
                    ret = api.sell_market(market=o_market, qty=o_size, reduce=False, ioc=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
                if o_type == 'limit':
                    if limit_price == 0:
                        bid, ask, last = api.get_ticker(market=o_market)
                        limit_price = ask
                        cp.yellow(f'[!] No price given, using current ask: {ask}')
                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    ret = api.sell_limit(market=o_market, qty=o_size, price=limit_price, reduce=False, cid=None)
                    if ret:
                        cp.purple(f'[~] Status: {ret}')
        if args.cancel:
            oid = args.cancel
            cp.red(f'[c] Canceling order #{oid}')
            ret = api.cancel_order(oid=oid)
            if ret:
                cp.purple(f'[~] Status: {ret}')


def main():
    global cp
    cp = NewColorPrint()
    args = get_args()

    if args.confirm:
        args.monitor_only = False
        for _ in range(0, 3):
            cp.random_color(f'[⚡! TOASTERTUB DISCLAIMER: You have specified `--confirm` which means that THIS BOT WILL '
                            f'interact with the FTX api, performing whatever actions were requested by *you*.]',  static_set='bright')
            time.sleep(0.125)
    else:
        args.monitor_only = True

    parse_and_exec(args)


if __name__ == '__main__':
    main()
