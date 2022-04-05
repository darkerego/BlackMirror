import argparse


def get_args():
    parser = argparse.ArgumentParser(usage='SUPPORT MY WORK! USE MY REFERRAL: https://ftx.com/referrals#a=darkerego')
    gen_opts = parser.add_argument_group('General Opts')
    gen_opts.description = 'General Options'
    gen_opts.add_argument('-m', '--monitor', dest='monitor', action='store_true', default=False,
                          help='Start the account monitor. See '
                               'current status.')
    gen_opts.add_argument('-sa', '--subaccount', dest='subaccount', default=None, type=str, help='Subaccount to connect'
                                                                                                 'to. None for main '
                                                                                                 'account.')
    gen_opts.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False, help='Verbose mode.')
    gen_opts.add_argument('-st', '--show_tickers', dest='show_tickers', action='store_true', default=False,
                          help='Do not show tickers.')
    arb_opts = parser.add_argument_group('OscillationArbitrage Engine Options')
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
                                                                                                  'reopen')

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
                          help='Execute a buy order: --buy <limit> <ETH-PERP> <0.5> 2898.89 ')
    api_opts.add_argument('-s', '--sell', dest='sell', type=str, nargs='+',
                          help='Execute a sell order --sell <market> <BTC-USD> <0.1>')
    api_opts.add_argument('-lc', '--limit_chase', dest='limit_chase', type=int, default=0, help=f'Chase this limit order this '
                                                                                          f'many times before .')
    api_opts.add_argument('-cf', '--chase_failsafe', action='store_true', dest='chase_failsafe', help='Revert to market'
                                                                                                      'if order chase'
                                                                                                      'fails.')
    api_opts.add_argument('-o', '--orders', dest='open_orders', action='store_true', default=False,
                          help='Return list of '
                               'open orders.')
    api_opts.add_argument('-c', '--cancel', dest='cancel', type=int, default=None, help='Cancel this order id.')
    api_opts.add_argument('-L', '--leverage', dest='set_leverage', type=int, choices=[1, 2, 3, 5, 10, 20, 50, 100, 101],
                          help='Set account leverage via API.')
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
    receiver_opts.add_argument('-uri', '--ws_uri', dest='ws_uri', type=str, default='ws://localhost:8000',
                               help='Websocket uri, wss://host:port')
    # receiver_opts.add_argument('-pf', '--portfolio_pct', dest='portfolio_pct', type=float,
    #                           help='Float representing % of'
    #                                'holdings to use on incoming'
    #                               'trade.')
    receiver_opts.add_argument('-re', '--reenter', dest='reenter', default=False, action='store_true',
                               help='Re enter position before it closes if price hits entry again.')
    receiver_opts.add_argument('-src', '--data_source', dest='data_source', type=str, choices=['binance'],
                               default='binance',
                               help='Exchange where the'
                                    'signals were aggravated.')
    receiver_opts.add_argument('-exc', '--exclude_markets', dest='exclude_markets', type=str, default=[],
                               help='Do not trade these markets',
                               nargs='*')

    auto_stop_opts = parser.add_argument_group('Auto Stop Loss Options')
    auto_stop_opts.add_argument('-a', '--auto', dest='auto_trader', action='store_true', help='Use AutoTrader')
    auto_stop_opts.add_argument('-mo', '--monitor_only', dest='monitor_only', action='store_true',
                                help='Do not trade. Monitor only.')
    auto_stop_opts.add_argument('--trade', '--really', dest='confirm',
                                action='store_true',
                                help='This is a FAILSAFE options to'
                                     'prevent accidental losses! Will not'
                                     'trade automatically without enabling.')

    auto_stop_opts.add_argument('-ds', '--disable_sl', dest='disable_stop_loss', action='store_true', default=False,
                                help='Do not use stop losses.')

    auto_stop_opts.add_argument('-sl', '--stop_loss', dest='stop_loss_pct', action='store', type=float, default=0.5,
                                help='Stop Loss Percentage represented as a floating point. -0.1 would be -10 percent PNL')
    auto_stop_opts.add_argument('-tp', '--take_profit', dest='take_profit_pct', type=float, default=5.0,
                                help='Percentage '
                                     'to '
                                     'take profit '
                                     'at, represented'
                                     'as sa floating point number.'
                                     '0.2 wouild be 20 pcercent')
    auto_stop_opts.add_argument('-tpo', '--trailing_stop_off', dest='no_use_trailing_stop', action='store_true',
                                help='Do not use Trailing Stops. Not sure why you would not to, but the option is here!')
    auto_stop_opts.add_argument('-ts', '--trailing_stop_offset', dest='ts_offset', type=float, default=0.1,
                                help='Trailing stop offset, represented as a floating point number, percentage of pnl.')
    auto_stop_opts.add_argument('-ot', '--order_type', choices=['limit', 'market'], default='market',
                                type=str, help='Take profit order type.')
    auto_stop_opts.add_argument('-ro', '--reopen', dest='reopen_method', choices=['increment', 'market', None],
                                default=None,
                                help='Method to use to reopen positions. Market just sends a limit or market order. Increment '
                                     'splits size into several smaller orders according to standard deviation')
    auto_stop_opts.add_argument('-cm', '--close_method', dest='close_method', choices=['increment', 'market', False],
                                default='market', help='Method to use to close positions. Market just sends a limit '
                                                       'or market order. Increment '
                                                       'splits size into several smaller orders according to standard deviation')
    auto_stop_opts.add_argument('-ip', '--increment_period', dest='increment_period',
                                choices=[15, 60, 300, 900, 3600, 14400, 86400],
                                type=int,
                                help='Standard deviation of this period (in seconds) to spread limit orders over when '
                                     'rebuilding position using '
                                     'increment mode. See documentation.'
                                ,default=None)
    #auto_stop_opts.add_argument('-')
    auto_stop_opts.add_argument('-no', '--num_orders', dest='num_open_orders', default=4, type=int,
                                help='Number of open orders to reopen position in increments')
    auto_stop_opts.add_argument('-ps', '--position_step_size', dest='position_step_size', default=0.2, type=float,
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
                                help='Max amount of collateral to use. 1 == 100 percent, .5 == 50 percent.')
    auto_stop_opts.add_argument('-pc', '--position_close_pct', type=float, default=1.0,
                                help='Float point percentage (.5 is 50%) of position to close at at time'
                                     'when taking profit.')
    #wallet_opts = parser.add_argument_group('Wallet & Subacct Options')
    #wallet_opts.add_argument('')

    return parser.parse_args()
