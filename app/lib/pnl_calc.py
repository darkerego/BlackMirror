def pnl_calc(qty, sell, buy, fee=0.00019):
    """
    Profit and Loss Calculator - assume paying
     two market fees (one for take profit, one for re-opening). This way we can
     set tp to 0 and run as market maker and make something with limit orders.
    """
    if fee <= 0:
        pnl = float(qty * (sell - buy) * (1 - fee))
    else:
        pnl = float(qty * (sell - buy) * (1 - (fee * 2)))
    if pnl is not None:  # pythonic double negative nonsense
        return pnl
    return 0.0