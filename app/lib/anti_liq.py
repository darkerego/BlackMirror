from trade_engine.api_wrapper import FtxApi
from utils import colorprint
cp = colorprint.NewColorPrint()
import time


class AntiLiq:

    def __init__(self, api: FtxApi, percentage: float = 0.1, subaccount = None, init=False):
        self.api = api
        self.percentage = percentage
        self.subaccount = subaccount
        self.init = init

    def transfer(self):
        balances = self.api.balances()
        for x in balances:
            if x.get('coin') == 'USD':
                avail = x.get('availableWithoutBorrow')
                if avail <= 0:
                    if self.init:
                        cp.yellow(f'[!] Please deposit some USD in this account and try again.')
                    return False
                else:
                    sas = self.api.get_subaccounts()
                    if self.init:
                        print(sas)
                        time.sleep(5)
                    q = avail * self.percentage
                    cp.yellow(f'[!] Transferring {q} USD to LIQUIDITY subaccount. This will be used as '
                              f'EMERGENCY funds to prevent liquidation. Do not trade with it!')
                    ret = self.api.transfer('USD', q, self.subaccount, 'LIQUIDITY')
        if self.init:
            print(balances[0])
        return ret

