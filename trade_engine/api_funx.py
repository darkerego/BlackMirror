if args.trailing_stop_buy:
    print('Not implemented.')
    return False

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
    print('Not implemented.')
    return False
    if len(args.buy) < 3:
        cp.red('[⛔] <market> <qty> <offset_percent>')
        market = args.trailing_stop_sell[0]
        qty = args.trailing_stop_sell[1]
        offset = args.trailing_stop_sell[2]