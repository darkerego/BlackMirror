import sys
import threading

import numpy as np
# import grequests
import requests
import talib
import argparse
from utils import colorprint
cp = colorprint.NewColorPrint()

import ssl
import trio
from python_socks.async_.trio import Proxy
#from conf import proxyrack
proxy = Proxy.from_url('socks5://user:password@127.0.0.1:1080')

# `connect` returns trio socket
# so we can pass it to trio.SocketStrea
async def sockify():
    sock = proxy.connect(dest_host='check-host.net', dest_port=443)

    stream = trio.SocketStream(sock)

    stream = trio.SSLStream(
        stream, ssl.create_default_context(),
        server_hostname='check-host.net'
    )
    stream.do_handshake()

    request = (
        b'GET /ip HTTP/1.1\r\n'
        b'Host: check-host.net\r\n'
        b'Connection: close\r\n\r\n'
    )

    await stream.send_all(request)
    response = await stream.receive_some(4096)
    return response

class TheSARsAreAllAligning:
    """
    Sar spike/dip detector - constantly check the sar on multi time frames. If they all align,
    send a trade signal.
    """

    def __init__(self, debug=False):
        self.debug = debug

    def spot_ticker(self, market):
        """
        Retrieve spot market ticker data
        :param market:
        :return: last price
        """
        ret = requests.get(f'https://ftx.com/api/markets/{market}').json()
        print(ret)
        return ret['result']['price']

    def future_ticker(self, market):
        """
        Futures market
        :param market:
        :return: mark price
        """

        ret = requests.get(f'https://ftx.com/api/futures/{market}').json()
        # print(ret)
        return ret['result']['mark']

    def generate_sar(self, high_array, low_array, acceleration=0.05, maximum=0.2):
        """
        Use talib's parabolic sar function to return current psar value
        :param high_array: as array
        :param low_array:
        :param acceleration: acceleration factor
        :param maximum: acc max
        :return:
        """
        sar = talib.SAR(high_array, low_array, acceleration=acceleration, maximum=maximum)
        return sar

    def calc_sar(self, sar, symbol):
        """
        Determine if sar reads under or above the candle
        :param sar:
        :param symbol:
        :return: tuple
        """
        ticker = (self.future_ticker(symbol))
        sar = sar[-3]
        if sar < ticker:
            # under candle, is long
            return 1, ticker, sar
        if sar > ticker:
            # above candle, is short
            return -1, ticker, sar

    def get_sar(self, symbol, period=60):
        """
        Grab kline data for multiple timeframes #TODO: aiohttp
        :param symbol:
        :param period:
        :param period_list:
        :param sar_:
        :return:
        """

        """
        Periods in number of seconds:
        15s, 1m,  5m,  15m,  1h,   4h,   1d
        15, 60, 300, 900, 3600, 14400, 86400
        0.01736111111111111 %, 0.06944444444444445 %  0.3472222222222222 % 1.0416666666666665% 4.166666666666666% 
        16.666666666666664 % 77%
        """
        close_array = []
        high_array = []
        low_array = []
        #print(f'Getting {period} {symbol}')
        _candles = requests.get(f'https://ftx.com/api/markets/{symbol}/candles?resolution={period}')
        for c in _candles.json()['result']:
            close_array.append(c['close'])
            high_array.append(c['high'])
            low_array.append(c['low'])
        high_array = np.asarray(high_array)
        low_array = np.asarray(low_array)
        sar = self.generate_sar(high_array, low_array)
        return self.calc_sar(sar, symbol)

    def sar_scalper(self, instrument):
        """
        main logic
        :param instrument:
        :return:
        """
        short = 0
        long = 0
        sars = []
        p_list = [60, 300, 900, 3600]
        count = len(p_list)
        for i in p_list:
            s, t, sr = self.get_sar(symbol=instrument, period=i)
            # print(sr)
            sars.append(sr)
            savg = sum(sars)/len(sars)
            if s == 1:
                long += 1
            elif s == -1:
                short += 1
        if long == count:
            cp.green(f'[▲] {instrument} SAR LONG @ ${t}! ')
            return 'long'
        elif long == short:
            if self.debug:
                cp.purple(f'[≜] {instrument} SAR Neutral: {long}/{short}')
            return False
        elif count > long > 0 and long > short:
            if self.debug:
                cp.yellow(f'[▲] {instrument} SAR partial long: {long}/{count}')
            return False
        elif short == count:
            cp.red(f'[▼] {instrument} SAR SHORT @ ${t}!')
            return 'short'
        elif count > short > 0 and short > long:
            if self.debug:
                cp.white(f'[▼] {instrument} SAR partial short: {short}/{count}')
            return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--symbol', dest='symbol', type=str, default='BTC-PERP', help='Future Market to Query')
    parser.add_argument('-l', '--list', dest='symbol_list', type=str, default=None, help='Iterate over list'
                                                                                                  'of symbols.')
    args = parser.parse_args()
    while True:
        if args.symbol_list:
            sar_ = TheSARsAreAllAligning(debug=True)
            with open(args.symbol_list, 'r') as f:
                f = f.readlines()
            try:
                for _ in f:
                    _ = _.strip('\r\n')
                    t = threading.Thread(target=sar_.sar_scalper, args=(_,))
                    t.run()
            except KeyboardInterrupt:
                print('\nCaught Signal, Exiting with Grace ...')
                sys.exit(0)
        else:
            try:
                sar_ = TheSARsAreAllAligning(debug=True)
                sar_.sar_scalper(instrument=args.symbol)
            except KeyboardInterrupt:
                print('\nCaught Signal, Exiting with Grace ...')
                sys.exit(0)


if __name__ == '__main__':
    main()
