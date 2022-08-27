# FTXTool or "BlackMirror" version 2

### NOTICE - this readme is out of date. See README.md in the root directory of this repository.

<pre>
  ____ ______ _   _     ___  __ __ ______   ___      ______ ____   ___  ____    ____ ____ 
 ||    | || | \ //    // \ || || | || |  // \     | || | || \ // \ || \  ||    || \
 ||==    ||    )X(     ||=|| || ||   ||   ((   ))      ||   ||_// ||=|| ||  )) ||==  ||_//
 ||      ||   // \    || || \_//   ||    \_//       ||   || \ || || ||_//  ||___ || \


usage: main.py [-h] [-m] [-sa SUBACCOUNT] [-v] [-st] [-O] [-ls LONG_SYMBOLS [LONG_SYMBOLS ...]] [-ss SHORT_SYMBOLS [SHORT_SYMBOLS ...]] [-mp MIN_SPREAD] [-p] [-b BUY [BUY ...]] [-s SELL [SELL ...]]
               [-o] [-c CANCEL] [-S] [-str {sar}] [-sy SYMBOL] [-sym SYMBOL_MONITOR] [-xs CONTRACT_SIZE] [-a] [-mo] [-ds] [-sl STOP_LOSS_PCT] [-tp TAKE_PROFIT_PCT] [-tpo] [-ts TS_OFFSET]
               [-ot {limit,market}] [-ro {increment,market,None}] [-cm {increment,market,False}] [-ip {15,60,300,900,3600,14400,86400}] [-no NUM_OPEN_ORDERS] [-ps POSITION_STEP_SIZE]

optional arguments:
  -h, --help            show this help message and exit

General Opts:
  General Options

  -m, --monitor         Start the account monitor. See current status.
  -sa SUBACCOUNT, --subaccount SUBACCOUNT
                        Subaccount to connectto. None for main account.
  -v, --verbose         Verbose mode.
  -st, --show_tickers   Do not show tickers.

OscillationArbitrage Engine Options:
  -O, --osc_arb         Run experimental balance arbitrage engine.
  -ls LONG_SYMBOLS [LONG_SYMBOLS ...], --long_symbols LONG_SYMBOLS [LONG_SYMBOLS ...]
                        List of instruments to long.
  -ss SHORT_SYMBOLS [SHORT_SYMBOLS ...], --short_symbols SHORT_SYMBOLS [SHORT_SYMBOLS ...]
                        List of symbols to short
  -mp MIN_SPREAD, --min_spread MIN_SPREAD
                        Minimum arbitrage spread to target.

API Commands:
  Options for interacting with the exchange. For creating orders, the syntax is -b/-s <order type> <quantity> <price>

  -p, --portfolio       Get current balances
  -b BUY [BUY ...], --buy BUY [BUY ...]
                        Execute a buy order: --buy <limit> <ETH-PERP> <0.5> 2898.89
  -s SELL [SELL ...], --sell SELL [SELL ...]
                        Execute a sell order --sell <market> <BTC-USD> <0.1>
  -o, --orders          Return list of open orders.
  -c CANCEL, --cancel CANCEL
                        Cancel this order id.

Trade Strategy Options:
  -S, --strategy        Use the TA based trade strategy engine.
  -str {sar}, --strat {sar}
                        Trade Strategy to use
  -sy SYMBOL, --symbol SYMBOL
                        FTX instrument to trade.
  -sym SYMBOL_MONITOR, --symbol_monitor SYMBOL_MONITOR
                        Binance symbol to watch.
  -xs CONTRACT_SIZE, --contract_size CONTRACT_SIZE

Auto Stop Loss Options:
  -a, --auto            Use AutoTrader
  -mo, --monitor_only   Do not trade. Monitor only.
  -ds, --disable_sl     Do not use stop losses.
  -sl STOP_LOSS_PCT, --stop_loss STOP_LOSS_PCT
                        Stop Loss Percentage represented as a floating point. -0.1 would be -10 percent PNL
  -tp TAKE_PROFIT_PCT, --take_profit TAKE_PROFIT_PCT
                        Percentage to take profit at, representedas sa floating point number.0.2 wouild be 20 pcercent
  -tpo, --trailing_stop_on
                        Use Trailing Stops. Not sure why you would not to, but the option is here!
  -ts TS_OFFSET, --trailing_stop_offset TS_OFFSET
                        Trailing stop offset, represented as a floating point number, percentage of pnl.
  -ot {limit,market}, --order_type {limit,market}
                        Take profit order type.
  -ro {increment,market,None}, --reopen {increment,market,None}
                        Method to use to reopen positions. Market just sends a limit or market order. Increment splits size into several smaller orders according to standard deviation
  -cm {increment,market,False}, --close_method {increment,market,False}
                        Method to use to close positions. Market just sends a limit or market order. Increment splits size into several smaller orders according to standard deviation
  -ip {15,60,300,900,3600,14400,86400}, --increment_period {15,60,300,900,3600,14400,86400}
                        Period (in seconds) to spread limit order over when rebuilding position using increment mode
  -no NUM_OPEN_ORDERS, --num_orders NUM_OPEN_ORDERS
                        Number of open orders to reopen position in increments
  -ps POSITION_STEP_SIZE, --position_step_size POSITION_STEP_SIZE
                        Percentage to spread limit orders apart represented as floating point number.

</pre>

### General Options

`-m, --monitor` - Start the account monitor. This is always the first function that is called. Although the -m flag 
does not need to be specified anymore, I tend to use it out of habbit. This creates a websocket and restful API 
connetion and then begins monitoring the connection for quality. If there is lag or other issues, a force restart 
is initiated. 

`-sa, --subaccount` - Simply the name of the subaccount to connect to. Ignore if usng the main account. This can be 
overwritten in the config file. 

`-v, --verbose` - Increase verbosity of output

`-st, --show_tickers` - Possibly not quite fully implmented function which shows trending markets on ftx. 




### OscillationArbitrage 

This section can be ignored for now, as it is nowhere near complete. 


### API Commands:

`-p, --portfolio` - Show currently held assets on FTX. Uses a pandas dataframe so it is pretty and readable. 

`-b, --buy` - Buy command. Syntax is `--buy <order type> <market> <quantity> <optional price>`

`-s, --sell` - Sell command. Same syntax. Note if using market orders, there is no need to ever specifiy a price.

`-c, --cancel` - Cancel this order (by order id) --cancel 124435345




### Trade Strategy Options:

Introducing a new feature - a technical analysis framework, built to be modular such that we can author our 
own indicators and have a plug and play system to use with the trade engine. Currently, I have only written one 
indicator, which is multi timeframe slightly modified version of the parabolic sar indicator, which is included 
in this codebase. The idea is to start the program with no current open positions. The TA engine will enter trades 
when opportune, and the trade engine will take over from there. So, if you are going to use the experimental 
sar algo, then you may want to run it with `-ds` and without `--reopen`, because we do not want to reopen the 
position unless we are getting a valid trade signal. Rather we want positions to be opened by the TA engine, 
and then we want the trade engine to take profit when the `-tp` specified level is achieved. A trailing stop 
is good to use in this situation. It is enabled by default, so you don't need to worry about that. Do keep in 
mind that this is ALPHA software and your mileage may vary.

Example command to start up the SAR algo:
<pre>
$ ./main.py -a -tp 1 -ts .25 -sl .5 -sy ETH-PERP -sym ETHUSDT -xs .1
</pre>

Breakdown of command:

Start autotrader. Set take profit to 1%. Set trailing stop offset to .25% , set stop loss to .5% , trade on 
ftx with ETH-PERP futures, but monitor the binance ETHUSDT market to generate those signals. When entering a 
trade, enter with a size of .1 etherum. 


### Auto Stop Loss Options:

Autotrader is the "backbone" of the program. This is my signature feature, and the one I am most proud of 
and find the most useful. Personally I think it is one the coolest things I have written. It assumes multiple functions, 
from guilded semi-automatic  trading (doing thing like taking profit and setting stops). 
It also has the ability to reopen a position after taking profit. This can be done either incrementally, or all at once. 
Most of these options are the same as in the last release, with the notable exception is `--close_method`. 
This is a lot like `-reopen`. Essentially you can choose to take profit in increments, potentially maximizing your gains.
It is the same idea as "pyramiding" your orders. But now, it happens automatically. 

`-a, --auto`            Enable auto trader

`  -mo, --monitor_only`   Do not trade. Monitor only. Sort of like a paper trading mode.

`  -ds, --disable_sl`     Do not use stop losses.

`  -sl` STOP_LOSS_PCT --stop_loss STOP_LOSS_PCT
                        Stop Loss Percentage represented as a floating point. -0.1 would be -10 percent PNL
`  -tp` TAKE_PROFIT_PCT --take_profit TAKE_PROFIT_PCT

                        Percentage to take profit at, representedas sa floating point number.0.2 wouild be 20 pcercent
 ` -tpo`, --trailing_stop_off
                       Do not Use Trailing Stops. Not sure why you would not to, but the option is here!
  `-ts` TS_OFFSET, --trailing_stop_offset TS_OFFSET

                        Trailing stop offset, represented as a floating point number, percentage of pnl.
  `-ot` {limit,market}, --order_type {limit,market}
                        Take profit order type.

  `-ro` {increment,market,None}, --reopen {increment,market,limit, None}
                        Method to use to reopen positions. Market just sends a limit or market order. Increment splits size into several smaller orders according to standard deviation
  `-cm. --close_method`  {increment,market,False}, --close_method {increment,market,False}

                        Method to use to close positions. Market just sends a limit or market order. Increment splits size into several smaller orders according to standard deviation
  `-ip, --increment_period` {15,60,300,900,3600,14400,86400}, --increment_period {15,60,300,900,3600,14400,86400}
                        Period (in seconds) to spread limit order over when rebuilding position using increment mode

  `-no` NUM_OPEN_ORDERS, --num_orders NUM_OPEN_ORDERS
                        Number of open orders to reopen position in increments

  `-ps` POSITION_STEP_SIZE, --position_step_size POSITION_STEP_SIZE
                        Percentage to spread limit orders apart represented as floating point number.



