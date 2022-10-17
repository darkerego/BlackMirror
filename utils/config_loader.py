import json
import os

if not os.path.exists('conf.json'):
    print('[!] Please copy `conf.json.example` to `conf.json` and add your api keys. Then run again!')
    exit(1)


def load_config(config_path='conf.json'):
    print('Reading %s' % config_path)
    with open(config_path, 'r') as f:
        f = json.load(f)
        key = f['conf']['key']
        secret = f['conf']['secret']
        subaccount = f['conf']['subaccount']
        #long_new_listings = f['conf']['long_new_listings']
        return key, secret, subaccount, 0
