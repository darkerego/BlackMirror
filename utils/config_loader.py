import json

def load_config(config_path='conf.json'):
    with open(config_path, 'r') as f:

        f = json.load(f)
        print(f)
        key = f[0]['key']
        secret = f[0]['secret']
        subaccount = f[0]['subaccount']
        return key, secret, subaccount