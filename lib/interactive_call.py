
"""
Example usage of interactive_call:
1) assign the InteractiveParser variables
2) Treat this like its an argparse object
3) Pass it to interactive_call
"""
import threading

from autotrader import Bot
from utils import config_loader
from utils.colorprint import NewColorPrint


class InteractiveParser:
    # general opts
    monitor = False  # bool
    subaccount = None  # str
    verbose = False  # bool
    show_tickers = False  # bool
    # strategy opts
    use_strategy = False  # bool
    strategy = 'SAR'  # choices - str - SAR is only current strategy
    symbol = None  # ftx symbol - string 'BTC-PERP'
    symbol_monitor = None  # binance pair - string - 'BTCUSDT
    contract_size = 0.0  # for TA trading, how much (ie BTC) should we buy (like .01)
    # balance arb
    balance_arbitrage = False
    order_type = 'market'
    reenter = False
    data_source = 'binance'
    exclude_markets = None
    enable_ws = False
    ws_uri = False
    long_symbols = []
    short_symbols = []
    min_spread = 0.0
    # auto trader opts
    auto_trader = False  # bool
    monitor_only = True  # bool
    confirm = False  # bool
    disable_stop_loss = False  # bool
    stop_loss_pct = 0.5  # float
    take_profit_pct = 3.0  # float
    use_trailing_stop = True  # bool
    ts_offset = 0.005  # float
    reopen_method = 'market'  # choices, market, increment, None
    close_method = 'market'  # choices, market, increment
    increment_period = 300  # choices, [15, 60, 300, 900, 3600, 14400, 86400]
    num_open_orders = 4  # int
    position_step_size = 0.02  # float


def interactive_call(_args):
    """
    Interactively start the monitor and whatever else
    :param args:
    :return:
    """
    global cp
    _args_ = _args
    key, secret, subaccount = config_loader.load_config('conf.json')
    bot = Bot()
    cp = NewColorPrint()
    t = threading.Thread(target=bot.monitor, args=(key, secret, subaccount, _args_))
    t.start()
