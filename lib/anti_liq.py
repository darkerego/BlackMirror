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
                                      f'EMERGENCY funds to prevent liquidation. Do not fucking trade with it!')
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