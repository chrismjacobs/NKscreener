from flask import Flask, request, render_template, jsonify
import json
from datetime import datetime, timezone
from settings import SECRET_KEY, TVCODE, USER, DEBUG, RANGE, auth_required, r, DHOOK_H1, DHOOK_H4
from logHandler import logger
import time
import redis
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG


@app.route('/')
@auth_required
def home():

    return render_template('alertdash.html')


def updateJSON(dataDict):
    tf = dataDict['tf']
    print(dataDict)
    rName = 'NK_' + tf

    storeTF = json.loads(r.get(rName))

    sheetName = dataDict['force'].strip()
    print('SHEETNAME', sheetName)
    groups = dataDict['groups']
    messagesString = dataDict['mess']
    # "[MA Cross _1 _2, MA Cross _1 _3, MA Cross _1 _4, MA Cross _2 _3, MA Cross _2 _4, MA Cross _3 _4, RSI_1, RSI_2, MD_1, MD_2, MD_3, MD_1 ZERO, MD_2 ZERO, MD_3 ZERO, MD_P, MA_1 EQ, MA_2 EQ, MA_3 EQ, MA_4 EQ, MA_1 X ABOVE, MA_2 X ABOVE, MA_3 X ABOVE, MA_4 X ABOVE, MA_1 X BELOW, MA_2 X BELOW, MA_3 X BELOW, MA_4 X BELOW, SLOPE, SUPPORT, RESISTANCE]"
    messages1 = messagesString.split('[')[1]
    messages2 = messages1.split(']')[0]
    messages = messages2.split(',')

    tickers = dataDict['tickers']


    ## start new JSON
    newJSON = {}

    ## earlier JSON entries
    allStored = list(storeTF.keys())
    allStored.sort()
    print('SORTED LIST', allStored)
    if len(allStored) > 3:
        print('POP ', allStored[0])
        allStored.pop(0)


    for recordDay in allStored:
        newJSON[recordDay] = storeTF[recordDay]

    if sheetName not in list(newJSON.keys()):
        newJSON[sheetName] = {}

    # print(day)

    for t in tickers:
        #"(5)15;16;17;28"

        alertStr = tickers[t]['alert']
        alertStrSplit = alertStr.split(')')
        dayStr = alertStrSplit[0].split('(')[1]

        triggers = ''
        for tr in alertStrSplit[1].split(';'):
            triggers += (messages[int(tr)].strip() + '; ')


        newJSON[sheetName][t] = {
            'key': tickers[t]['key'],
            'alert' : triggers,
            'day' : dayStr,
            'group' : groups[int(tickers[t]['g'])]
        }

    postStored = list(newJSON.keys())
    print('NEWLIST', postStored)
    r.set(rName, json.dumps(newJSON))

    return True



def sendMessage(_signal, DHOOK, _ticker, _group, _index):
    str1 = "```ansi\n"

    ## 0 = normal text  1 = bold text   4 = Underline
    zeroUse = 1
    crossUse = 0
    colorChoice = {
        'A' : 'yellow',
        'B' : 'pink',
        'C' : 'cyan'
    }


    escape =  "\u001b[" + str(crossUse) + ";"

    if 'ZERO' in _signal:
        escape =  "\u001b[" + str(zeroUse) + ";"

    ## High Intensity [0;91m] instead of 31m

    colors = {  ### bg / text
        '': [''],
        'grey': ['44;'],
        'red' : ['45;', '31m'],
        'green' : ['43;', '32m'],
        'yellow' : ['41;', '33m'],
        'blue' : ['40;', '34m'],
        'pink' : ['45;', '35m'],
        'cyan' : ['42;', '36m'],
        'white' : ['47;', '37m']
    }
    ## bground first then color

    str2 = "\n```"

    textCol = 'white'
    if '_A' in _signal:
        textCol = colorChoice['A']
    if '_B' in _signal:
        textCol = colorChoice['B']
    if '_C' in _signal:
        textCol = colorChoice['C']


    message = _ticker + ' ' + _signal + ' ' + _group + ' ' + _index

    msg = str1 + escape +  colors[''][0] + colors[textCol][1] + message + str2


    data = {'content': msg}
    response = requests.post(DHOOK, json=data)
    print(response)

    return True


def getSignal(dataDict):

    tf = dataDict['tf']

    DDICT = {
        '60' : DHOOK_H1,
        '240' : DHOOK_H4
    }

    DHOOK = DDICT[tf]

    groups = dataDict['groups']
    messagesString = dataDict['mess']
    # print(messagesString)
    # "[MD_1, MD_2, MD_3, MD_1 ZERO, MD_2 ZERO, MD_3 ZERO]"
    messages1 = messagesString.split('[')[1]
    # print(messages1)
    messages2 = messages1.split(']')[0]
    # print(messages2)
    messages = messages2.split(',')
    print(messages)

    tickers = dataDict['tickers']

    for t in tickers:
        #"(5)15;16;17;28"

        alertStr = tickers[t]['alert']
        alertStrSplit = alertStr.split(')')
        print(alertStrSplit)
        dayStr = alertStrSplit[0].split('(')[1]

        triggers = ''

        for tr in alertStrSplit[1].split(';'):
            # print(t, tr, tickers)
            _signal = messages[int(tr)].strip()
            # print('S', _signal)
            _ticker = tickers[t]['key']
            # print('T', _ticker)
            _group = 'Unknown'
            if len(groups) > 0:
                _group = groups[int(tickers[t]['g'])]
            # print('G', _group)
            _index = t
            print('sendMessage')
            sendMessage(_signal, DHOOK, _ticker, _group, _index)

    return True


@app.route("/webhook", methods=['POST'])
def tradingview_webhook():

    dataDict = None

    try:
        dataDict = json.loads(request.data)
    except Exception as e:
        logger.error('DATA WEBHOOK LOAD EXCEPTION ' + str(e))
        return 'ERROR'

    logger.info('WEBHOOK DATA: ' +  json.dumps(dataDict))


    try:
        ## check TV code
        logger.debug(dataDict['tvCode'])
        if not dataDict['tvCode']:
            logger.error('CODE ERROR NONE')
            return 'ERROR'
        elif int(dataDict['tvCode']) != int(TVCODE):
            logger.error('CODE MATCH ERROR')
            return 'ERROR'
        else:
            logger.debug('CODE SUCCESS')
    except Exception as e:
        logger.error('TV CODE EXCEPTION: ' + str(e))
        return 'ERROR'

    try:
        resultCheck = updateJSON(dataDict)
        m = 'UPDATE JSON: ' + str(resultCheck)
        logger.debug(m)
    except Exception as e:
        m = 'UPDATE JSON: ' + str(e)
        logger.error(m)


    return 'TV WEBHOOK COMPLETE'


@app.route("/intraday", methods=['POST'])
def tradingview_intraday():
    print('INTRADAY')

    dataDict = None

    try:
        dataDict = json.loads(request.data)
    except Exception as e:
        logger.error('DATA INTRADAY LOAD EXCEPTION ' + str(e))
        return 'ERROR'

    logger.info('INTRADAY DATA: ' +  json.dumps(dataDict))


    try:
        ## check TV code
        logger.debug(dataDict['tvCode'])
        if not dataDict['tvCode']:
            logger.error('CODE ERROR NONE')
            return 'ERROR'
        elif int(dataDict['tvCode']) != int(TVCODE):
            logger.error('CODE MATCH ERROR')
            return 'ERROR'
        else:
            logger.debug('CODE SUCCESS')
    except Exception as e:
        logger.error('TV CODE EXCEPTION: ' + str(e))
        return 'ERROR'

    try:
        resultCheck = getSignal(dataDict)
        m = 'SEND MESSAGE: ' + str(resultCheck)
        logger.debug(m)
    except Exception as e:
        m = 'SEND MESSAGE: ' + str(e)
        logger.error(m)


    return 'TV WEBHOOK COMPLETE'


@app.route("/ping", methods=['POST'])
def ping_webhook():
    logger.warning('PING RECEIVED')
    return 'PING'

def sortData(alerts):
    alertKeys = list(alerts.keys())
    alertKeys.sort()

    setCount = []
    missing = []
    newAlerts = {}
    for a in alertKeys:
        newAlerts[a]=alerts[a]
        setNum = a.split('-')[0]
        if int(setNum) not in setCount:
            setCount.append(int(setNum))

    for i in range(int(RANGE)):
        if i+1 not in setCount:
            missing.append(i+1)

    setCount.sort(key=int)

    return [newAlerts, setCount, missing]


@app.route('/getData', methods=['POST'])
def getData():
    pw = request.form ['pw']
    day = request.form ['day']
    month = request.form ['month']
    year = request.form ['year']
    tf = request.form ['tf']

    print(day, month, tf)
    if int(pw) != int(TVCODE):
        return {'error' : 'authentication code input required'}

    store = {}
    rName = 'NK_' + tf
    store = json.loads(r.get(rName))
    dataDict = {}

    dataDict['user'] = USER
    dataDict['alerts'] = {}
    dataDict['sets'] = []
    dataDict['miss'] = []
    dataDict['saved'] = list(store.keys())
    m = month
    d = day
    print(month, type(month))
    print(day, type(day))
    if int(month) < 10:
        m = '0' + str(month)
    if int(day) < 10:
        d = '0' + str(day)
    sheetName = str(year) + '-' + m + '-' + d + '-' + tf
    if sheetName in list(store.keys()):
        sD = sortData(store[sheetName])
        #print(sD)
        dataDict['alerts'] = sD[0]
        dataDict['sets'] = sD[1]
        dataDict['miss'] = sD[2]
    else:
        print('Data not found')

    print('getInfo', sheetName, list(store.keys()))

    try:
        with open('log.log', 'r') as log_file:
            try:
                logLines = []
                for l in log_file.readlines():
                    if 'HTTP' not in l and 'DEBUG' not in l and 'OSError' not in l:
                        logLines.append(l)

                if len(logLines) > 100:
                    reverseLogs = logLines[:len(logLines)-100:-1]
                else:
                    reverseLogs = logLines[::-1]

                dataDict['logs'] = reverseLogs
            except Exception as e:
                logger.error('GET DATA LOAD ERROR LOGS: ' + str(e))
                return False
    except Exception as e:
        print('LOGGER ERROR', e)

    return json.dumps(dataDict)






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

