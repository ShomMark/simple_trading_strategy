#!/usr/bin/env python3

import numpy as np
import pandas as pd
import talib as ta# for technical analysis
import random
from pandas_datareader import data
import os
from sklearn.preprocessing import StandardScaler # for preprocesing data
import matplotlib.pyplot as plt # for visualizing data
#from datetime import datetime # for manipulations with time features
import datetime
import time
from sklearn.preprocessing import MinMaxScaler # for preprocesing data
from sklearn import metrics # getting all needed metrcis for the model
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV
import math
import pytz
import json
from binance.client import Client
import requests 
import seaborn as sns
from datetime import timedelta

def get_hist_daily(symbol, start = "1000 days ago UTC", end = "now UTC"):
    # Connecting to Binance API
    API_KEY = "LdCZHDrnjgCLIUWyaW2ODGJ1VS8yl86GQtO4LEUDw7HVdzxrbpHHzN0DXoNfIJmD"
    API_SECRET = "DqoItExxTNFZdfK8Sqvo7MHzN2BfXJa1xOGeSUeXol1qrSDJjdUWfe8piTckECUq"
    client = Client(API_KEY, API_SECRET)
    interval = Client.KLINE_INTERVAL_1DAY
    
    klines = client.get_historical_klines(symbol, interval, start, end)
    df = pd.DataFrame(klines)
    df.columns = ['open_time',
                  'o', 'h', 'l', 'c', 'v',
                  'close_time', 'qav', 'num_trades',
                  'taker_base_vol', 'taker_quote_vol', 'ignore']
    # Time processing
    df.open_time = pd.to_datetime(df.open_time, unit='ms')
    df.close_time = pd.to_datetime(df.close_time, unit='ms')
    # Cleaning data
    del df['qav']
    del df['taker_base_vol']
    del df['taker_quote_vol']
    del df['ignore']
    del df['open_time']
    del df['num_trades']

    df['o'] = df['o'].astype(float)
    df['h'] = df['h'].astype(float)
    df['l'] = df['l'].astype(float)
    df['c'] = df['c'].astype(float)
    df['v'] = df['v'].astype(float)
    
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    df.close_time = pd.to_datetime(df.close_time).apply(lambda x: x.date())
    
    return df

def tester(test_ser, take_prof, stop_loss, tplong, tpshort, verb = 1, strategy = '', time_period = 30, close_nxt_day = False):
    signal = 0
    call = 'flat'
    order_amount = 10
    num = 0
    long_paid = 0
    long_profit = 0
    short_paid = 0
    short_profit = 0
    order_book = pd.DataFrame(columns = ['time', 'price', 'paid', 'size', 'order', 'type',
                                         'close_time', 'close_price','profit', 'perc', 'TP', 'SL'])
    ti = time.time()
    test_ser.reset_index(drop=True, inplace = True)
    #test_ser = test_ser.loc[-time_period:, :].copy()
    test_ser = test_ser.tail(time_period).copy()
    test_ser.reset_index(drop=True, inplace = True)
    for c in range(test_ser.shape[0]):

        if test_ser[strategy].loc[c] == 1:
            signal = 1
            call = 'long'
            price_d = 1.001
        elif test_ser[strategy].loc[c] == -1:
            signal = -1
            call = 'short'
            price_d = 0.999
        elif test_ser[strategy].loc[c] == 0:
            signal = 0
            call = 'flat'
        else:
            signal = 2
            call = 'flat'
            
        # Create Order
        if call != 'flat':
            price = price_d * test_ser.c[c]
            paid = order_amount
            coins = paid/price
            paid = paid*1.0025
            if call == 'long':
                long_paid += paid
                sl = stop_loss * price
            else:
                short_paid += paid
                sl = (2 - stop_loss) * price
            order_book.loc[num] = [test_ser.close_time[c], price, paid, coins, call, 'open', 
                                   test_ser.close_time[c], price, 0, 0, take_prof, sl]
            num += 1
        
        # Stop Loss, Take Profit, Time Stop
        for index, row in order_book[order_book['type'] == 'open'].iterrows():
            if row['order'] == 'long' and (tplong(signal) or c == test_ser.shape[0] - 1) or (close_nxt_day and test_ser.close_time[c] != row['time']):
                # Close Order
                order_book.loc[index,:], long_profit = take_long_prof(row, 
                                                                      test_ser.c[c], 
                                                                      test_ser.close_time[c], 
                                                                      long_profit)
            
            if row['order'] == 'short' and (tpshort(signal) or c == test_ser.shape[0] - 1) or (close_nxt_day and test_ser.close_time[c] != row['time']):
                # Close Order
                order_book.loc[index,:], short_profit = take_short_prof(row, 
                                                                        test_ser.c[c], 
                                                                        test_ser.close_time[c], 
                                                                        short_profit)
        if (c+1)%200==0 and verb == 1:
            ord_book = order_book.copy(deep = True)
            ord_book.to_csv(r'orders_not.csv')
            print('Perc_long = ' + '{0:.2f}'.format(100*long_profit / (long_paid+0.0001)) + '%' )
            print("Perc_short = " + "{0:.2f}".format(100*short_profit / (short_paid+ 0.0001)) + '%' )
            progress_display(c + 1, len(test_ser.close_time), ti)
            print('-----------------------------------')
    if verb == 1:
        print('Paid for long', long_paid)
        print('Profit from long', long_profit)
        print('Perc_long = ' + '{0:.2f}'.format(100*long_profit / (long_paid+0.0001)) + '%' )
        print('Paid for short', short_paid)
        print('Profit from short', short_profit)
        print("Perc_short = " + "{0:.2f}".format(100*short_profit / (short_paid+0.0001)) + '%' )
    ord_book = order_book.copy(deep = True)
    for z in range(len(order_book.time)):
        ord_book.loc[z,'time'] = ord_book.loc[z,'time'].strftime("%Y-%m-%d %H:%M:%S")
        ord_book.loc[z,'close_time'] = ord_book.loc[z,'close_time'].strftime("%Y-%m-%d %H:%M:%S")
    ord_book['perc'] = ord_book['perc'] * 100
        
    return ord_book, [long_paid, long_profit, short_paid, short_profit]

def tester_help(test_ser, take_prof, stop_loss, tplong, tpshort, verb = 1, strategy = '', time_period = 30, close_nxt_day = False):
    zz = 0
    zz_olong = 0
    zz_oshort = 0
    minn = 10000
    stepp = 30
    ll = len(range(30, time_period + stepp, stepp))
    for i in range(30, time_period+stepp, stepp):
        orders, ord_res = tester(test_ser.tail(time_period).head(i), take_prof, stop_loss, tplong, tpshort,
                                 verb = verb, strategy = strategy, close_nxt_day = close_nxt_day, time_period = 30)
        z0 = 100 * ((ord_res[1]/(ord_res[0]+0.00001)) + (ord_res[3]/(ord_res[2]+0.00001)))/2
        zz += z0
        if z0 < minn:
            minn = z0
        zz_olong += 100*orders[(orders['order']=='long')&(orders['profit']>0)].shape[0]/(orders[orders['order']=='long'].shape[0]+0.0001)
        zz_oshort += 100*orders[(orders['order']=='short')&(orders['profit']>0)].shape[0]/(orders[orders['order']=='short'].shape[0]+0.0001)
    return zz/ll, zz_olong/ll, zz_oshort/ll, minn

def take_long_prof(row, pr, time, longg_profit):
    row = row.copy()
    row['close_time'] = time
    row.loc['type'] = 'close'
    price = 0.999*pr
    row.loc['profit'] = row.loc['size']*price*0.999 - row.loc['paid']
    row.loc['perc'] = row.loc['profit'] / row.loc['paid']
    longg_profit += row.loc['profit']
    row.loc['close_price'] = price
    return row, longg_profit
    
def take_short_prof(row, pr, time, shortt_profit):
    row = row.copy()
    row['close_time'] = time
    row['type'] = 'close'
    price = 1.001*pr
    row['profit'] = row['paid'] - row['size']*price*0.999
    row['perc'] = row.loc['profit'] / row.loc['paid']
    shortt_profit += row['profit']
    row['close_price'] = price
    return row, shortt_profit

def plot_orders(orders, test_ser, signal):
    orders.time = pd.to_datetime(orders.time)
    orders.close_time = pd.to_datetime(orders.close_time)
    test_ser.close_time = pd.to_datetime(test_ser.close_time)
    test_ser.set_index('close_time', inplace=True)
    fig, ax = plt.subplots(figsize=(16,8))
    ax.plot(test_ser['c'])
    color = '-vr'
    if signal == 'long':
        color = '-^g'
    for index, row in orders[orders['order'] == signal].iterrows():
        #print(row)
        x1 = row.loc['time']
        x2 = row.loc['close_time']
        y1 = test_ser.loc[x1, 'c']
        y2 = test_ser.loc[x2, 'c']
        #print(x1, x2, y1, y2)
        ax.plot([x1,x2], [y1, y2], color, linewidth=.5)

def progress_display(a, b, ti):
    percc = 100 * a / b
    print("Progress: " + "{0:.2f}".format(percc) + '%')
    ttt = time.time() - ti
    time_now = chop_microseconds(datetime.timedelta(seconds = ttt))
    print("Time: " + str(time_now))
    time_left = chop_microseconds(datetime.timedelta(seconds = (100 * (ttt / percc)) - ttt))
    print("Left time: " + str(time_left))

def chop_microseconds(delta):
    return delta - datetime.timedelta(microseconds=delta.microseconds)

