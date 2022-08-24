import talib
import yfinance as yf
from datetime import date

today = date.today().strftime("%Y-%m-%d")
stockticker = '^BSESN'
dataframe = yf.download(stockticker, start='2021-03-31', end=today)

open = dataframe['Open']
high = dataframe['High']
low = dataframe['Low']
close = dataframe['Adj Close']

threeLineStrike = talib.CDL3LINESTRIKE(open,high,low,close)
threeBlackCrow = talib.CDL3BLACKCROWS(open,high,low,close)
eveningStar = talib.CDLEVENINGSTAR(open,high,low,close)
engulfing = talib.CDLENGULFING(open,high,low,close)
dragonflyDoji = talib.CDLDRAGONFLYDOJI(open,high,low,close)
gravestoneDoji = talib.CDLGRAVESTONEDOJI(open,high,low,close)
tasukigap = talib.CDLTASUKIGAP(open,high,low,close)
hammer = talib.CDLHAMMER(open,high,low,close)
darkCloudCover = talib.CDLDARKCLOUDCOVER(open,high,low,close)
piercingLine = talib.CDLPIERCING(open,high,low,close)


dataframe['3 Line Strike'] = threeLineStrike
dataframe['3 Black Crow'] = threeBlackCrow
dataframe['Evening Star'] = eveningStar
dataframe['Engulfing'] = engulfing
dataframe['Dragonfly Doji'] = dragonflyDoji
dataframe['Gravestone Doji'] = gravestoneDoji
dataframe['Tasuki Gap'] = tasukigap
dataframe['Hammer'] = hammer
dataframe['DarkCloudCover'] = darkCloudCover
dataframe['Piercing Line'] = piercingLine


topCandles = ["3 Line Strike","3 Black Crow","Evening Star","Engulfing","Dragonfly Doji","Gravestone Doji","Tasuki Gap","Hammer","DarkCloudCover","Piercing Line"]


for x in dataframe.index:
    for cd in topCandles:
        if dataframe.loc[x, cd] == -100:
            dataframe.loc[x, cd] = "Bearish"
        if dataframe.loc[x, cd] == 100:
            dataframe.loc[x, cd] = "Bullish"

dataframe.drop('Open', axis=1, inplace=True)
dataframe.drop('High', axis=1, inplace=True)
dataframe.drop('Low', axis=1, inplace=True)
dataframe.drop('Close', axis=1, inplace=True)
dataframe.drop('Adj Close', axis=1, inplace=True)
dataframe.drop('Volume', axis=1, inplace=True)

dataframe.to_csv("dataf.csv")