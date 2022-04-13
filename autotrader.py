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
from lib.exceptions import RestartError
from lib.pos_monitor import Monitor
from lib.receivers import WebSocketSignals
from trade_engine.api_wrapper import FtxApi
# from trade_engine.stdev_aggravator import FtxAggratavor
from utils import config_loader
from utils import logo
from utils.colorprint import NewColorPrint
from utils.ftx_exceptions import FtxDisconnectError
from utils.get_args import get_args
from lib import pnl_calc

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
                except RestartError:
                    ftx.__exit__()
                    self.restarts += 1
                    print('[!] Timeout error, restart!')
                except FtxDisconnectError as err:
                    ftx.__exit__()
                    self.restarts += 1
                    cp.red(f'[!] Websocket Disconnected: Restarts #: {self.restarts}, Error Message: {err}')



def parse_and_exec(args):
    limit_price = 0
    key, secret, subaccount = config_loader.load_config('conf.json')
    bot = Bot()

    if args.monitor or args.auto_trader or args.monitor_only or args.update_db:
        logo.post()
        if args.update_db:
            cp.red('[I] Updating the market database, please stand by ... ')
            exit()
        if args.monitor and not args.auto_trader:
            cp.navy('[🌡] Monitoring only mode.')

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
            cp.yellow('[m] Enabling mqtt signal client')
            cp.blue(f'[i] Receiver options: Min Score:{args.min_score}, Portfolio Pct: {args.portfolio_pct} '
                    f'Re-enter: {args.reenter} Data Source: '
                    f'{args.data_source}, Exclude Markets: {args.exclude_markets}, URI: {args.ws_uri}')

        if args.confirm and not args.monitor_only:
            cp.red(f'[!] WARN: Autotrader is enabled! This cam make or cost you money.')
            cp.yellow('[📊] Loading auto trader ... ')
        if args.show_tickers:
            cp.green('[~] Tickers Enabled!')
        bot.monitor(key=key, secret=secret, subaccount_name=args.subaccount, args=args)

    if args.show_portfolio or args.buy or args.sell or args.cancel or args.open_orders or args.configure_anti_liq \
            or args.trailing_stop_buy or args.trailing_stop_sell:
        api = bot.api_connection(key=key, secret=secret, subaccount=args.subaccount)
        rest = api[0]
        ws = api[1]
        api = FtxApi(rest=rest, ws=ws, sa=subaccount)
        if args.configure_anti_liq:
            pass




        if args.show_portfolio:
            balances = api.parse_balances()
            cp.yellow('Account Balances:')
            print(balances)
        if args.open_orders:
            cp.yellow('Querying API for open orders...')
            orders = api.rest_get_open_orders()
            for o in orders:
                print(o)

        if args.trailing_stop_buy:

            """{'future': 'AXS-PERP', 'size': 1.1, 'side': 'buy', 'netSize': 1.1, 'longOrderSize': 0.0,
             'shortOrderSize': 0.0, 'cost': 49.7475, 'entryPrice': 45.225, 'unrealizedPnl': 0.0, 're
                 alizedPnl': 28.41865541, 'initialMarginRequirement': 0.05, 'maintenanceMarginRequirement
             ': 0.03, 'openSize': 1.1, 'collateralUsed': 2.487375, 'estimatedLiquidationPrice': 18.72
                 990329657341, 'recentAverageOpenPrice': 45.207, 'recentPnl': 0.0198, 'recentBreakEvenPrice': 45.207,
             'cumulativeBuySize': 1.1, 'cumulativeSellSize': 0.0}"""
            if len(args.trailing_stop_buy) < 3:
                cp.red('[⛔] <market> <qty> <offset_percent>')
            else:
                market = args.trailing_stop_buy[0]
                qty = args.trailing_stop_buy[1]
                offset = args.trailing_stop_buy[2]
                pos = api.positions()
                info = api.info()
                for p in pos:
                    print(p)
                    if float(p['collateralUsed'] != 0.0) or float(p['longOrderSize']) > 0 or float(
                            p['shortOrderSize']) < 0:
                        if p['future'] == market:
                            bid, ask, last = api.get_ticker(market)
                            entry = p['entryPrice']
                            size = p['size']
                            cost = p['cost']
                            fee = info['takerFee']
                            pnl = pnl_calc.pnl_calc(qty=size, sell=ask, buy=entry, fee=fee)
                            pnl_pct = (float(pnl) / float(cost)) * 100
                            current_price = api.get_ticker(market=market)[1]
                            print(current_price, offset, entry)
                            trail_value = float((current_price) - float(entry)) * float(offset) * -1
                            # offset_price = (float(current_price) - float(entry_price)) * (1-offset)
                            offset_price = float(current_price) - (float(current_price) - float(entry)) * float(offset)

                            if pnl_pct > 0.0:
                                print(f'[t] Trailing sell stop for long triggered: PNL: {pnl_pct}, offset: {offset}, '
                                      f'Trail: {trail_value}')
                                ret = api.trailing_stop(market=market, side='sell', offset=offset_price, qty=qty,
                                                             reduce=True)
                                print(ret)
                            else:
                                print(f'Position is not in profit!')


        if args.trailing_stop_sell:
            if len(args.buy) < 3:
                cp.red('[⛔] <market> <qty> <offset_percent>')
                market = args.trailing_stop_sell[0]
                qty = args.trailing_stop_sell[1]
                offset = args.trailing_stop_sell[2]

        if args.buy:
            if len(args.buy) < 3:
                cp.red('[⛔] Required parameters: <order type> <market> <qty> Optional Parameters: <price>')
                return False
            else:
                post = False
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
                if o_type == 'limit' or o_type == 'post':

                    if limit_price == 0:
                        bid, ask, last = api.get_ticker(market=o_market)
                        limit_price = bid
                        cp.red(f'[!] No price given, using current bid: {bid}')

                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    if args.limit_chase > 0 or o_type == 'post':
                        post = True

                    ret = api.buy_limit(market=o_market, qty=o_size, price=limit_price, post=post, reduce=False,
                                        cid=None)
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
                post = False
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
                if o_type == 'limit' or o_type == 'post':
                    if limit_price == 0:
                        bid, ask, last = api.get_ticker(market=o_market)
                        print(ask, bid, last)
                        limit_price = ask
                        cp.yellow(f'[!] No price given, using current ask: {ask}')
                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    if args.limit_chase > 0 or o_type == 'post':
                        post = True
                    ret = api.sell_limit(market=o_market, qty=o_size, price=limit_price, post=post, reduce=False, cid=None)
                    if args.limit_chase > 0:
                        cp.yellow(f'[-] Chasing limit order up the books ... Max Chase: {args.limit_chase} '
                                  f'Revert to market: {args.chase_failsafe}')
                        ret = api.chase_limit_order(market=o_market, oid=ret['id'], max_chase=args.limit_chase,
                                              failsafe_market=args.chase_failsafe)
                        cp.purple(f'[~] {ret}')
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

    if args.confirm and args.auto_trader:
        args.monitor_only = False
        for _ in range(0, 3):
            cp.random_color(f'[⚡! TOASTERTUB DISCLAIMER: You have specified `--confirm` which means that THIS BOT WILL '
                            f'interact with the FTX api, performing whatever actions were requested by *you*.]',  static_set='bright')
            time.sleep(0.125)
    else:
        if args.auto_trader:
            args.monitor_only = True

    parse_and_exec(args)


if __name__ == '__main__':
    main()
