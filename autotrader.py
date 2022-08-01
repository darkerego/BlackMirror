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

import asyncio
import logging
import threading
import time


from lib.auto_trader import tally
from lib.exceptions import RestartError
from lib.pos_monitor import Monitor
from lib.receivers import WebSocketSignals
from lib.sql_lib import SQLLiteConnection
from trade_engine.api_wrapper import FtxApi
# from trade_engine.stdev_aggravator import FtxAggratavor
from utils import config_loader
from utils import logo
from utils.colorprint import NewColorPrint
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
    lock = threading.Lock()
    restarts = 0





    async def monitor(self, api, args={}):
        while True:
            print('Starting mon')
            with Monitor(api, conf=args) as ftx:
                try:
                    cp.navy('[🌡] Monitoring...')
                    # await ftx.receiver()
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


async def parse_and_exec(args):
    limit_price = 0
    key, secret, subaccount, anti_liq = config_loader.load_config('conf.json')
    bot = Bot()
    subaccount = args.subaccount

    if args.reset_db:
        cp.yellow('[~] Resetting the pnl stats ... ')
        tally.reset()

    if args.monitor or args.auto_trader or args.update_db or args.dumpdb:
        if args.dumpdb:
            sql = SQLLiteConnection()
            futs  =sql.get_list('futures')
            for _ in futs:
                print(_)
            exit()

        logo.post()
        if args.update_db:
            cp.red('[I] Updating the market database, please stand by ... ')

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

        if args.confirm:
            cp.red(f'[!] WARN: Autotrader is enabled! This cam make or cost you money.')
            cp.yellow('[📊] Loading auto trader ... ')
        if args.show_tickers:
            cp.green('[~] Tickers Enabled!')
        api = FtxApi(key, secret, subaccount)
        await bot.monitor(api, args=args)


    if args.show_portfolio or args.buy or args.sell or args.cancel or args.open_orders or args.configure_anti_liq \
            or args.trailing_stop_buy or args.trailing_stop_sell or args.set_leverage:

        #api = bot.api_connection(key=key, secret=secret, subaccount=args.subaccount)
        #rest = api[0]
        #ws = api[1]

        if args.set_leverage:
            cp.yellow('Setting leverage ... ')
            print(api.leverage(lev=args.set_leverage))
        if args.configure_anti_liq:
            cp.yellow('[~] Configuring AntiLiq .. ')
            ret = api.info().get('freeCollateral')
            if ret > 0:
                balances = api.balances()
                for x in balances:
                    if x.get('coin') == 'USD':
                        avail = x.get('availableWithoutBorrow')
                        if avail <= 0:
                            cp.yellow(f'[!] Please deposit some USD in this account and try again.')
                            exit()
                        else:
                            sas = api.get_subaccounts()
                            print(sas)
                            time.sleep(5)
                            q = avail / 5
                            cp.yellow(f'[!] Transferring {q} USD to LIQUIDITY subaccount. This will be used as '
                                      f'EMERGENCY funds to prevent liquidation. Do not trade with it!')
                            api.transfer('USD', q, )

                print(balances[0])
                time.sleep(5)
                try:
                    sas = api.get_subaccounts()
                except Exception:
                    cp.red('Ensure you have permission to transfer and create subaccounts and try again!')
                else:
                    try:
                        reserve_sa = api.new_subaccount('LIQUIDITY')
                    except Exception as err:
                        cp.red('Ensure you have permission to transfer and create subaccounts and try again!')
                    else:
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
                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    if args.limit_chase > 0 or o_type == 'post':
                        ret = api.post_limit_retry(market=o_market, side='buy', qty=o_size)
                    else:
                        if limit_price == 0:
                            bid, ask, last = api.rest_ticker(market=o_market)
                            limit_price = bid
                            cp.red(f'[!] No price given, using current bid: {bid}')
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
                    cp.red(f'[~] Executing a limit sell order on {o_market} of quantity {o_size}!')
                    if args.limit_chase > 0 or o_type == 'post':
                        ret = api.post_limit_retry(market=o_market, side='sell', qty=o_size)
                    else:
                        if limit_price == 0:
                            bid, ask, last = api.get_ticker(market=o_market)
                            print(ask, bid, last)
                            limit_price = ask
                            cp.yellow(f'[!] No price given, using current ask: {ask}')
                        ret = api.sell_limit(market=o_market, qty=o_size, price=limit_price, post=post, reduce=False,
                                             cid=None)
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


async def main():
    global cp
    cp = NewColorPrint()
    args = get_args()

    if args.confirm and args.auto_trader:
        args.monitor_only = False
        for _ in range(0, 3):
            cp.random_color(f'[⚡! TOASTER TUB DISCLAIMER: You have specified `--confirm` which means that THIS BOT WILL '
                            f'interact with the FTX api, performing whatever actions were requested by *you*.]',  static_set='bright')
            time.sleep(0.125)



    await parse_and_exec(args)


if __name__ == '__main__':
    asyncio.run(main())
