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

from funcs_for_trading import progress_display, get_hist_daily, tester_help
import sqlite3
from sqlite3 import Error

def get_last_index(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(id) FROM params")
 
    rows = cur.fetchall()
    return rows[0][0]

def get_sma_signal(symbol, p1, p2):
    data = get_hist_daily("ETHUSDT", start = str(p1+2)+" days ago UTC", end = "1 day ago UTC")
    data['SMA'] = ta.SMA(data.c, timeperiod = p1)
    data = data.tail(2)
    data.reset_index(drop=True, inplace = True)
    signal = 0
    data['SMA_startegy'] = signal
    if p2 == 0:
        data['SMA_startegy'] = np.where((data['SMA'] > data['c']) & (data['SMA'].shift() < data['c'].shift()), -1, data['SMA_startegy'])
        data['SMA_startegy'] = np.where((data['SMA'] < data['c']) & (data['SMA'].shift() > data['c'].shift()), 1, data['SMA_startegy'])
    else:
        data['SMA_startegy'] = np.where((data['SMA'] > data['c']), -1, data['SMA_startegy'])
        data['SMA_startegy'] = np.where((data['SMA'] < data['c']), 1, data['SMA_startegy'])
    signal = data['SMA_startegy'].iloc[-1]
    return signal, data

def trade(symbol, signal, data, quant = 0.15):
    API_KEY = "LdCZHDrnjgCLIUWyaW2ODGJ1VS8yl86GQtO4LEUDw7HVdzxrbpHHzN0DXoNfIJmD"
    API_SECRET = "DqoItExxTNFZdfK8Sqvo7MHzN2BfXJa1xOGeSUeXol1qrSDJjdUWfe8piTckECUq"
    client = Client(API_KEY, API_SECRET)
    database = r"/root/trading_apps/sma_trader/sma_order_book.db"
    conn = sqlite3.connect(database)
    sql_stmt = 'INSERT INTO order_book(open_time, open_price, open_paid, quantity, order_type, open_close, close_time, close_price, close_paid, profit, perc) VALUES(?,?,?,?,?,?,?,?,?,?,?)'
    cur = conn.cursor()
    
    if signal == 1:
        order_type = "long"
        order = client.order_market_buy(symbol=symbol, quantity=quant)
        paid = float(order['cummulativeQuoteQty'])
        price = float(order['fills'][0]['price'])
        ordd = (str(data.close_time.iloc[-1]), price, paid, quant, order_type, 'open',
                str(data.close_time.iloc[-1]), price, paid, profit, perc)
        cur.execute(sql_stmt, ordd)
    elif signal == -1:
        order_type = "short"
        order = client.order_market_sell(symbol=symbol, quantity=quant)
        paid = float(order['cummulativeQuoteQty'])
        price = float(order['fills'][0]['price'])
        ordd = (str(data.close_time.iloc[-1]), price, paid, quant, order_type, 'open',
                str(data.close_time.iloc[-1]), price, paid, 0, 0)
        cur.execute(sql_stmt, ordd)
    else:
        order_type = "flat"
    conn.close()

    trade_open_orders(symbol, signal, data)
    return

def trade_open_orders(symbol, signal, data):
    database = r"/root/trading_apps/sma_trader/sma_order_book.db"
    conn = sqlite3.connect(database)
    order_book = pd.read_sql_query("SELECT * FROM order_book WHERE open_close='open'", conn)
    conn.close()

    tplong = lambda x: x == -1
    tpshort = lambda x: x == 1

    sql = ''' UPDATE order_book
              SET open_time = ? ,
                  open_price = ? ,
                  open_paid = ? ,
                  quantity = ? ,
                  order_type = ? ,
                  open_close = ? ,
                  close_time = ? ,
                  close_price = ? ,
                  close_paid = ? ,
                  profit = ? ,
                  perc = ?
              WHERE id = ?'''
    
    for index, row in order_book[order_book['open_close'] == 'open'].iterrows():
        if row['order_type'] == 'long' and tplong(signal) and str(data.close_time.iloc[-1]) != row['open_time']:
            # Close Order
            order = client.order_market_sell(symbol=symbol, quantity=row['quantity'])
            ordd = tuple(row)[1:]
            ordd[6] = 'close'
            ordd[7] = str(data.close_time.iloc[-1])
            ordd[8] = float(order['fills'][0]['price'])
            ordd[9] = float(order['cummulativeQuoteQty'])
            ordd[10] = ordd[9] - ordd[3]
            ordd[10] = 100 * ((ordd[9] / ordd[3]) - 1)
            ordd = ordd + (int(row['id']),)

            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute(sql, ordd)
            conn.close()
        
        if row['order_type'] == 'short' and tpshort(signal) and str(data.close_time.iloc[-1]) != row['open_time']:
            # Close Order
            order = client.order_market_buy(symbol=symbol, quantity=row['quantity'])
            ordd = tuple(row)
            ordd[6] = 'close'
            ordd[7] = str(data.close_time.iloc[-1])
            ordd[8] = float(order['fills'][0]['price'])
            ordd[9] = float(order['cummulativeQuoteQty'])
            ordd[10] = ordd[3] - ordd[9]
            ordd[10] = 100 * ((ordd[3] / ordd[9]) - 1)
            ordd = ordd + (int(row['id']),)

            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute(sql, ordd)
            conn.close()
            
    return

def main():
    print ("System time:" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    database = r"/root/trading_apps/sma_trader/sma_params.db"
    conn = sqlite3.connect(database)
    with conn:
        idd = get_last_index(conn)
        cur = conn.cursor()
        cur.execute("SELECT * FROM params WHERE id="+str(idd))
        rows = cur.fetchall()
        ll = rows[0]
    conn.close()
    
    symbol = "ETHUSDT"
    quant = 0.15
    signal, data = get_sma_signal(symbol, int(ll[1]), int(ll[2]))
    # Get quantity to buy or sell 
    trade(symbol, signal, data, quant)
    print ("Signal = ", signal)
    print ("System time:" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

if __name__ == '__main__':
    main()
