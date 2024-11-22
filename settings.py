
from functools import wraps
from flask import make_response, request
import os
import redis
import json

try:
    import config as config
    SECRET_KEY = config.SECRET_KEY
    USER = config.USER
    RANGE = config.RANGE
    TVCODE = config.TVCODE
    DEBUG = True
    REDIS_URL = config.REDIS_URL
    DHOOK_H1 = config.DHOOK_H1
    DHOOK_H4 = config.DHOOK_H4
    print('CONFIG SUCCESS')
    LOCAL = True
except:
    print('ACCESS OS ENVIRON CREDENTIALS')
    SECRET_KEY = os.environ['SECRET_KEY']
    USER = os.environ['USER']
    TVCODE = os.environ['TVCODE']
    RANGE = os.environ['RANGE']
    REDIS_URL = os.environ['REDIS_URL']
    DHOOK_H1 = os.environ['DHOOK_H1']
    DHOOK_H4 = os.environ['DHOOK_H4']
    DEBUG = False
    LOCAL = False


if REDIS_URL:
    if LOCAL:
        r = redis.from_url(REDIS_URL, ssl_cert_reqs=None, decode_responses=True)
    else:
        ## For Render URL
        r = redis.from_url(REDIS_URL, decode_responses=True)

if not r.get('NK_D'):
    r.set('NK_D', json.dumps({}))
if not r.get('NK_W'):
    r.set('NK_W', json.dumps({}))

print('CONFIG SUCCESS')

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        username = USER
        passcode = TVCODE

        if auth and auth.username == username and auth.password == passcode:
            return f(*args, **kwargs)
        return make_response("<h1>Access denied!</h1>", 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})

    return decorated


