import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import sqlite3
from sqlite3 import Error
import pandas as pd
import numpy as np
from binance.client import Client
import matplotlib.pyplot as plt

def plot_orders(orders, test_ser):
    orders.open_time = pd.to_datetime(orders.open_time)
    orders.close_time = pd.to_datetime(orders.close_time)
    test_ser.close_time = pd.to_datetime(test_ser.close_time)
    test_ser.set_index('close_time', inplace=True)
    fig, ax = plt.subplots(figsize=(16,10))
    ax.plot(test_ser['c'])
    for index, row in orders.iterrows():
        x1 = row.loc['open_time']
        x2 = row.loc['close_time']
        y1 = test_ser.loc[x1, 'c']
        y2 = test_ser.loc[x2, 'c']
        color = '-vr'
        if row.loc['order_type'] == 'long':
            color = '-^g'
        ax.plot([x1,x2], [y1, y2], color, linewidth=.5)

    return fig
