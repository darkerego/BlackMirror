import json

def load_config(config_path='conf.json'):
    print('Reading %s' % config_path)
    with open(config_path, 'r') as f:
        f = json.load(f)
        print('conf:', f)

        #
        key = f['conf']['key']
        secret = f['conf']['secret']
        subaccount = f['conf']['subaccount']
        anti_liq = f['conf']['anti_liq']
        # print(key, secret, subaccount, anti_liq)
        return key, secret, subaccount, anti_liq