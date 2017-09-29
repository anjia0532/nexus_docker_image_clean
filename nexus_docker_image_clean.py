#! /usr/bin/env python
# -*- coding: utf-8 -*-
# python2.7

from requests import Request, Session
from requests.exceptions import RequestException
from datetime import datetime,timedelta
import json
import sys

username = 'admin'
password = 'admin123'

nexusHost = 'http://localhost:8081'

repoName = 'docker'

days = 30

headers = {
    'content-type': 'application/json'
}

loginUrl = '%s/service/rapture/session' % nexusHost

directUrl = '%s/service/extdirect' % nexusHost

s = Session()


def post(url,headers={},data = {}):
    response = s.post(url,headers = headers,data=data)
    try:
        response.raise_for_status()
    except RequestException as e:
        print e
        return None
    if 'content-type' in response.headers and "application/json" in response.headers["content-type"]:
        respJson = response.json()
        if respJson and respJson.get("result",{"success":False}).get("success",False):
            return respJson["result"]
        else:
            return None
            
    return response.text

def signIn():
    return post(url = loginUrl, data = {
        "username": base64.b64encode(username),
        "password": base64.b64encode(password)
    }) != None

# docker image list
def getList(page=1,start=0,limit=300):
    imgList = post(url = directUrl, headers = headers, data = json.dumps({
        "action": "coreui_Component",
        "method": "read",
        "data": [{
            "page": page,
            "start": start,
            "limit": limit,
            "sort": [{
                "property": "name",
                "direction": "ASC"
            }, {
                "property": "version",
                "direction": "ASC"
            }],
            "filter": [{
                "property": "repositoryName",
                "value": repoName
            }]
        }],
        "type": "rpc",
        "tid": 5
    }))
    
    if not imgList : return None
    # get all image list
    if len(imgList["data"])==limit:
        tmpList = getList(page=page+1,start=limit*page,limit=limit)
        if tmpList and tmpList.get("data",False):
            tmpList["data"].extend(imgList["data"])
            return tmpList
        
    return imgList

# get image details(e.g. last download datetime)
def getImgInfo(page=1,start=0,limit=300,imgId=None,name=None,version=None,repo=repoName):
    if not imgId or not name or not version or not repo: return None
    
    imgInfo =  post(directUrl, headers = headers, data = json.dumps({
        "action": "coreui_Component",
        "method": "readComponentAssets",
        "data": [{
            "page": page,
            "start": start,
            "limit": limit,
            "filter": [{
                "property": "repositoryName",
                "value": repo
            }, {
                "property": "componentId",
                "value": imgId
            }, {
                "property": "componentName",
                "value": name
            }, {
                "property": "componentVersion",
                "value": version
            }]
        }],
        "type": "rpc",
        "tid": 9
    }))
    
    if not imgInfo or "data" not in imgInfo:
        return None
    return imgInfo["data"]

# purge expire image 
def purgeExpire(data=None,name=None,version=None):
    
    if not data or not name or not version:
        return None
    
    for item in data:
        lastDown = datetime.strptime(item["lastDownloaded"][0:19],'%Y-%m-%dT%H:%M:%S')
        diffDays = (datetime.now() - lastDown).days
        if diffDays > days:
            result = post(directUrl, headers = headers, data = json.dumps({
                "action": "coreui_Component",
                "method": "deleteComponent",
                "data": [item["id"], item["repositoryName"]],
                "type": "rpc",
                "tid": 64
            }))
            print "%s:%s lastest downloaded is %s(more than %s days), delete result %s" %(name,version,lastDown,days,json.dumps(result))

# sign in
if not signIn():
    print 'failed to sign in'
    sys.exit(1)

# get all image list
imgList=getList()
if not imgList:
    print 'failed to get images list'
    sys.exit(1)

data = imgList["data"]

for item in data:
    imgInfo = getImgInfo(imgId=item["id"],name=item["name"],version=item["version"],repo=item["repositoryName"])
    purgeExpire(data=imgInfo,name=item["name"],version=item["version"])
