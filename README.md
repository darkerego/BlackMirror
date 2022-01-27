# SemiAuto

## Support my work:
And use my [FTX referal code](https://ftx.com/referrals#a=darkerego)

# Rational For Existance

I decided to open source this. It is a very featured tool for the FTX trading platform that I wrote to semi automate the manual trade process. It is part of a larger project, a fully automated system in development. I wrote this to stop forgetting to set stop losses and missing oppurtunities to take profit in my sleep. It can also take profit in increments, pyramiding up and down the books as you take profit, and then re-enter, essentially just swing trading 
the volatility. It is really cool to watch. I will post some asciinema soon. The documentation should be decent. To get started, run:

```
./autotrade.py -ma
```

# Usage:

```
usage: autotrader.py [-h] [-m] [-sa SUBACCOUNT] [-v] [-st] [-O] [-ls LONG_SYMBOLS [LONG_SYMBOLS ...]] [-ss SHORT_SYMBOLS [SHORT_SYMBOLS ...]] [-mp MIN_SPREAD] [-p] [-b BUY [BUY ...]] [-s SELL [SELL ...]]
                     [-o] [-c CANCEL] [-S] [-str {sar}] [-sy SYMBOL] [-sym SYMBOL_MONITOR] [-xs CONTRACT_SIZE] [-ws] [-uri WS_URI] [-re] [-src {binance}] [-exc [EXCLUDE_MARKETS [EXCLUDE_MARKETS ...]]]
                     [-a] [-mo] [--really] [-ds] [-sl STOP_LOSS_PCT] [-tp TAKE_PROFIT_PCT] [-tpo] [-ts TS_OFFSET] [-ot {limit,market}] [-ro {increment,market,None}] [-cm {increment,market,False}]
                     [-ip {15,60,300,900,3600,14400,86400}] [-no NUM_OPEN_ORDERS] [-ps POSITION_STEP_SIZE]

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

Websocket Trade Signal Options:
  -ws, --ws_signals     Enable websocket client for signals
  -uri WS_URI, --ws_uri WS_URI
                        Websocket uri, wss://host:port
  -re, --reenter        Re enter position before it closes if price hits entry again.
  -src {binance}, --data_source {binance}
                        Exchange where thesignals were aggravated.
  -exc [EXCLUDE_MARKETS [EXCLUDE_MARKETS ...]], --exclude_markets [EXCLUDE_MARKETS [EXCLUDE_MARKETS ...]]
                        Do not trade these markets

Auto Stop Loss Options:
  -a, --auto            Use AutoTrader
  -mo, --monitor_only   Do not trade. Monitor only.
  --really, --i_accept_the_tos, --confirm
                        Confirm that you really want to have the bot manage your positions.This is a FAILSAFE options toprevent accidental losses! Will nottrade without this enabled!
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

```
