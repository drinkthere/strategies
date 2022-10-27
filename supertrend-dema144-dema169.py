# import libs
import sys
import logging
import os
import requests
import time
import json
import telegram
import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
# plt.style.use('fivethirtyeight')

logging.basicConfig(filename='logs/alarm.log', level=logging.INFO)

# 加载env


def import_env():
    for line in open('.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            key, value = var[0].strip(), var[1].strip()
            os.environ[key] = value


import_env()

# configuration
klinesCount = 1000
atrPeriod = 34
atrMultiplier = 3


# 初始化tgbot替换为实际的 token
tgToken = os.environ.get('TG_TOKEN')
tgChatId = os.environ.get('TG_CHAT_ID')
bot = telegram.Bot(token=tgToken)


def fetch_klines_from_binance(count):
    # now = int(time.time())
    # # nowArray = time.strptime('2022-10-25 23:00:00', "%Y-%m-%d %H:%M:%S")
    # # now = int(time.mktime(nowArray))

    # # 获取最新K线的时间戳
    # prevTimeArr = time.localtime(now - 3600)
    # datetime = time.strftime("%Y-%m-%d %H:00:00", prevTimeArr)
    # endTimeArr = time.strptime(datetime, "%Y-%m-%d %H:%M:%S")
    # endTime = int(time.mktime(endTimeArr) * 1000)

    # # 获取最早K线的时间戳
    # timeArr = time.localtime(now - 3600 * count)
    # datetime = time.strftime("%Y-%m-%d %H:00:00", timeArr)
    # startTimeArr = time.strptime(datetime, "%Y-%m-%d %H:%M:%S")
    # startTime = int(time.mktime(startTimeArr) * 1000)
    # print(startTime, endTime)
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36"
    # }
    # url = 'https://fapi.binance.com/fapi/v1/klines'
    # params = {
    #     "symbol": symbol,
    #     "interval": interval,
    #     "startTime": startTime,
    #     "endTime": endTime
    # }

    # using limit
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36"
    }
    url = 'https://fapi.binance.com/fapi/v1/klines'
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 1000
    }
    return requests.get(url=url, params=params, headers=headers).text


def init_data_frame(klines):
    df = pd.DataFrame(klines, columns=[
        'openTime', 'open', 'high', 'low',
        'close', 'volume', 'closeTime', 'amount',
        'txCount', 'takerVolume', 'takerAmount', 'foo'
    ])

    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['hour'] = pd.to_datetime(
        df['openTime'], utc=True, unit='ms').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:00')
    df = df.set_index('hour')

    return df


def strategy(data):
    # cal & store dema144 and dema169 into the dataset
    data['dema144'] = dema(data, 144, 'close')
    data['dema169'] = dema(data, 169, 'close')

    # # print to debug
    # for x in range(len(data['dema144'])):
    #     print(data.index.values[x], data['open'].values[x], data['close'].values[x],
    #           data['high'].values[x], data['low'].values[x], data['dema144'].values[x])

    # # graph to debug
    # column_list = ['dema144', 'dema169']
    # data[column_list].plot(figsize=(20, 10))
    # plt.title('close price for btcbusd')
    # plt.ylabel('USD Price($)')
    # plt.xlabel('Date')
    # plt.xticks(rotation=90)
    # plt.show()
    # exit()

    # calculate atr
    ranges = [data['high'] - data['low'], data['high'] -
              data['close'].shift(1), data['low'] - data['close'].shift(1)]
    data['tr'] = pd.DataFrame(ranges).T.abs().max(axis=1)
    data['atr'] = data['tr'].ewm(span=atrPeriod, adjust=False).mean()

    # calculate up and down
    data['hl2'] = (data['high'] + data['low']) / 2
    data['up'] = data['hl2'] - atrMultiplier * data['atr']
    data['down'] = data['hl2'] + atrMultiplier * data['atr']

    # calulate supertrend
    data['trendUp'] = 0.0
    data['trendDown'] = 0.0
    data['trend'] = 1
    data['buy'] = np.nan
    data['sell'] = np.nan
    data = data.fillna(0)

    for i in range(len(data)):
        if (i < 1):
            data['trendUp'].values[i] = data['up'].values[i]
            data['trendDown'].values[i] = data['down'].values[i]
            data['trend'].values[i] = 1
        else:
            curr, prev = i, i - 1
            if (data['close'].values[prev] > data['trendUp'].values[prev]):
                data['trendUp'].values[curr] = max(
                    data['up'].values[curr], data['trendUp'].values[prev])
            else:
                data['trendUp'].values[curr] = data['up'].values[curr]

            if (data['close'].values[prev] < data['trendDown'].values[prev]):
                data['trendDown'].values[curr] = min(
                    data['down'].values[curr], data['trendDown'].values[prev])
            else:
                data['trendDown'].values[curr] = data['down'].values[curr]

            if (data['close'].values[curr] > data['trendDown'].values[prev] and data['trend'].values[prev] == -1):
                data['trend'].values[curr] = 1
            else:
                if (data['close'].values[curr] < data['trendUp'].values[prev] and data['trend'].values[prev] == 1):
                    data['trend'].values[curr] = -1
                else:
                    data['trend'].values[curr] = data['trend'].values[prev]

    if (data['trend'].values[-1] == 1 and data['trend'].values[-2] == -1):
        msg = symbol + ' 多|平空 ' + str(data['close'].values[-1])
        bot.send_message(tgChatId, msg)
    elif (data['trend'].values[-1] == -1 and data['trend'].values[-2] == 1):
        msg = symbol + ' 空|平多 ' + str(data['close'].values[-1])
        bot.send_message(tgChatId, msg)
    else:
        msg = symbol + ' 无需操作 ' + str(data['close'].values[-1])
        logging.info(msg)

    # for i in range(1, len(data)):
    #     curr, prev = i, i - 1
    #     if (data['trend'].values[curr] == 1 and data['trend'].values[prev] == -1):
    #         if (data['close'].values[curr] > data['dema144'].values[curr] and data['close'].values[curr] > data['dema169'].values[curr]):
    #             # 创建买订单
    #             data['buy'].values[curr] = data['close'].values[curr]

    #     if (data['trend'].values[curr] == -1 and data['trend'].values[prev] == 1):
    #         if (data['close'].values[curr] < data['dema144'].values[curr] and data['close'].values[curr] < data['dema169'].values[curr]):
    #             # 创建卖订单
    #             data['sell'].values[curr] = data['close'].values[curr]

    # for x in range(len(data['buy'])):
    #     if (data['buy'].values[x] > 0):
    #         print(data['openTime'].values[x])

    # # show the signal diagram
    # start_time_string = "2022-10-25 00:00"
    # end_time_string = "2022-10-26 23:00"
    # showdata = data[start_time_string:end_time_string]

    # plt.figure(figsize=(20.2, 4.5))
    # plt.scatter(showdata.index, showdata['buy'],
    #             color='green', label='buy signal', marker='^', alpha=1)
    # plt.scatter(showdata.index, showdata['sell'],
    #             color='red', label='sell signal', marker='v', alpha=1)
    # plt.plot(showdata['close'], label='close price', alpha=0.35)
    # plt.xticks(rotation=90)
    # plt.title('buy & sell signals for btcbusd')
    # plt.ylabel('USD Price($)')
    # plt.ylim((19000, 19500))
    # plt.xlabel('Date')
    # plt.legend(loc='upper left')
    # plt.show()


# calculate double exponential moving average (dema)
def dema(data, time_period, column):
    ema = data[column].ewm(span=time_period, adjust=False).mean()
    dema = 2 * ema - ema.ewm(span=time_period, adjust=False).mean()

    return dema


def main():
    # klines = [[1666674000000, "19331.70", "19335.80", "19287.10", "19330.60", "8341.560", 1666677599999, "161084721.92930", 48780, "4528.208", "87445084.23100", "0"], [
    #     1666677600000, "19330.70", "19357.40", "19314.10", "19319.00", "7302.847", 1666681199999, "141201576.04410", 45809, "3421.150", "66150889.70050", "0"]]
    # df = pd.DataFrame(klines, columns=[
    #     'openTime', 'open', 'high', 'low',
    #     'close', 'volume', 'closeTime', 'amount',
    #     'txCount', 'takerVolume', 'takerAmount', 'foo'
    # ])
    # df['hour'] = pd.to_datetime(
    #     df['openTime'], utc=True, unit='ms').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:00')
    # print(df)

    # 读取binance api的数据，获取最近200条K线数据
    klines = fetch_klines_from_binance(klinesCount)

    # 创建dataframe
    df = init_data_frame(json.loads(klines))

    # 运行strategy
    strategy(df)


if __name__ == "__main__":
    # 解析命令行参数并赋值给全局变量
    symbol = sys.argv[1]
    interval = sys.argv[2]
    main()
