#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import sqlite3
from sqlite3 import Error
import pandas as pd
import numpy as np
from binance.client import Client
import matplotlib.pyplot as plt
from funcs_for_telegram import plot_orders

TOKEN = "1020340451:AAEvxRS2Y46IFtKBpntQLl0waOrAa4-U8xs"
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

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


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text(
        'Try these commands:\n' +
        '/balance [currency] - get latest balance\n' +
        '/get_sma_params - get latest params for sma_trader\n' +
        '/ticker [pair] - get latest ticker\n' +
        '/graph_30d [pair] - get 30 days graph\n' +
        '/graph_10d [pair] - get 10 days graph\n' +
        '/trades [pair] - show last 2 orders\n' +
        '/orders_sma  - show sma orders\n')
    ''' +

        '/orderbook [pair] [depth] - get orderbook\n' +
        '/limit [buy/sell] [pair] [quantity] [price] - trade\n' +
        '/stop [buy/sell] [pair] [quantity] [price] - trade\n' +
        '/market [buy/sell] [pair] [quantity] - trade\n' +
        '/orders [pair] - show open orders\n' +
        '/cancel-all [pair] - cancel all orders\n' +
        '/cancel [order_id] - cancel one order\n' +
        '/tradehistory - show last few closed trades\n' +
        '/address [currency] - get address\n' +
        '/newaddress [currency] - create new address'
    )
    '''

def balance(update, context):
    """Get balance """
    API_KEY = "LdCZHDrnjgCLIUWyaW2ODGJ1VS8yl86GQtO4LEUDw7HVdzxrbpHHzN0DXoNfIJmD"
    API_SECRET = "DqoItExxTNFZdfK8Sqvo7MHzN2BfXJa1xOGeSUeXol1qrSDJjdUWfe8piTckECUq"
    client = Client(API_KEY, API_SECRET)
    symbol = context.args[0]
    update.message.reply_text(client.get_asset_balance(asset=symbol)['free'])

def ticker(update, context):
    """Get ticker """
    API_KEY = "LdCZHDrnjgCLIUWyaW2ODGJ1VS8yl86GQtO4LEUDw7HVdzxrbpHHzN0DXoNfIJmD"
    API_SECRET = "DqoItExxTNFZdfK8Sqvo7MHzN2BfXJa1xOGeSUeXol1qrSDJjdUWfe8piTckECUq"
    client = Client(API_KEY, API_SECRET)
    symbol = context.args[0]

    kk = client.get_ticker(symbol=symbol).keys()
    ddf = pd.DataFrame(client.get_ticker(symbol=symbol), index = [symbol]).transpose()
    
    update.message.reply_text(ddf.to_string())

def echo(update, context):
    """Echo the user message."""
    #update.message.reply_text(update.message.text)
    update.message.delete() #update.message.chat_id, update.message.message_id)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def get_sma_params(update, context):
    database = r"root/trading_apps/sma_trader/sma_params.db"#sftp://root@138.197.79.99/root/trading-apps/sma-trader/sma_params.db
    conn = sqlite3.connect(database)
    with conn:
        idd = get_last_index(conn)
        cur = conn.cursor()
        cur.execute("SELECT * FROM params WHERE id="+str(get_last_index(conn)))
        rows = cur.fetchall()
        ll = rows[0]
    conn.close()
    update.message.reply_text("SMA Strategy Parameters:\n" +
                              "Window = " + "{0:.2f}".format(ll[1]) + "\n" + 
                              "Single/Multiple = " + "{0:.2f}".format(ll[2]) + "\n" + 
                              "Profit = " + "{0:.2f}".format(ll[3]) + "\n" + 
                              "Risk = " + "{0:.2f}".format(ll[4]))

def get_last_index(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(id) FROM params")
 
    rows = cur.fetchall()
    return rows[0][0]

def graph_30d(update, context):
    """Get ticker """
    symbol = context.args[0]

    data = get_hist_daily(symbol, start = "30 days ago UTC")

    plt.figure(figsize=(16,10))
    plt.plot(data.close_time,data.c)
    filename = '/root/telegram_bots/data/gr_30d.png'
    plt.savefig(filename, bbox_inches='tight')
    #update.message.reply_photo(photo = '/root/telegram_bots/data/gr_30d.png', quote = True)
    update.message.reply_photo(photo = open(filename, 'rb'), quote = True, caption = "30d graph of "+symbol)

def graph_10d(update, context):
    """Get ticker """
    symbol = context.args[0]

    data = get_hist_daily(symbol, start = "10 days ago UTC")

    plt.figure(figsize=(16,10))
    plt.plot(data.close_time,data.c)
    filename = '/root/telegram_bots/data/gr_10d.png'
    plt.savefig(filename, bbox_inches='tight')
    #update.message.reply_photo(photo = '/root/telegram_bots/data/gr_30d.png', quote = True)
    update.message.reply_photo(photo = open(filename, 'rb'), quote = True, caption = "10d graph of " + symbol)

def orders_sma(update, context):
    symbol = "ETHUSDT"
    data = get_hist_daily(symbol, start = "30 days ago UTC")
    database = r"/root/trading_apps/sma_trader/sma_order_book.db"
    conn = sqlite3.connect(database)
    order_book = pd.read_sql_query("SELECT * FROM order_book", conn)
    conn.close()
    fig = plot_orders(order_book, data)
    filename = '/root/telegram_bots/data/orders_sma.png'
    plt.savefig(filename, bbox_inches='tight')
    update.message.reply_photo(photo = open(filename, 'rb'), quote = True, caption = "SMA order book " + symbol)
    

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater("1020340451:AAEvxRS2Y46IFtKBpntQLl0waOrAa4-U8xs", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("get_sma_params", get_sma_params))
    dp.add_handler(CommandHandler("graph_30d", graph_30d, pass_args=True))
    dp.add_handler(CommandHandler("graph_10d", graph_10d, pass_args=True))
    dp.add_handler(CommandHandler("balance", balance, pass_args=True))
    dp.add_handler(CommandHandler("ticker", ticker, pass_args=True))
    dp.add_handler(CommandHandler("orders_sma", orders_sma))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.all, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
