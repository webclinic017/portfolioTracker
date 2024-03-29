#!/usr/bin/env python
import pika, sys, os, json
from datetime import date
import datetime
from pymongo import MongoClient
import logging
import logging.handlers
from Email import Mail
import MongoPortfolio

handler = logging.handlers.WatchedFileHandler(
    os.environ.get("LOGFILE", "./log"))
formatter = logging.Formatter(logging.BASIC_FORMAT)
handler.setFormatter(formatter)
root = logging.getLogger()
root.setLevel(os.environ.get("LOGLEVEL", "DEBUG"))
logging.getLogger('pika').setLevel(logging.ERROR)
root.addHandler(handler)
emailObj = Mail(logging)

credentials = pika.PlainCredentials('messenger', 'messengerPassword')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', port=5672, virtual_host='/', credentials=credentials ))
channel = connection.channel()

def sanitizeNews(body):
    payload = json.loads(body)
    logging.info(payload)
    if payload['title'] == None or type(payload['title']) != str:
        raise Exception("unable to parse title")
    if payload['comment'] == None or type(payload['comment']) != str:
        raise Exception("unable to parse comment")
    if payload['link'] == None or type(payload['link']) != str:
        raise Exception("unable to parse link")
    if type(payload['tags']) != list:
        raise Exception("unable to parse tags")

userPortfolio = None

def emailInSystem(email):
    try:
        userPortfolio = MongoPortfolio.MongoGetDocument(email)
        if userPortfolio:
            return True
    except:
        return False

def sanitizeOrder(body):
    payload = json.loads(body)
    logging.info(payload)
    if payload['email'] == None or not emailInSystem(payload['email']) :
        print('email failed')
        raise Exception("unable to parse email")
    if payload['order'] not in ['buy', 'sell'] :
        print('order failed')
        raise Exception("unable to parse order type")
    if payload['ticker'] not in ["AAPL", "VUG", "GME", "VOO", "BTC", "ETH", "BRK-B"]:
        print('ticker failed')
        raise Exception("unable to parse ticker")
    if type(payload['price']) != float and type(payload['price']) !=  int or payload['price'] <= 0:
        print('price failed')
        raise Exception("unable to parse price")
    if type(payload['volume']) != float and type(payload['volume']) != int or payload['volume'] <= 0:
        print('volume failed')
        raise Exception("unable to parse volume")
    print('handling ok')

def persistNews(body):
    payload = json.loads(body)
    print(payload)
    if 'All' not in payload['tags']:
        payload['tags'].append('all')
    logging.info("writing to db")
    logging.info("title: " + payload['title'])
    logging.info("comment: " + payload['comment'])
    logging.info("link: " + payload['link'])
    logging.info("tags: " + str(payload['tags']))
    message_date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    try:
        client = MongoClient("localhost")
        db = client.portfolioTracker
        data = {"date": message_date, "title" : payload['title'], "comment": payload['comment'], "link" : payload['link'], "tags" : payload['tags']}
        db.news.insert_one(data)
        emailObj.sendNews(title=payload['title'])
    except:
        logging.error("unable to write to db")
        raise Exception("unable to write to db")

def persistOrder(body):
    payload = json.loads(body)
    email = payload['email']
    user = MongoPortfolio.MongoGetDocument(payload['email'])
    stocks = user['portfolio'].keys()
    for item in stocks:
        logging.info(item + ", owning " + str(user['portfolio'][item]) + " shares")
    ownedShares = 0
    assetChoice = payload['ticker']
    if assetChoice not in stocks:
        if assetChoice in known_tickers:
            logging.info("purchasing a new asset")
            user['portfolio'][assetChoice] = 0
            paddingLength = len(user['dates'])
            padding = []
            for i in range(paddingLength):
                padding.append(0)
            user['seriesdataset'].append({'name' : assetChoice, 'data' : padding})
            logging.info(user['seriesdataset'])
        else:
            raise Exception("exit program. ensure getters/setters are defined in portfolio.py")
            print("exit program. ensure getters/setters are defined in portfolio.py")
    else:
        ownedShares = user['portfolio'][assetChoice]
        logging.info("available shares: "+ str(ownedShares))
    action = payload['order']
    volume = round(float(payload['volume']),8)
    if str(volume)[-2:] == '.0': # if the volume is a integer, we won't persist trailing zeros.
        logging.info("converting float to int")
        volume = int(volume)
    newOwned = 0
    if action == "sell" and volume > ownedShares:
        raise Exception("exit program. ensure shares are available.")
        print("exit program. ensure shares are available.")
    if action == "sell":
        newOwned = ownedShares - volume
    elif action == "buy":
        newOwned = ownedShares + volume
    price = round(float(payload['price']),2)

    user['portfolio'][assetChoice]=newOwned
    logging.info(user['portfolio'])

    graphPoint = MongoPortfolio.MongoGetDocument("Market")
    managedList = 0
    for list in graphPoint['seriesdataset']:
        if list['name'] == "Managed Assets":
             managedList= list['data']
    dataLength = len(managedList)
    allAssets = round(managedList[dataLength-1], 2)
    date = graphPoint['dates'][dataLength-1]

    scatterData = MongoPortfolio.MongoGetScatter(payload['email'])
    scatterData["endValue"].append(allAssets)
    scatterData["date"].append(date)
    scatterData["volume"].append(price)
    logging.info(scatterData["endValue"][-1])
    logging.info(scatterData["date"][-1])
    logging.info(scatterData["volume"][-1])
    try:
        MongoPortfolio.MongoPersistDocument(user, email)
        MongoPortfolio.MongoPersistScatter(scatterData, email)
        emailObj.sendOrder(emailTo=email, user=MongoPortfolio.MongoGetUserName(email), order=action, volume=volume, ticker=assetChoice, price=price)
        if email != 'stumay1992@gmail.com':
            emailObj.sendOrder(emailTo='stumay1992@gmail.com', user=MongoPortfolio.MongoGetUserName(email), order=action, volume=volume, ticker=assetChoice, price=price)
    except Exception as e:
        raise Exception("unable to persist order " + str(e))


newsQueuePending = True
while newsQueuePending:
    method_frame, header_frame, body = channel.basic_get(queue = 'news')
    if method_frame is None:
        newsQueuePending = False
        break
    else:
        logging.info("we have news")
        try:
            sanitizeNews(body)
            persistNews(body)
            logging.info("done")
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        except Exception as e:
            print("failed to handle message " + str(e))
            channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)

orderQueuePending = True
while orderQueuePending:
    method_frame, header_frame, body = channel.basic_get(queue = 'order')
    if method_frame is None:
        orderQueuePending = False
        break
    else:
        logging.info("we have orders")
        try:
            sanitizeOrder(body)
            persistOrder(body)
            logging.info("done")
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        except Exception as e:
            print("failed to handle message " + str(e))
            channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)


