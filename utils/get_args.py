import argparse
import configargparse


def geneneral_options():
    args = argparse.ArgumentParser()



def get_args():
    parser = configargparse.ArgumentParser(usage='SUPPORT MY WORK! USE MY REFERRAL: https://ftx.com/referrals#a=darkerego')
    gen_opts = parser.add_argument_group('General Opts')
    gen_opts.description = 'General Options'
    gen_opts.add_argument('-m', '--monitor', dest='monitor', action='store_true', default=False,
                          help='Start the account monitor. See '
                               'current status.')
    gen_opts.add_argument('--configure', dest='configure_anti_liq', action='store_true',
                          help='Configure AntiLiquidation feature -- highly recommended!')
    gen_opts.add_argument('-sa', '--subaccount', dest='subaccount', default=None, type=str, help='Subaccount to connect'
                                                                                                 'to. None for main '
                                                                                                 'account.')
    gen_opts.add_argument('--antiliq', dest='anti_liq', action='store_true')
    gen_opts.add_argument('--rsp', '--reserve_pct',  dest='anti_liq_pct', type=float, default=0.1, help='Stash this '
                                                                                                        'amount of '
                                                                                                        'profit for '
                                                                                                        'emergency '
                                                                                                        'situations, '
                                                                                                        'where 0.1 is 10 '
                                                                                                        'percent.')
    gen_opts.add_argument('-nlp', '--new_listing_percentage', dest='new_listing_percent', type=float, default=0.25,
                          help='Floating point percentage of equity to use on new listing orders. 1 is 100')

    gen_opts.add_argument('-rst', '--reset', dest='reset_db', action='store_true', help='Reset PNL and Volume stats')

    gen_opts.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False, help='Verbose mode.')
    gen_opts.add_argument('-st', '--show_tickers', dest='show_tickers', action='store_true', default=False,
                          help='Do not show tickers.')
    exchange_stats_opts = parser.add_argument_group('Exchange Statistical Options')
    exchange_stats_opts.add_argument('-u', '--update_db', action='store_true',
                                     dest='update_db', help='Initialize/Update the market stat'
                                                                                    'database.')
    exchange_stats_opts.add_argument('-dump', '--dumpdb', action='store_true', dest='dumpdb', help='Dumb the database.')

    """arb_opts = parser.add_argument_group('OscillationArbitrage Engine Options')
    arb_opts.add_argument('-O', '--osc_arb', dest='balance_arbitrage', action='store_true',
                          help='Run experimental balance arbitrage engine.')
    arb_opts.add_argument('-ls', '--long_symbols', dest='long_symbols', type=str, nargs='+', help='List of instruments '
                                                                                                  'to long.')
    arb_opts.add_argument('-ss', '--short_symbols', dest='short_symbols', type=str, nargs='+', help='List of symbols '
                                                                                                    'to short')
    arb_opts.add_argument('-mp', '--min_spread', dest='min_spread', type=float, default=0.25,
                          help='Minimum arbitrage spread to target.')
    arb_opts.add_argument('-cc', '--chase_close', dest='chase_close', type=int, default=0, help='Use order chase for '
                                                                                                'position close')
    arb_opts.add_argument('-cr', '--chase_reopen', dest='chase_reopen', type=int, default=0, help='Use order chase '
                                                                                                  'for position '
                                                                                                  'reopen')"""
    strategy_opts = parser.add_argument_group('EXPERIMENTAL Trade Strategy Options')
    strategy_opts.add_argument('-S', '--strategy', dest='use_strategy', action='store_true', default=False,
                               help='Use the TA based trade strategy engine.')
    strategy_opts.add_argument('-str', '--strat', dest='strategy', type=str, choices=['sar'], default='SAR',
                               help='Trade Strategy to use')
    strategy_opts.add_argument('-sy', '--symbol', dest='symbol', type=str, default=None,
                               help='FTX instrument to trade.')
    strategy_opts.add_argument('-sym', '--symbol_monitor', dest='symbol_monitor', default=None,
                               help='Binance symbol to watch.')
    strategy_opts.add_argument('-xs', '--contract_size', dest='contract_size', type=float, default=0.0)
    receiver_opts = parser.add_argument_group('Websocket Trade Signal Options')
    receiver_opts.add_argument('-ws', '--ws_signals', action='store_true', dest='enable_ws', default=False,
                               help='Enable websocket client for signals')
    receiver_opts.add_argument('-mq', '--mqtt_signals', action='store_true', dest='enable_mqtt',
                               help='Enable mqtt receiver for automatic trading of signals.')
    receiver_opts.add_argument('-uri', '--ws_uri', dest='ws_uri', type=str, default='ws://localhost:8000',
                               help='Websocket/Mqtt uri, wss://host:port | localhost:1883')
    receiver_opts.add_argument('-mt', '--mqtt_topic', dest='mqtt_topic', default='/signals', help='MqTT Topic For '
                                                                                                  'Signals')
    receiver_opts.add_argument('-lS', '--live_score', dest='live_score', action='store_true', help='Experimental: '
                                                                                                   'use the real-time'
                                                                                                   'analysis feed.')
    receiver_opts.add_argument('-pf', '--portfolio_pct', dest='portfolio_pct', type=float, default=.1,
                               help='Float representing pct of'
                                    'holdings to use on incoming'
                                   'trade.')
    receiver_opts.add_argument('-re', '--reenter', dest='reenter', default=False, action='store_true',
                               help='Re enter position before it closes if price hits entry again.')
    receiver_opts.add_argument('-cbo', '--check', action='store_true', dest='check_before_reopen', help='Before reopening a position, '
                                                                                  'check the current TA score.')
    receiver_opts.add_argument('-src', '--data_source', dest='data_source', type=str, choices=['binance'],
                               default='binance',
                               help='Exchange where the'
                                    'signals were aggravated.')
    receiver_opts.add_argument('-exc', '--exclude_markets', dest='exclude_markets', type=str, default=[],
                               help='Do not trade these markets',
                               nargs='*')
    receiver_opts.add_argument('-ms', '--min_score', dest='min_score', type=float, default=25, help='Minimum score to '
                                                                                                    'execute a trade '
                                                                                                    'from a received '
                                                                                                    'signal.')
    receiver_opts.add_argument('-ma', '--min_adx', dest='min_adx', type=float, default=20, help='Min mean adx to enter '
                                                                                                'trade.')
    receiver_opts.add_argument('-sv', '--sar_validation', dest='sar_validation', default=[60, 300], type=int, nargs='+'
                               , help='The period(s) to validate the signal for with sar. Set to 0 to disable.')

    auto_stop_opts = parser.add_argument_group('Auto Stop Loss Options')
    auto_stop_opts.add_argument('-a', '--auto', dest='auto_trader', action='store_true', help='Use AutoTrader')

    auto_stop_opts.add_argument('--trade', '--really', dest='confirm',
                                action='store_true',
                                help='This is a FAILSAFE options to'
                                     'prevent accidental losses! Will not'
                                     'trade automatically without enabling.')

    auto_stop_opts.add_argument('-ds', '--disable_sl', dest='disable_stop_loss', action='store_true', default=False,
                                help='Do not use stop losses.')
    auto_stop_opts.add_argument('-aso', '--auto_stop_only', dest='auto_stop_only', action='store_true',
                                help='Only manage stop losses and not '
                                                                                      'take profit.')

    auto_stop_opts.add_argument('-sl', '--stop_loss', dest='stop_loss_pct', action='store', type=float, default=0.5,
                                help='Stop Loss Percentage represented as a floating point. -0.1 would be -10 percent PNL')
    auto_stop_opts.add_argument('-tp', '--take_profit', dest='take_profit_pct', type=float, default=5.0,
                                help='Percentage '
                                     'to '
                                     'take profit '
                                     'at, represented'
                                     'as sa floating point number.'
                                     '0.2 wouild be 20 pcercent')

    auto_stop_opts.add_argument('-ts', '--trailing_stop_offset', dest='ts_offset', type=float, default=0.25,
                                help='Trailing stop offset, represented as a floating point number, percentage of pnl.')
    auto_stop_opts.add_argument('-ot', '--order_type', choices=['limit', 'market'], default='market',
                                type=str, help='Take profit order type.')
    auto_stop_opts.add_argument('-ro', '--reopen', dest='reopen_method', choices=['increment', 'market', None],
                                default=None,
                                help='Method to use to reopen positions. Market just sends a limit or market order. Increment '
                                     'splits size into several smaller orders according to standard deviation')
    auto_stop_opts.add_argument('-cm', '--close_method', dest='close_method', choices=['increment', 'market', 'limit', 'trailing', False],
                                default='trailing', help='Method to use to close positions. Market just sends a limit '
                                                       'or market order. Increment '
                                                       'splits size into several smaller orders according to standard deviation')
    auto_stop_opts.add_argument('-ip', '--increment_period', dest='increment_period',
                                choices=[15, 60, 300, 900, 3600, 14400, 86400],
                                type=int,
                                help='Standard deviation of this period (in seconds) to spread limit orders over when '
                                     'rebuilding position using '
                                     'increment mode. See documentation.'
                                ,default=None)
    auto_stop_opts.add_argument('-ri', '--relist_period', dest='relist_period',
                                choices=[15, 60, 300, 900, 3600, 14400, 86400],
                                type=int,
                                help='Period to relist open orders.'
                                , default=300)
    smart_sl_tp_opts = parser.add_argument_group('Smart Stoploss/Take Profit Options')

    smart_sl_tp_opts.add_argument('-ftp', '--fibtp', dest='tp_fib_enable', action='store_true', help='Enable fib retrace '
                                                                                                'levels for taking '
                                                                                                'profit.')
    smart_sl_tp_opts.add_argument('-fsl', '--fibsl', dest='tp_fib_sl_enable', action='store_true', help='Enable fib retrace '
                                                                                                        'levels for stoploss.')
    smart_sl_tp_opts.add_argument('-ssl', '--sarsl', dest='sar_sl', type=float, choices=[15, 60, 180, 300, 900, 3600, 14400, 86400],
                                  help='Sar stop loss -- close position when the sar on this period flips.')
    smart_sl_tp_opts.add_argument('--sfro', '--sarflip_reenter', action='store_true', help='Reopen position on flip '
                                                                                           'after exiting after a sar stop loss')
    smart_sl_tp_opts.add_argument('-fp', '--fib_period', dest='tp_fib_res', type=float, default=60, choices=[15, 60, 180,
                                                                                                           300, 900,
                                                                                                           900, 3600,
                                                                                                           14400, 86400],
                                help='The period to derive the standard deviation for the fib retrace.')


    auto_stop_opts.add_argument('-no', '--num_orders', dest='num_open_orders', default=4, type=int,
                                help='Number of open orders to reopen position in increments')
    auto_stop_opts.add_argument('-ps', '--position_step_size', dest='position_step_size', default=0.02, type=float,
                                help='Percentage to spread limit orders apart represented as  floating point number'
                                     'Default: 0.2.')
    auto_stop_opts.add_argument('-rl', '--relist', dest='relist_iterations', default=100, type=int,
                                help='Number of '
                                     'iterations '
                                     'before canceling '
                                     'and relisting '
                                     'open take profit '
                                     'and reopen orders.')
    auto_stop_opts.add_argument_group('Hedged Trading')
    auto_stop_opts.add_argument('-hm', '--hedge_mode', dest='hedge_mode', action='store_true',
                                help='Hedged trading mode.')
    auto_stop_opts.add_argument('-hr', '--hedge_ratio', dest='hedge_ratio', type=float, default=0.5,
                                help='Hedge ratio. Greater than 0: Delta is long. Less than 0 (negative): Delta is '
                                     'short.')
    auto_stop_opts.add_argument('-mc', '--max_collateral', dest='max_collateral', type=float, default=0.5,
                                help='Max amount of collateral to use. 1 == 100 percent, .5 == 50 percent. Note that '
                                     'this will actually use half of whatever you specify as a safeguard.')
    auto_stop_opts.add_argument('-pc', '--position_close_pct', type=float, default=1.0,
                                help='Float point percentage (.5 is 50 percent) of position to close at at time'
                                     'when taking profit.')
    auto_stop_opts.add_argument('-mf', '--mitigate_fees', dest='mitigate_fees', type=float, default=0.0,
                                help='Attempt to mitigate the fees incurred from stop loss orders by moving '
                                     'stop to this value, 0 being disabled and 1 being 100pct ')
    auto_stop_opts.add_argument('-ie', '--incremental_enter', dest='incremental_enter', action='store_true',
                                help='Enter positions with incremental orders instead of all at once.')
    #wallet_opts = parser.add_argument_group('Wallet & Subacct Options')
    #wallet_opts.add_argument('')
    mm_opts = parser.add_argument_group('Market Maker Options')
    mm_opts.add_argument('-mmm', '--maker_maker_mode', dest='mm_mode', action='store_true', help='Enable market maker mode.')
    mm_opts.add_argument('-mmlm', '--mm_long_market', dest='mm_long_market', type=str, default='BTC-PERP', help='Long Market to run mm on')
    mm_opts.add_argument('-mmsm', '--mm_short_market', dest='mm_short_market', type=str, help='Short market to run mm on')
    mm_opts.add_argument('-mms', '--mm_spread', dest='mm_spread', type=float, default=0.01, help='Min spread to operate')
    mm_opts.add_argument('-mmr', '--mm_ratio', dest='mm_ratio', type=float, default=0.5, help='Ratio of long and short')
    api_opts = parser.add_argument_group('API Commands')
    api_opts.description = (
        'Options for interacting with the exchange. For creating orders, the syntax is -b/-s <order type> <quantity> '
        '<price>')
    api_opts.add_argument('-p', '--portfolio', dest='show_portfolio', action='store_true', default=False,
                          help='Get current balances')
    api_opts.add_argument('-oc', '--chase', dest='limit_order_chase', nargs=2, help='Limit Order Chasing. '
                                                                                    'Keeps your limit '
                                                                                    'order at '
                                                                                    'the top of the books.'
                                                                                    'Specify order ID following'
                                                                                    'an integer representing the max '
                                                                                    'number of '
                                                                                    'order modifications '
                                                                                    'before giving up and '
                                                                                    'executing as market. ')
    api_opts.add_argument('-b', '--buy', dest='buy', type=str, nargs='+',
                          help='Execute a buy order: --buy <limit> <ETH-PERP> <0.5> 2898.89 , '
                               '[order types: limit, post, market]')
    api_opts.add_argument('--repeat', dest='repeat_action', type=int, default=1, help='Repeat this order this many times in '
                                                                                      'fast succession.')
    api_opts.add_argument('-s', '--sell', dest='sell', type=str, nargs='+',
                          help='Execute a sell order --sell <market> <BTC-USD> <0.1>')
    api_opts.add_argument('-lc', '--limit_chase', dest='limit_chase', type=int, default=0,
                          help=f'Chase this limit order this '
                               f'many times before .')
    api_opts.add_argument('-tsb', '--trailing_stop_buy', dest='trailing_stop_buy', type=str, nargs='+', help='API Trailing Stop \
        <market> <0.1> <.5>')

    api_opts.add_argument('-tss', '--trailing_stop_sell', dest='trailing_stop_sell', type=str, nargs='+', help='API Trailing Stop \
            <market> <0.1> <.5>')

    api_opts.add_argument('-cf', '--chase_failsafe', action='store_true', dest='chase_failsafe', help='Revert to market'
                                                                                                      'if order chase'
                                                                                                      'fails.')
    api_opts.add_argument('-o', '--orders', dest='open_orders', action='store_true', default=False,
                          help='Return list of '
                               'open orders.')
    api_opts.add_argument('-ca', '--cancel', dest='cancel', type=int, default=None, help='Cancel this order id.')
    api_opts.add_argument('-L', '--leverage', dest='set_leverage', type=int, choices=[1, 2, 3, 5, 10, 20],
                          help='Set account leverage via API.')

    mirror_opts = parser.add_argument_group('Trade Mirroring Options')
    mirror_opts.add_argument('--mirror', '-mi', dest='enable_mirror', action='store_true', help='Enable trade mirror.')
    mirror_opts.add_argument('-mst', '--master_account', dest='master_account', type=str, help='Mirror trades from this account')
    mirror_opts.add_argument('-cn', '--client_accounts', dest='client_accounts', type=str, nargs='+', help='Mirror to these subaccounts')
    mirror_opts.add_argument('-mm', '--mirror_markets', dest='mirror_markets', type=str, nargs='+', help='Mirr these markets')


    config_file_args = parser.add_argument_group('Configuration file arguments')
    config_file_args.add_argument('-wc', '--write_cfg', dest='write_cfg', type=str, default=None, help='Write currently supplied args to disc.')
    config_file_args.add_argument('-c', '--config', dest='config_fn', type=str, default='blackmirror.cfg',
                                  help='Write/read config to/from this file (stored in configs directory).')

    """if args.write_cfg:
                parsed_args, argv = parser.parse_known_args()
                print(parsed_args, argv)
                print(f'Writing configuration to {args.write_cfg} ... ')
                parser.write_config_file(parsed_args, [f'configs/{args.write_cfg}'], True)


            else:
                if args.config_fn:
                    import os
                    if os.path.exists(args.config_fn):
                        pass
                    else:
                        if os.path.exists(f'configs/{args.config_fn}'):
                            setattr(args, 'config_fn', f'configs/{args.config_fn}')
                    print(f'Opening and parsing {args.config_fn}')
                    with open(args.config_fn, 'r') as f:
                        config = configparser.SafeConfigParser()
                        config.read([args.config_fn])
                    for k, v in config.items("Defaults"):
                       setattr(args, k, v)

                    args = parser.parse_args(args)
            return args"""
    return parser.parse_args()

