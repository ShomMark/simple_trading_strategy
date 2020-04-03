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

def tuning_sma_strategy(data, t_period = 30):  
    maxx = 0
    ll = len(range(2,80))
    ti = time.time()
    t=1
    df_params = pd.DataFrame(columns = ['maxx', 'i', 'j', 'orders_long', 'orders_short', 'alpha', 'min'])
    dd = 0
    for i in range(2,80):
        for j in [0, 1]:
            # Create strategy
            data['SMA'] = ta.SMA(data.c, timeperiod = i)
            data['SMA_startegy'] = 0
            if j == 0:
                data['SMA_startegy'] = np.where((data['SMA'] > data['c']) & (data['SMA'].shift() < data['c'].shift()), -1, data['SMA_startegy'])
                data['SMA_startegy'] = np.where((data['SMA'] < data['c']) & (data['SMA'].shift() > data['c'].shift()), 1, data['SMA_startegy'])
            else:
                data['SMA_startegy'] = np.where((data['SMA'] > data['c']), -1, data['SMA_startegy'])
                data['SMA_startegy'] = np.where((data['SMA'] < data['c']), 1, data['SMA_startegy'])
            # Test strategy
            #orders, ord_res = tester(data, 0, 0, verb = 0, strategy = 'SMA_startegy',
            #                         time_period = t_period, tplong = lambda x: x == -1, tpshort = lambda x: x == 1)
            
            s, olong, oshort, minn = tester_help(data, 0, 0, verb = 0, strategy = 'SMA_startegy',
                                     time_period = t_period, tplong = lambda x: x == -1, tpshort = lambda x: x == 1)
            
            #s = 100 * ((ord_res[1]/(ord_res[0]+0.00001)) + (ord_res[3]/(ord_res[2]+0.00001)))/2
            #olong = orders[orders['order']=='long'].shape[0]
            #oshort = orders[orders['order']=='short'].shape[0]
            if s > 0:
                df_params.loc[dd,:] = [s, i, j, olong, oshort, s*(olong+oshort)/2, minn]
                dd +=1
        if (t-1)%10 == 0 or t == ll:
            progress_display(t, ll, ti)
            df_params.drop_duplicates(subset ="alpha", keep = 'first', inplace = True) 
        t += 1
    return df_params

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
 
    return conn

def create_params(conn, params):
    """
    Create a new task
    :param conn:
    :param task:
    :return:
    """
 
    sql_stmt = 'INSERT INTO params(id,p1,p2,profit,risk) VALUES(?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql_stmt, params)
    return cur.lastrowid

def get_last_index(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(id) FROM params")
 
    rows = cur.fetchall()
    return rows[0][0]

def main():
    df = get_hist_daily("ETHUSDT", start = "500 days ago UTC")
    df_p = tuning_sma_strategy(df, t_period = 60)
    df_p = df_p[df_p['min']>=0]
    df_p = df_p.sort_values(axis = 0, by = ['maxx'], ascending=False)
    df_p.reset_index(drop=True, inplace = True)
    df_p2 = df_p.head()
    print(df_p2)
    database = r"/root/trading-apps/sma-trader/sma_params.db"
    conn = create_connection(database)
    with conn:
        idd = 1 + get_last_index(conn)
        par = (idd, df_p['i'].loc[0], df_p['j'].loc[0], df_p['alpha'].loc[0], (df_p['orders_long'].loc[0]+df_p['orders_short'].loc[0])/2);
        par_id = create_params(conn, par)
    print ("System time:" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    conn.close()
    df=None
    df_p=None

if __name__ == '__main__':
    #while True:
    main()
    #time.sleep(5)
