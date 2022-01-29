import json

def load_config(config_path='conf.json'):
    with open(config_path, 'r') as f:
        f = json.load(f)
        print('conf:', f)

        #
        key = f['conf']['key']
        secret = f['conf']['secret']
        subaccount = f['conf']['subaccount']
        print(key, secret, subaccount)
        return key, secret, subaccount