from pymongo import MongoClient


def MongoGetDocument(user = 'Stu'):
    key = "'_id': {}".format(user)
    client = MongoClient("localhost")
    db = client.portfolioTracker
    return db.portfolios.find_one({'_id': user})
    client.close()
def MongoGetUsers():
    userList = []
    client = MongoClient("localhost")
    db = client.portfolioTracker
    userDict = list(db.users.find({}, {'email':1, '_id' : 0}))
    for emailKey in userDict:
        userList.append(emailKey['email'])
    return userList

def MongoGetUserName(email):
    userList = []
    client = MongoClient("localhost")
    db = client.portfolioTracker
    userDict = list(db.users.find({'email': email}, {'name':1, '_id' : 0}))
    for name in userDict:
        userList.append(name['name'])
    return userList[0]

def MongoMarketScatter(data):
    client = MongoClient("localhost")
    db = client.portfolioTracker
    return db.volume.replace_one({'_id': 'all'}, data)
    client.close()

def MongoPersistDocument(data, user = 'Stu'):
    key = {'_id': user}
    client = MongoClient("localhost")
    db = client.portfolioTracker
    if db.portfolios.find_one({}) == None:
        db.portfolios.insert_one(data)
    else:
        result=db.portfolios.replace_one(key, data)
    confirmEntry = db.portfolios.find_one({'_id': user})
    client.close()

def MongoPersistUser(data, user = 'stumay1992@gmail.com'):
    key = {'email': user}
    client = MongoClient("localhost")
    db = client.portfolioTracker
    result=db.users.replace_one(key, data)
    confirmEntry = db.users.find_one({'email': user})
    client.close()

def MongoUpdateSecret(secret):
    users = MongoPortfolio.MongoGetUsers()
    for user in users:
        data = MongoGetDocument(user)
        data['daily secret'] = secret
        MongoPersistUser(data, user)
