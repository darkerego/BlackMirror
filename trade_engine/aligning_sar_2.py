import sys
import threading
import time
from datetime import datetime
import numpy as np
import talib
import argparse
from utils import colorprint
from binance.client import Client

cp = colorprint.NewColorPrint()


class TheSARsAreAllAligning:
    """
    Sar spike/dip detector - constantly check the sar on multi time frames. If they all align,
    send a trade signal.
    """

    def __init__(self, debug=False):
        self.debug = debug
        self.api = Client()
        self.has_signal = {}
        self.signal_at = {}

    def future_ticker(self, instrument):
        for x in self.api.futures_ticker():
            if x['symbol'] == instrument:
                return x['lastPrice']

    def get_klines(self, trading_pair, interval):
        return self.api.get_klines(symbol=trading_pair, interval=interval)

    def aggravate(self, symbol, interval):
        klines = self.api.get_klines(symbol=symbol, interval=interval)
        open_time = [int(entry[0]) for entry in klines]
        low = [float(entry[1]) for entry in klines]
        mid = [float(entry[2]) for entry in klines]
        high = [float(entry[3]) for entry in klines]
        close = [float(entry[4]) for entry in klines]
        close_array = np.asarray(close)
        high_array = np.asarray(high)
        low_array = np.asarray(low)
        new_time = [datetime.fromtimestamp(time / 1000) for time in open_time]
        return open_time, low, mid, high, close, close_array, high_array, low_array, new_time

    def generate_sar(self, high_array, low_array, acceleration=0.02, maximum=0.2):
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
        ticker = float(self.future_ticker(symbol))
        # print(sar)
        sar = sar[-3]
        # print(sar)
        sar = float(sar)
        if sar < ticker:
            # under candle, is long
            return 1, ticker, sar
        if sar > ticker:
            # above candle, is short
            return -1, ticker, sar

    def get_sar(self, symbol, period=None):
        """
        Grab kline data for multiple timeframes #TODO: aiohttp
        :param symbol:
        :param period:
        :return:
        """

        open_time, low, mid, high, close, close_array, high_array, low_array, new_time = self.aggravate(symbol=symbol,
                                                                                                        interval=period)
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
        # p_list = ['5m', '15m', '30m', '1h', '4h']
        # p_list = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h']
        p_list = ['1m', '5m', '15m', '30m']
        count = len(p_list)
        sars_ = {}

        for i in p_list:
            if sars_.get(i) is None:
                s, t, sr = self.get_sar(symbol=instrument, period=i)
                sars_.update({i: sr})
                if s == 1:
                    long += 1
                elif s == -1:
                    short += 1

            current_ticker = self.future_ticker(instrument=instrument)
            print(current_ticker)
            if float(sars_.get(i)) < float(current_ticker) and long == count:
                sars_.update({i: None})
            if float(sars_.get(i)) > float(current_ticker) and short == count:
                sars_.update({i: None})

            if long == count:
                if not self.has_signal['instrument']:
                    self.signal_at[instrument] = t
                cp.green(f'[▲] {instrument} SAR LONG @ ${self.signal_at[instrument]}! ')
                self.has_signal[instrument] = True
                return 'long'
            elif long == short:
                self.has_signal[instrument] = False
                self.signal_at[instrument] = 0
                if self.debug:
                    cp.purple(f'[≜] {instrument} SAR Neutral: {long}/{short}')
                return False
            elif count > long > 0 and long > short:
                self.has_signal[instrument] = False
                self.signal_at[instrument] = 0
                if self.debug:
                    cp.yellow(f'[▲] {instrument} SAR partial long: {long}/{count}')
                return False
            elif short == count:
                if not self.has_signal['instrument']:
                    self.signal_at[instrument] = t
                self.signal_at[instrument] = t
                cp.red(f'[▼] {instrument} SAR SHORT @ ${self.signal_at[instrument]}!')
                self.has_signal[instrument] = True
                return 'short'
            elif count > short > 0 and short > long:
                self.has_signal[instrument] = False
                self.signal_at[instrument] = 0
                if self.debug:
                    cp.white(f'[▼] {instrument} SAR partial short: {short}/{count}')
                return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--symbol', dest='symbol', type=str, default='BTC-PERP', help='Future Market to Query')
    parser.add_argument('-l', '--list', dest='symbol_list', type=str, default=None, help='Iterate over list'
                                                                                         'of symbols.')
    args = parser.parse_args()
    print(args)
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
            except Exception as err:
                print(err)


if __name__ == '__main__':
    main()
    #sar_ = TheSARsAreAllAligning(debug=True)
    #sar_.sar_scalper(instrument='BTCUSDT')