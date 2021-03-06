import configparser
import requests
import json
from urllib.parse import parse_qs
from abc import ABC, abstractmethod
from datetime import timezone, datetime
from colorpk.models.db import User

config = configparser.ConfigParser()
config.read('local/connection.cnf')

def getUrl(src, state):
    url = ''
    if src == 'wb':
        url = "https://api.weibo.com/oauth2/authorize?" \
              "client_id=%s&scope=follow_app_official_microblog&" \
              "state=%s&redirect_uri=%s"\
              %(config[src]['appkey'], state, config[src]['url'])
    elif src == 'fb':
        url = "https://www.facebook.com/v2.8/dialog/oauth?" \
              "client_id=%s&response_type=code&state=%s&redirect_uri=%s"\
              %(config[src]['appkey'], state, config[src]['url'])
    elif src == 'gg':
        url = "https://accounts.google.com/o/oauth2/v2/auth?" \
              "client_id=%s&scope=https://www.googleapis.com/auth/plus.me https://www.googleapis.com/auth/userinfo.profile&" \
              "response_type=code&state=%s&redirect_uri=%s"\
              %(config[src]['appkey'], state, config[src]['url'])

    elif src == 'gh':
        url = "https://github.com/login/oauth/authorize?client_id=%s&state=%s&redirect_uri=%s"\
              %(config[src]['appkey'], state, config[src]['url'])

    return url

class OAuth2(ABC):
    def __init__(self, src):
        self.oauth = src
        self.api = config[src]['api']
        self.appKey = config[src]['appKey']
        self.appSecret = config[src]['appSecret']
        self.url = config[src]['url']
    @abstractmethod
    def getToken(self, code):
        pass

    @abstractmethod
    def getUserInfo(self, token):
        pass

    def registerUser(self, data):
        result = {'id': None, 'name': data['name'], 'img': data['img'], 'isadmin': False}
        qs = User.objects.filter(oauth=data['oauth'], oauthid=data['oauthid'])
        if qs.exists():
            qs.update(lastlogin=datetime.now(timezone.utc))
            thisUser = qs.get()
            result['id'] = thisUser.id
            result['isadmin'] = thisUser.isadmin
        else:
            newUser = User(oauth=data['oauth'],
                           name=data['name'],
                           oauthid=data['oauthid'],
                           lastlogin=datetime.now(timezone.utc))
            newUser.save()
            result['id'] = newUser.id
        return result

class OAuth2_fb(OAuth2):
    def __init__(self):
        super().__init__('fb')

    def getToken(self, code):
        payload = {
            "client_id": self.appKey,
            "client_secret": self.appSecret,
            "code": code,
            "redirect_uri": self.url,
        }
        r = requests.get("%s/oauth/access_token" % self.api, params=payload)
        res = json.loads(r.text)
        token = res['access_token'] if 'access_token' in res else ''
        return token

    def getUserInfo(self, token):
        payload = {
            "access_token": token,
            "fields": 'id,name,picture'
        }
        r = requests.get("%s/me" % self.api, params=payload)
        res = json.loads(r.text)
        data = {
            "oauthid": res["id"],
            "name": res["name"],
            "isadmin": False,
            "img": res['picture']['data']['url'],
            "oauth": self.oauth,
        }
        return data


class OAuth2_wb(OAuth2):
    def __init__(self):
        super().__init__('wb')
        self.uid = None

    def getToken(self, code):
        payload = {
            "client_id": self.appKey,
            "client_secret": self.appSecret,
            "code": code,
            "grant_type": 'authorization_code',
            "redirect_uri": self.url,
        }
        r = requests.post("%s/oauth2/access_token" % self.api, data=payload)
        res = json.loads(r.text)
        if 'access_token' in res:
            token = res['access_token']
            self.uid = res['uid']
        else:
            token = ''
        return token

    def getUserInfo(self, token):
        payload = {
            "access_token": token,
            "uid": self.uid
        }
        r = requests.get("%s/2/users/show.json" % self.api, params=payload)
        res = json.loads(r.text)
        data = {
            "oauthid": res["id"],
            "name": res["name"],
            "isadmin": False,
            "img": res['profile_image_url'],
            "oauth": self.oauth,
        }
        return data


class OAuth2_gg(OAuth2):
    def __init__(self):
        super().__init__('gg')

    def getToken(self, code):
        payload = {
            "code": code,
            "client_id": self.appKey,
            "client_secret": self.appSecret,
            "redirect_uri": self.url,
            "grant_type": "authorization_code"
        }
        r = requests.post("%s/oauth2/v4/token"%self.api, data=payload)
        res = json.loads(r.text)
        token = res['access_token'] if 'access_token' in res else ''
        return token

    def getUserInfo(self, token):
        payload = {
            "access_token": token,
        }
        r = requests.get("%s/plus/v1/people/me"%self.api, params=payload)
        res = json.loads(r.text)
        data = {
            "oauthid": res["id"],
            "name": res["displayName"],
            "isadmin": False,
            "img": res['image']['url'],
            "oauth": self.oauth,
        }
        return data


class OAuth2_gh(OAuth2):
    def __init__(self):
        super().__init__('gh')

    def getToken(self, code):
        payload = {
            "client_id": self.appKey,
            "client_secret": self.appSecret,
            "code": code,
            "redirect_uri": self.url,
        }
        r = requests.post("https://github.com/login/oauth/access_token", data=payload)
        res = parse_qs(r.text)
        token = res['access_token'][0] if 'access_token' in res else ''
        return token

    def getUserInfo(self, token):
        payload = {
            "access_token": token,
        }
        r = requests.get("%s/user" % self.api, params=payload)
        res = json.loads(r.text)
        data = {
            "oauthid": res["id"],
            "name": res["name"] if res['name'] else res['login'],
            "isadmin": False,
            "img": res['avatar_url'],
            "oauth": self.oauth,
        }
        return data